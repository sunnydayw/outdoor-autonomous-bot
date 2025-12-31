# backend/uart_bridge.py
"""Pi->Pico UART bridge that sends velocity commands with a periodic heartbeat."""
from __future__ import annotations

import logging
import struct
import time
from typing import Optional, Tuple

import serial
from serial import SerialException

from .command_state import CommandState

logger = logging.getLogger(__name__)


class PiUartBridge:
    """
    Build and send velocity frames to the Pico.

    Frame layout:
        START1 START2 MSG_ID LEN_H LEN_L PAYLOAD CHECKSUM
        START1, START2: 0xAA, 0x55
        MSG_ID (velocity): 0x01
        PAYLOAD: float32 linear_mps, float32 angular_rps (big-endian)
        CHECKSUM: sum(MSG_ID, LEN_H, LEN_L, PAYLOAD bytes) & 0xFF
    """

    START1 = 0xAA
    START2 = 0x55
    MSG_ID_VELOCITY = 0x01
    PAYLOAD_FMT = "!ff"
    PAYLOAD_LEN = struct.calcsize(PAYLOAD_FMT)
    MSG_ID_TELEMETRY = 0x02
    TELEMETRY_FMT = "!fffffffffff"
    TELEMETRY_LEN = struct.calcsize(TELEMETRY_FMT)

    def __init__(
        self,
        port: str = "/dev/ttyAMA0",
        baud: int = 115_200,
        heartbeat_s: float = 0.05,
        reconnect_interval_s: float = 1.0,
        max_linear_mps: float = 0.6,
        max_angular_rps: float = 2.0,
    ) -> None:
        self.port = port
        self.baud = baud
        self.heartbeat_s = heartbeat_s
        self.reconnect_interval_s = reconnect_interval_s
        self.max_linear_mps = max_linear_mps
        self.max_angular_rps = max_angular_rps

        self._ser: Optional[serial.Serial] = None
        self._next_reconnect_ts: float = 0.0
        self._last_send_ts: float = 0.0
        self._last_sent: Optional[Tuple[float, float]] = None

    def step(self, cmd_state: CommandState) -> None:
        """
        Send the latest velocity command. Always sends on change, and at least
        once per heartbeat interval even if unchanged.
        """
        now = time.monotonic()
        ser = self._ensure_serial(now)
        if ser is None:
            return

        v_cmd, w_cmd, _ = cmd_state.get_current_command()
        v_cmd, w_cmd = self._clamp(v_cmd, w_cmd)

        should_send = self._last_sent is None
        if self._last_sent is not None:
            dv = abs(v_cmd - self._last_sent[0])
            dw = abs(w_cmd - self._last_sent[1])
            if dv > 1e-4 or dw > 1e-4:
                should_send = True
            elif (now - self._last_send_ts) >= self.heartbeat_s:
                should_send = True

        if should_send:
            self._send_velocity(ser, v_cmd, w_cmd)

        # Try to read incoming telemetry
        self._read_telemetry(ser, cmd_state)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_serial(self, now: float) -> Optional[serial.Serial]:
        if self._ser is not None and self._ser.is_open:
            return self._ser

        if now < self._next_reconnect_ts:
            return None

        try:
            self._ser = serial.Serial(self.port, self.baud, timeout=0)
            logger.info("Connected to UART device %s @ %d", self.port, self.baud)
        except SerialException as exc:
            logger.warning("UART open failed (%s); retrying in %.1fs", exc, self.reconnect_interval_s)
            self._ser = None

        self._next_reconnect_ts = now + self.reconnect_interval_s
        return self._ser

    def _clamp(self, v: float, w: float) -> Tuple[float, float]:
        v_clamped = max(-self.max_linear_mps, min(self.max_linear_mps, v))
        w_clamped = max(-self.max_angular_rps, min(self.max_angular_rps, w))
        return v_clamped, w_clamped

    def _calc_checksum(self, msg_id: int, length: int, payload: bytes) -> int:
        len_hi = (length >> 8) & 0xFF
        len_lo = length & 0xFF
        return (msg_id + len_hi + len_lo + sum(payload)) & 0xFF

    def _build_packet(self, msg_id: int, payload: bytes) -> bytes:
        length = len(payload)
        len_hi = (length >> 8) & 0xFF
        len_lo = length & 0xFF
        header = bytes([self.START1, self.START2, msg_id, len_hi, len_lo])
        chk = self._calc_checksum(msg_id, length, payload)
        return header + payload + bytes([chk])

    def _send_velocity(self, ser: serial.Serial, v_cmd: float, w_cmd: float) -> None:
        payload = struct.pack(self.PAYLOAD_FMT, v_cmd, w_cmd)
        frame = self._build_packet(self.MSG_ID_VELOCITY, payload)

        try:
            ser.write(frame)
            self._last_send_ts = time.monotonic()
            self._last_sent = (v_cmd, w_cmd)
        except SerialException as exc:
            logger.warning("UART write failed (%s); closing serial", exc)
            try:
                ser.close()
            finally:
                self._ser = None

    def _read_telemetry(self, ser: serial.Serial, cmd_state: CommandState) -> None:
        """
        Non-blocking read for telemetry frames from Pico.
        """
        try:
            # Check if there's data available
            if ser.in_waiting < 7:  # Minimum frame size: START1 START2 MSG_ID LEN_H LEN_L PAYLOAD_MIN CHECKSUM
                return

            # Read header
            header = ser.read(5)
            if len(header) != 5:
                return

            start1, start2, msg_id, len_hi, len_lo = header
            if start1 != self.START1 or start2 != self.START2:
                logger.warning("Invalid frame start bytes: %02x %02x", start1, start2)
                return

            length = (len_hi << 8) | len_lo
            if length != self.TELEMETRY_LEN:
                logger.warning("Unexpected telemetry payload length: %d", length)
                return

            # Read payload and checksum
            payload_and_chk = ser.read(length + 1)
            if len(payload_and_chk) != length + 1:
                logger.warning("Incomplete telemetry frame")
                return

            payload = payload_and_chk[:-1]
            chk = payload_and_chk[-1]

            # Verify checksum
            expected_chk = self._calc_checksum(msg_id, length, payload)
            if chk != expected_chk:
                logger.warning("Telemetry checksum mismatch: got %02x, expected %02x", chk, expected_chk)
                return

            # Unpack telemetry
            if msg_id == self.MSG_ID_TELEMETRY:
                telemetry = struct.unpack(self.TELEMETRY_FMT, payload)
                cmd_state.update_telemetry(*telemetry)
                logger.debug("Received telemetry: %s", telemetry)

        except SerialException as exc:
            logger.warning("UART read failed (%s); closing serial", exc)
            try:
                ser.close()
            finally:
                self._ser = None
        except struct.error as exc:
            logger.warning("Telemetry unpack failed (%s)", exc)


def control_loop(
    cmd_state: CommandState,
    period_s: float = 0.02,
    port: str = "/dev/ttyAMA0",
    baud: int = 115_200,
    heartbeat_s: float = 0.05,
    reconnect_interval_s: float = 1.0,
    max_linear_mps: float = 0.6,
    max_angular_rps: float = 2.0,
) -> None:
    """
    Blocking loop that continuously pushes velocity commands over UART.
    """
    bridge = PiUartBridge(
        port=port,
        baud=baud,
        heartbeat_s=heartbeat_s,
        reconnect_interval_s=reconnect_interval_s,
        max_linear_mps=max_linear_mps,
        max_angular_rps=max_angular_rps,
    )

    while True:
        bridge.step(cmd_state)
        time.sleep(period_s)
