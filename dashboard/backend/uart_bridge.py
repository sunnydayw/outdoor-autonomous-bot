# backend/uart_bridge.py
"""
Pi-side UART bridge that speaks the same framing/proto as the Pico.

Key behaviors:
- Clamps v/w to indoor-safe limits before sending.
- Periodic heartbeat so the Pico watchdog sees activity even when idle.
- Automatic reconnect/backoff if the serial device disappears.

"""
from __future__ import annotations

import logging
from pathlib import Path
import sys
import time
from typing import Optional, Tuple

import serial
from serial import SerialException

from .command_state import CommandState, ControlMode

logger = logging.getLogger(__name__)

# Make the Pico proto module importable (shared definitions).
PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROTO_DIR = PROJECT_ROOT / "robot" / "Raspberry-Pi-Pico-2"
if str(PROTO_DIR) not in sys.path:
    sys.path.append(str(PROTO_DIR))
try:
    import proto  # type: ignore
except ImportError as exc:  # pragma: no cover - exercised at runtime
    raise RuntimeError(f"Unable to import proto definitions from {PROTO_DIR}") from exc


class PiUartBridge:
    """
    Handles UART framing and outbound velocity commands to the Pico.
    """

    START1 = 0xAA
    START2 = 0x55
    MSG_ID_VELOCITY_CMD = 0x01

    def __init__(
        self,
        port: str = "/dev/ttyACM0",
        baud: int = 115_200,
        heartbeat_s: float = 0.5,
        reconnect_interval_s: float = 2.0,
        max_linear_mps: float = 0.6,
        max_angular_rps: float = 2.0,
        # max_linear_accel: float = 1.0,
        # max_angular_accel: float = 2.0,
    ) -> None:
        """
        :param port: UART device path as seen by the Pi (map in docker run).
        :param baud: UART baud rate.
        :param heartbeat_s: Period to resend the latest command to keep the Pico alive.
        :param reconnect_interval_s: Minimum delay between reconnect attempts.
        :param max_linear_mps: Clamp for v_cmd (indoor-safe default).
        :param max_angular_rps: Clamp for w_cmd (indoor-safe default).
        :param max_linear_accel: Included in proto payload; Pico uses for shaping.
        :param max_angular_accel: Included in proto payload.
        """
        self.port = port
        self.baud = baud
        self.heartbeat_s = heartbeat_s
        self.reconnect_interval_s = reconnect_interval_s
        self.max_linear_mps = max_linear_mps
        self.max_angular_rps = max_angular_rps

        self._ser: Optional[serial.Serial] = None
        self._next_reconnect_ts: float = 0.0
        self._seq: int = 0
        self._cmd_id: int = 0
        self._last_send_ts: float = 0.0
        self._last_sent: Tuple[float, float, Optional[ControlMode]] = (0.0, 0.0, None)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def step(self, cmd_state: CommandState) -> None:
        """
        Attempt to send the latest command over UART (with heartbeat).
        """
        now = time.monotonic()
        ser = self._ensure_serial(now)
        if ser is None:
            time.sleep(self.reconnect_interval_s)
            return

        v_cmd, w_cmd, mode = cmd_state.get_current_command()
        v_cmd, w_cmd = self._clamp(v_cmd, w_cmd)

        should_send = self._heartbeat_due(now) or mode != self._last_sent[2]
        if mode != ControlMode.IDLE:
            # Send on change or heartbeat while active.
            dv = abs(v_cmd - self._last_sent[0])
            dw = abs(w_cmd - self._last_sent[1])
            if dv > 1e-3 or dw > 1e-3:
                should_send = True
            if should_send:
                self._send_velocity(ser, v_cmd, w_cmd, cmd_type=proto.CommandType.SET_VELOCITY, mode=mode)
        else:
            # Mode idle → send STOP heartbeat occasionally.
            if should_send:
                self._send_velocity(ser, 0.0, 0.0, cmd_type=proto.CommandType.STOP, mode=mode)

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

    def _heartbeat_due(self, now: float) -> bool:
        return (now - self._last_send_ts) >= self.heartbeat_s

    def _clamp(self, v: float, w: float) -> Tuple[float, float]:
        v_clamped = max(-self.max_linear_mps, min(self.max_linear_mps, v))
        w_clamped = max(-self.max_angular_rps, min(self.max_angular_rps, w))
        return v_clamped, w_clamped

    def _next_seq(self) -> int:
        self._seq = (self._seq + 1) & 0xFFFFFFFF
        return self._seq

    def _next_cmd_id(self) -> int:
        self._cmd_id = (self._cmd_id + 1) & 0xFFFFFFFF
        return self._cmd_id

    def _calc_checksum(self, data: bytes) -> int:
        chk = 0
        for b in data:
            chk = (chk + b) & 0xFF
        return chk

    def _build_packet(self, msg_id: int, payload: bytes) -> bytes:
        length = len(payload)
        len_hi = (length >> 8) & 0xFF
        len_lo = length & 0xFF
        header = bytes([self.START1, self.START2, msg_id, len_hi, len_lo])
        chk = self._calc_checksum(header[2:] + payload)
        return header + payload + bytes([chk])

    def _send_velocity(
        self,
        ser: serial.Serial,
        v_cmd: float,
        w_cmd: float,
        cmd_type: int,
        mode: ControlMode,
    ) -> None:
        payload = proto.VelocityCommandPayload(
            header=proto.Header.now(self._next_seq()),
            cmd_type=cmd_type,
            v=v_cmd,
            omega=w_cmd,
            command_id=self._next_cmd_id(),
        )
        frame = self._build_packet(self.MSG_ID_VELOCITY_CMD, payload.to_bytes())

        try:
            ser.write(frame)
            self._last_send_ts = time.monotonic()
            self._last_sent = (v_cmd, w_cmd, mode)
        except SerialException as exc:
            logger.warning("UART write failed (%s); closing serial", exc)
            try:
                ser.close()
            finally:
                self._ser = None


def control_loop(
    cmd_state: CommandState,
    period_s: float = 0.02,
    port: str = "/dev/ttyACM0",
    baud: int = 115_200,
    heartbeat_s: float = 0.5,
    reconnect_interval_s: float = 2.0,
    max_linear_mps: float = 0.6,
    max_angular_rps: float = 2.0,
) -> None:
    """
    Blocking loop that:
      - Reads current (v, w, mode) from cmd_state.
      - Clamps to safe indoor limits.
      - Sends commands/heartbeats to the Pico over UART.

    Runs forever; caller is expected to start it in a background thread.
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
