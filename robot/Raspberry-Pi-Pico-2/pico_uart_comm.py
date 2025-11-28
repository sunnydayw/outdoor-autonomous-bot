# pico_uart_comm.py
#
# Low-level UART link between Pico and Pi 5 using proto.py structures.
#
# Public usage:
#   tele = PicoLowLevelLink(controller=drive, ...)
#   loop:
#       tele.poll_cmd()   # handle incoming commands from Pi
#       tele.send()       # send telemetry (drive RPM and battery voltage)
#
# Expected external interface:
#   controller: DriveSystem or DiffDriveController-like, with:
#       - update_cmd_vel(v, w)          # apply high-level velocity command
#       - get_drive_feedback() -> dict (optional), with keys:
#             {
#               "left_rpm", "right_rpm"
#             }
#
# If get_drive_feedback() is not present or missing keys, RPMs default to 0.0.

from machine import UART, Pin, ADC
import time
import proto


class PicoLowLevelLink:
    """
    UART framing + command/telemetry logic between Pico and Pi 5.

    This class deals only with:
        - Velocity commands from Pi (SET_VELOCITY, STOP).
        - Drive feedback: left/right RPM.
        - Battery voltage.

    All timestamps are carried in proto.Header (seq + stamp).
    """

    # UART framing (big-endian style)
    START1 = 0xAA
    START2 = 0x55

    # Message IDs
    MSG_ID_VELOCITY_CMD   = 0x01
    MSG_ID_DRIVE_FEEDBACK = 0x10
    MSG_ID_BATTERY_STATUS = 0x11

    def __init__(
        self,
        controller,
        uart_id=0,
        baud=115200,
        tx_pin=0,
        rx_pin=1,
        battery_adc_pin=None,
        debug=False,
        fb_period_ms=20,
        batt_period_ms=200,
        adc_divider_ratio=11.0,
    ):
        """
        :param controller:    Object with at least update_cmd_vel(v, w).
                              Optionally get_drive_feedback() for real RPMs.
                              (DriveSystem works here.)
        :param uart_id:       UART bus index (0 or 1 on Pico).
        :param baud:          UART baud rate.
        :param tx_pin, rx_pin:Gpios for UART TX/RX.
        :param battery_adc_pin: Pico ADC pin for battery sense (or None to disable).
        :param debug:         If True, prints debug info on parse errors, etc.
        :param fb_period_ms:  Drive feedback send period in ms (None to disable).
        :param batt_period_ms:Battery status send period in ms (None to disable).
        :param adc_divider_ratio: Voltage divider factor between battery and ADC.
        """
        self.ctrl = controller
        self.debug = debug

        # --- UART setup ---
        self.uart = UART(uart_id, baudrate=baud, tx=Pin(tx_pin), rx=Pin(rx_pin))
        self._rx_buf = bytearray()

        # Optional battery ADC
        self.adc = ADC(Pin(battery_adc_pin)) if battery_adc_pin is not None else None
        self._adc_divider = float(adc_divider_ratio)

        # TX sequence counter (Pico -> Pi 5)
        self._seq_out = 0

        # Telemetry timing
        now = time.ticks_ms()
        self._last_fb_ms = now
        self._last_batt_ms = now

        # Periods (ms). If any is None, that telemetry type is disabled.
        self._fb_period_ms = fb_period_ms
        self._batt_period_ms = batt_period_ms

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def poll_cmd(self) -> None:
        """
        Non-blocking: read UART, parse frames, handle incoming commands.

        Call this frequently in the main loop.
        """
        self._read_bytes()

        while True:
            msg_id, payload = self._try_extract_packet()
            if msg_id is None:
                break

            if msg_id == self.MSG_ID_VELOCITY_CMD:
                self._handle_velocity_command(payload)
            else:
                if self.debug:
                    print("PicoLowLevelLink: unknown msg_id:", msg_id)

    def send(self) -> None:
        """
        Send outgoing telemetry frames as needed based on time.

        Call this periodically in the main loop (e.g. every 10–20 ms).
        """
        now = time.ticks_ms()

        # Drive feedback (Pico -> Pi), e.g. ~50 Hz
        if (self._fb_period_ms is not None) and \
           (time.ticks_diff(now, self._last_fb_ms) >= self._fb_period_ms):
            try:
                self._send_drive_feedback()
            except Exception as e:
                if self.debug:
                    print("send_drive_feedback error:", e)
            self._last_fb_ms = now

        # Battery status, e.g. ~5 Hz
        if (self._batt_period_ms is not None) and \
           (time.ticks_diff(now, self._last_batt_ms) >= self._batt_period_ms):
            try:
                self._send_battery_status()
            except Exception as e:
                if self.debug:
                    print("send_battery_status error:", e)
            self._last_batt_ms = now

    # ------------------------------------------------------------------
    # Internal helpers: UART framing
    # ------------------------------------------------------------------

    def _calc_checksum(self, data: bytes) -> int:
        """Simple checksum: sum of bytes modulo 256."""
        s = 0
        for b in data:
            s = (s + b) & 0xFF
        return s

    def _build_packet(self, msg_id: int, payload: bytes) -> bytes:
        """
        Build a framed UART packet:

            START1 START2 MSG_ID LEN_H LEN_L PAYLOAD... CHECKSUM
        """
        length = len(payload)
        len_hi = (length >> 8) & 0xFF
        len_lo = length & 0xFF
        header = bytes([self.START1, self.START2, msg_id, len_hi, len_lo])
        chk = self._calc_checksum(header[2:] + payload)
        return header + payload + bytes([chk])

    def _read_bytes(self) -> None:
        """Read any available bytes from UART into the internal RX buffer."""
        data = self.uart.read()
        if data:
            self._rx_buf.extend(data)

    def _try_extract_packet(self):
        """
        Try to extract one complete frame from self._rx_buf.

        Frame layout:
            START1 START2 MSG_ID LEN_H LEN_L PAYLOAD... CHECKSUM

        Returns:
            (msg_id, payload_bytes) or (None, None) if no complete frame.
        """
        buf = self._rx_buf

        # Hunt for start bytes
        while len(buf) >= 2 and not (buf[0] == self.START1 and buf[1] == self.START2):
            buf.pop(0)

        # Need at least start + msg_id + length (5 bytes)
        if len(buf) < 5:
            return None, None

        msg_id = buf[2]
        length = (buf[3] << 8) | buf[4]
        total_len = 2 + 1 + 2 + length + 1  # start1,start2,msg_id,len,len,payload,chk

        if len(buf) < total_len:
            return None, None  # incomplete frame

        frame = buf[:total_len]
        del buf[:total_len]

        payload = frame[5:-1]
        chk = frame[-1]
        calc = self._calc_checksum(frame[2:-1])
        if chk != calc:
            if self.debug:
                print("PicoLowLevelLink: checksum error, got", chk, "calc", calc)
            return None, None

        return msg_id, payload

    # ------------------------------------------------------------------
    # Command handlers
    # ------------------------------------------------------------------

    def _handle_velocity_command(self, payload: bytes) -> None:
        """Handle VelocityCommand from Pi 5."""
        try:
            cmd, _ = proto.VelocityCommandPayload.from_bytes(payload, 0)
        except Exception as e:
            if self.debug:
                print("VelocityCommand parse error:", e)
            return

        if cmd.cmd_type == proto.CommandType.SET_VELOCITY:
            self.ctrl.update_cmd_vel(cmd.v, cmd.omega)
        elif cmd.cmd_type == proto.CommandType.STOP:
            self.ctrl.update_cmd_vel(0.0, 0.0)

        if self.debug:
            print("VelocityCommand: seq={} type={} v={} w={} id={}".format(
                cmd.header.seq, cmd.cmd_type, cmd.v, cmd.omega, cmd.command_id))

    # ------------------------------------------------------------------
    # Telemetry senders
    # ------------------------------------------------------------------

    def _next_seq(self) -> int:
        """Increment and return the next sequence number."""
        self._seq_out = (self._seq_out + 1) & 0xFFFFFFFF
        return self._seq_out

    def _send_drive_feedback(self) -> None:
        """Send DriveFeedbackPayload to the Pi (left/right RPM)."""
        seq = self._next_seq()
        header = proto.Header.now(seq)

        left_rpm, right_rpm = self._fetch_rpms()

        payload_obj = proto.DriveFeedbackPayload(
            header=header,
            left_rpm=left_rpm,
            right_rpm=right_rpm,
        )
        pkt = self._build_packet(self.MSG_ID_DRIVE_FEEDBACK, payload_obj.to_bytes())
        self.uart.write(pkt)

    def _fetch_rpms(self):
        """
        Get left/right RPM from controller, with robust fallback.

        Expected from controller.get_drive_feedback():
            { "left_rpm": float, "right_rpm": float }
        """
        left_rpm = 0.0
        right_rpm = 0.0

        if hasattr(self.ctrl, "get_drive_feedback"):
            try:
                fb = self.ctrl.get_drive_feedback() or {}
                left_rpm = float(fb.get("left_rpm", left_rpm))
                right_rpm = float(fb.get("right_rpm", right_rpm))
            except Exception as e:
                if self.debug:
                    print("get_drive_feedback error:", e)

        return left_rpm, right_rpm

    def _read_battery_voltage(self) -> float:
        """
        Read battery voltage from ADC.

        Returns:
            pack_voltage [V], or 0.0 if no ADC configured.
        """
        if self.adc is None:
            return 0.0

        raw = self.adc.read_u16()  # 0..65535
        v_adc = (raw / 65535.0) * 3.3
        v_pack = v_adc * self._adc_divider
        return v_pack

    def _send_battery_status(self) -> None:
        """Send BatteryStatusPayload to the Pi (voltage only)."""
        seq = self._next_seq()
        header = proto.Header.now(seq)

        voltage = float(self._read_battery_voltage())
        payload_obj = proto.BatteryStatusPayload(
            header=header,
            voltage=voltage,
        )
        pkt = self._build_packet(self.MSG_ID_BATTERY_STATUS, payload_obj.to_bytes())
        self.uart.write(pkt)
