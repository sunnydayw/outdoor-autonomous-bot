# Minimal Pi -> Pico UART receiver for velocity commands only.
#
# Frame layout:
#   START1 START2 MSG_ID LEN_H LEN_L PAYLOAD CHECKSUM
#   START1/START2: 0xAA 0x55
#   MSG_ID (velocity): 0x01
#   PAYLOAD: float32 linear_mps, float32 angular_rps (big-endian)
#   CHECKSUM: sum(MSG_ID, LEN_H, LEN_L, PAYLOAD bytes) & 0xFF
#
# The Pico only listens; it never sends bytes back to the Pi.

import struct
from machine import UART, Pin


class PicoVelocityReceiver:
    START1 = 0xAA
    START2 = 0x55
    MSG_ID_VELOCITY = 0x01

    PAYLOAD_FMT = "!ff"
    PAYLOAD_LEN = struct.calcsize(PAYLOAD_FMT)

    def __init__(self, controller, uart_id=0, baud=115200, tx_pin=0, rx_pin=1, debug=False):
        self.ctrl = controller
        self.debug = debug
        self.uart = UART(uart_id, baudrate=baud, tx=Pin(tx_pin), rx=Pin(rx_pin))
        self._rx_buf = bytearray()

    def poll(self) -> None:
        """
        Read any available bytes and apply decoded velocity commands.
        Call this frequently from the main loop.
        """
        self._read_bytes()

        while True:
            parsed = self._try_extract_packet()
            if parsed is None:
                break

            linear, angular = parsed
            try:
                self.ctrl.set_cmd_vel(linear, angular)
            except Exception as exc:
                if self.debug:
                    print("update_cmd_vel failed:", exc)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _read_bytes(self) -> None:
        data = self.uart.read()
        if data:
            self._rx_buf.extend(data)

    def _try_extract_packet(self):
        """
        Return (linear, angular) when a complete velocity frame is present,
        otherwise None. Invalid frames are discarded.
        """
        buf = self._rx_buf

        # Align to start bytes
        while len(buf) >= 2 and not (buf[0] == self.START1 and buf[1] == self.START2):
            buf[:] = buf[1:]

        if len(buf) < 5:
            return None

        msg_id = buf[2]
        length = (buf[3] << 8) | buf[4]
        if length != self.PAYLOAD_LEN:
            # Length is wrong; drop the first byte to resync and try again.
            if self.debug:
                print("unexpected payload length header:", length)
            buf[:] = buf[1:]
            return None

        total_len = 2 + 1 + 2 + length + 1  # start bytes + msg_id + len + payload + checksum

        if len(buf) < total_len:
            return None

        frame = buf[:total_len]
        buf[:] = buf[total_len:]  # consume the frame

        chk = frame[-1]
        calc = sum(frame[2:-1]) & 0xFF
        if chk != calc:
            if self.debug:
                print("checksum mismatch (got {}, expected {})".format(chk, calc))
            return None

        if msg_id != self.MSG_ID_VELOCITY:
            if self.debug:
                print("unexpected msg_id:", msg_id)
            return None

        if length != self.PAYLOAD_LEN:
            if self.debug:
                print("unexpected payload length:", length)
            return None

        payload = frame[5:-1]
        try:
            linear, angular = struct.unpack(self.PAYLOAD_FMT, payload)
        except Exception as exc:
            if self.debug:
                print("payload unpack failed:", exc)
            return None

        return linear, angular
