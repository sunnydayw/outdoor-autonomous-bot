# Pico UART communication for velocity commands and telemetry.
#
# Frame layout:
#   START1 START2 MSG_ID LEN_H LEN_L PAYLOAD CHECKSUM
#   START1/START2: 0xAA 0x55
#   MSG_ID (velocity): 0x01
#   PAYLOAD: float32 linear_mps, float32 angular_rps (big-endian)
#   MSG_ID (telemetry): 0x02
#   PAYLOAD: 11 float32 values (big-endian)
#   CHECKSUM: sum(MSG_ID, LEN_H, LEN_L, PAYLOAD bytes) & 0xFF
#
# The Pico receives velocity commands and sends telemetry data.

import struct
from machine import UART, Pin


class PicoUARTComm:
    START1 = 0xAA
    START2 = 0x55
    MSG_ID_VELOCITY = 0x01
    MSG_ID_TELEMETRY = 0x02

    PAYLOAD_FMT_VELOCITY = "!ff"
    PAYLOAD_LEN_VELOCITY = struct.calcsize(PAYLOAD_FMT_VELOCITY)

    PAYLOAD_FMT_TELEMETRY = "!fffffffffff"
    PAYLOAD_LEN_TELEMETRY = struct.calcsize(PAYLOAD_FMT_TELEMETRY)

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

    def send_telemetry(self, left_target, right_target, left_actual, right_actual, battery, accel_x, accel_y, accel_z, gyro_x, gyro_y, gyro_z):
        """
        Send telemetry data to the Pi.
        """
        payload = struct.pack(self.PAYLOAD_FMT_TELEMETRY, left_target, right_target, left_actual, right_actual, battery, accel_x, accel_y, accel_z, gyro_x, gyro_y, gyro_z)
        length = len(payload)
        len_h = (length >> 8) & 0xFF
        len_l = length & 0xFF
        msg_id = self.MSG_ID_TELEMETRY
        header = bytes([self.START1, self.START2, msg_id, len_h, len_l])
        checksum = (msg_id + len_h + len_l + sum(payload)) & 0xFF
        frame = header + payload + bytes([checksum])
        self.uart.write(frame)

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
        if length != self.PAYLOAD_LEN_VELOCITY:
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

        if length != self.PAYLOAD_LEN_VELOCITY:
            if self.debug:
                print("unexpected payload length:", length)
            return None

        payload = frame[5:-1]
        try:
            linear, angular = struct.unpack(self.PAYLOAD_FMT_VELOCITY, payload)
        except Exception as exc:
            if self.debug:
                print("payload unpack failed:", exc)
            return None

        return linear, angular
