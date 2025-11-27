# pico_uart_comm.py
#
# Low-level UART link between Pico and Pi 5 using proto.py structures.
# Inspired by RobotTelemetry: exposes a simple class with:
#   tele.poll_cmd()
#   tele.send()
#
# Expected external interfaces (you can adjust to your project):
#   - controller.update_cmd_vel(v, w)        # apply high-level velocity command
#   - controller.get_drive_feedback() -> dict with keys:
#         v_meas, omega_meas, left_ticks, right_ticks, left_rpm, right_rpm, status_flags
#     (If not present, we fall back to last commanded v, w and fake counters.)
#   - estop_manager (optional) with:
#         trigger_estop(source)
#         clear_estop_if_safe() -> bool
#         get_estop_state() -> dict with keys: estop_active, estop_source
#
# If you don't have these yet, you can stub them and gradually wire real logic in.

from machine import UART, Pin, ADC
import time
import struct
import proto


class PicoLowLevelLink:
    # UART framing (big-endian style)
    START1 = 0xAA
    START2 = 0x55

    # Message IDs
    MSG_ID_VELOCITY_CMD    = 0x01
    MSG_ID_CLEAR_ESTOP_CMD = 0x02

    MSG_ID_DRIVE_FEEDBACK  = 0x10
    MSG_ID_BATTERY_STATUS  = 0x11
    MSG_ID_LOWLEVEL_STATUS = 0x12

    def __init__(self,
                 controller,
                 uart_id=0,
                 baud=115200,
                 tx_pin=0,
                 rx_pin=1,
                 battery_adc_pin=None,
                 estop_manager=None,
                 debug=False):
        """
        controller    : object with at least update_cmd_vel(v, w).
                        Optionally get_drive_feedback() for real telemetry.
        estop_manager : optional object, see header comment.
        battery_adc_pin : Pico ADC pin number for battery sense, or None.
        """
        self.ctrl = controller
        self.debug = debug
        self.estop_mgr = estop_manager

        self.uart = UART(uart_id, baudrate=baud, tx=Pin(tx_pin), rx=Pin(rx_pin))
        self._rx_buf = bytearray()

        # Optional battery ADC
        self.adc = ADC(Pin(battery_adc_pin)) if battery_adc_pin is not None else None

        # TX sequence counter (Pico -> Pi5)
        self._seq_out = 0

        # Last commanded velocities (fallback if no real feedback yet)
        self._last_cmd_v = 0.0
        self._last_cmd_omega = 0.0

        # Telemetry timing
        self._last_fb_ms = time.ticks_ms()
        self._last_batt_ms = time.ticks_ms()
        self._last_ll_ms = time.ticks_ms()

        # Periods (ms)
        self._fb_period_ms = 20     # ~50 Hz drive feedback
        self._batt_period_ms = 200  # 5 Hz battery
        self._ll_period_ms = 200    # 5 Hz low-level status

    # ---------- Public API ----------

    def poll_cmd(self):
        """Non-blocking: read UART, parse frames, handle incoming commands."""
        self._read_bytes()

        while True:
            msg_id, payload = self._try_extract_packet()
            if msg_id is None:
                break

            if msg_id == self.MSG_ID_VELOCITY_CMD:
                self._handle_velocity_command(payload)
            elif msg_id == self.MSG_ID_CLEAR_ESTOP_CMD:
                self._handle_clear_estop(payload)
            else:
                # Unknown/unhandled message
                if self.debug:
                    print("PicoLowLevelLink: unknown msg_id:", msg_id)

    def send(self):
        """Send outgoing telemetry frames as needed based on time."""
        now = time.ticks_ms()

        # Drive feedback ~50 Hz
        if time.ticks_diff(now, self._last_fb_ms) >= self._fb_period_ms:
            try:
                self._send_drive_feedback()
            except Exception as e:
                if self.debug:
                    print("send_drive_feedback error:", e)
            self._last_fb_ms = now

        # Battery status ~5 Hz
        if time.ticks_diff(now, self._last_batt_ms) >= self._batt_period_ms:
            try:
                self._send_battery_status()
            except Exception as e:
                if self.debug:
                    print("send_battery_status error:", e)
            self._last_batt_ms = now

        # Low-level status ~5 Hz
        if time.ticks_diff(now, self._last_ll_ms) >= self._ll_period_ms:
            try:
                self._send_lowlevel_status()
            except Exception as e:
                if self.debug:
                    print("send_lowlevel_status error:", e)
            self._last_ll_ms = now

    # ---------- Internal helpers: UART framing ----------
    def _calc_checksum(self, data):
        """Simple checksum: sum of bytes modulo 256."""
        s = 0
        for b in data:
            s = (s + b) & 0xFF
        return s

    def _build_packet(self, msg_id, payload):
        length = len(payload)
        len_hi = (length >> 8) & 0xFF
        len_lo = length & 0xFF
        header = bytes([self.START1, self.START2, msg_id, len_hi, len_lo])
        chk = self._calc_checksum(header[2:] + payload)
        return header + payload + bytes([chk])

    def _read_bytes(self):
        data = self.uart.read()
        if data:
            self._rx_buf.extend(data)

    def _try_extract_packet(self):
        """
        Look in self._rx_buf, try to extract one complete frame.

        Frame layout:
            START1 START2 MSG_ID LEN_H LEN_L PAYLOAD... CHECKSUM

        Returns (msg_id, payload_bytes) or (None, None).
        """
        buf = self._rx_buf

        # hunt for start bytes
        while len(buf) >= 2 and not (buf[0] == self.START1 and buf[1] == self.START2):
            buf.pop(0)

        if len(buf) < 5:
            return None, None  # need at least start+msg_id+len

        msg_id = buf[2]
        length = (buf[3] << 8) | buf[4]
        total_len = 2 + 1 + 2 + length + 1  # start1,start2,msg_id,len,len,payload,chk

        if len(buf) < total_len:
            return None, None  # incomplete

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

    # ---------- Command handlers ----------

    def _handle_velocity_command(self, payload):
        try:
            cmd, _ = proto.VelocityCommandPayload.from_bytes(payload, 0)
        except Exception as e:
            if self.debug:
                print("VelocityCommand parse error:", e)
            return

        # store last commanded velocities for fallback telemetry
        self._last_cmd_v = cmd.v
        self._last_cmd_omega = cmd.omega

        # E-stop inside VelocityCommand: EMERGENCY_STOP
        if cmd.cmd_type == proto.CommandType.SET_VELOCITY:
            # if estop is active, you may want to ignore or clamp to zero
            self.ctrl.update_cmd_vel(cmd.v, cmd.omega)

        elif cmd.cmd_type == proto.CommandType.STOP:
            self.ctrl.update_cmd_vel(0.0, 0.0)

        elif cmd.cmd_type == proto.CommandType.EMERGENCY_STOP:
            # Immediately stop motors
            self.ctrl.update_cmd_vel(0.0, 0.0)
            # Optionally latch estop in estop_manager
            if self.estop_mgr is not None:
                try:
                    self.estop_mgr.trigger_estop(source=2)  # 2 = SW command
                except Exception:
                    # best-effort, avoid crashing control loop
                    pass

        if self.debug:
            print("VelocityCommand: seq={} type={} v={} w={} id={}".format(
                cmd.header.seq, cmd.cmd_type, cmd.v, cmd.omega, cmd.command_id))

    def _handle_clear_estop(self, payload):
        # ClearEstopPayload is optional in proto; only handle if defined
        if not hasattr(proto, "ClearEstopPayload"):
            if self.debug:
                print("ClearEstopPayload not defined in proto.py")
            return

        try:
            msg, _ = proto.ClearEstopPayload.from_bytes(payload, 0)
        except Exception as e:
            if self.debug:
                print("ClearEstop parse error:", e)
            return

        if self.debug:
            print("ClearEstop request: seq={} req_id={}".format(
                msg.header.seq, msg.request_id))

        if self.estop_mgr is not None:
            try:
                ok = self.estop_mgr.clear_estop_if_safe()
                if self.debug:
                    print("ClearEstop result:", ok)
            except Exception as e:
                if self.debug:
                    print("clear_estop_if_safe error:", e)

    # ---------- Telemetry senders ----------

    def _next_seq(self):
        self._seq_out = (self._seq_out + 1) & 0xFFFFFFFF
        return self._seq_out

    def _send_drive_feedback(self):
        seq = self._next_seq()
        header = proto.Header.now(seq)

        fb = self._fetch_drive_feedback()

        payload_obj = proto.DriveFeedbackPayload(
            header=header,
            v_meas=fb["v_meas"],
            omega_meas=fb["omega_meas"],
            left_ticks=fb["left_ticks"],
            right_ticks=fb["right_ticks"],
            left_rpm=fb["left_rpm"],
            right_rpm=fb["right_rpm"],
            status_flags=fb["status_flags"],
        )
        pkt = self._build_packet(self.MSG_ID_DRIVE_FEEDBACK, payload_obj.to_bytes())
        self.uart.write(pkt)

    def _fetch_drive_feedback(self):
        base = {
            "v_meas": self._last_cmd_v,
            "omega_meas": self._last_cmd_omega,
            "left_ticks": 0,
            "right_ticks": 0,
            "left_rpm": 0.0,
            "right_rpm": 0.0,
            "status_flags": 0,
        }

        if hasattr(self.ctrl, "get_drive_feedback"):
            try:
                fb = self.ctrl.get_drive_feedback() or {}
                for key in tuple(base.keys()):
                    if key in fb:
                        base[key] = fb[key]
            except Exception as e:
                if self.debug:
                    print("get_drive_feedback error:", e)
        return base

    def _read_battery(self):
        """Return (voltage, current, soc, temperature, status_flags). Placeholder model."""
        if self.adc is None:
            # no ADC; just return zeros
            return 0.0, 0.0, 0.0, 0.0, 0

        # Simple example: read ADC ~0..3.3V, assume divider factor for pack voltage.
        raw = self.adc.read_u16()  # 0..65535
        v_adc = (raw / 65535.0) * 3.3
        # Adjust this factor to your actual divider
        divider = 11.0
        v_pack = v_adc * divider

        # We don't know true current / SoC / temperature yet; placeholders:
        current = 0.0
        soc = 0.0
        temp = 0.0

        flags = 0
        # Example thresholds in volts; tune these:
        if v_pack < 10.5:
            flags |= proto.BatteryStatusFlags.LOW_BATTERY_WARNING
        if v_pack < 10.0:
            flags |= proto.BatteryStatusFlags.CRITICALLY_LOW

        return v_pack, current, soc, temp, flags

    def _send_battery_status(self):
        seq = self._next_seq()
        header = proto.Header.now(seq)

        voltage, current, soc, temp, flags = self._read_battery()
        payload_obj = proto.BatteryStatusPayload(
            header=header,
            voltage=float(voltage),
            current=float(current),
            soc=float(soc),
            temperature=float(temp),
            status_flags=flags,
        )
        pkt = self._build_packet(self.MSG_ID_BATTERY_STATUS, payload_obj.to_bytes())
        self.uart.write(pkt)

    def _send_lowlevel_status(self):
        seq = self._next_seq()
        header = proto.Header.now(seq)

        fault_flags = 0
        warning_flags = 0
        estop_active = 0
        estop_source = 0
        uptime_ms = time.ticks_ms() & 0xFFFFFFFF

        # If you have a real estop_manager, ask it:
        if self.estop_mgr is not None and hasattr(self.estop_mgr, "get_estop_state"):
            try:
                st = self.estop_mgr.get_estop_state()
                if st is not None:
                    estop_active = 1 if st.get("estop_active", False) else 0
                    estop_source = st.get("estop_source", 0)
            except Exception as e:
                if self.debug:
                    print("get_estop_state error:", e)

        # You can also set fault_flags/warning_flags here based on your motor driver state.

        payload_obj = proto.LowLevelStatusPayload(
            header=header,
            fault_flags=fault_flags,
            warning_flags=warning_flags,
            estop_active=estop_active,
            estop_source=estop_source,
            uptime_ms=uptime_ms,
        )
        pkt = self._build_packet(self.MSG_ID_LOWLEVEL_STATUS, payload_obj.to_bytes())
        self.uart.write(pkt)


# # ---------- Example usage skeleton ----------

# if __name__ == "__main__":
#     # These should be your real objects
#     class DummyController:
#         def __init__(self):
#             self.v = 0.0
#             self.w = 0.0

#         def update_cmd_vel(self, v, w):
#             self.v = v
#             self.w = w

#         def get_drive_feedback(self):
#             # Minimal fake, just to demo
#             return {
#                 "v_meas": self.v,
#                 "omega_meas": self.w,
#                 "left_ticks": 0,
#                 "right_ticks": 0,
#                 "left_rpm": self.v * 60.0,
#                 "right_rpm": self.v * 60.0,
#                 "status_flags": 0x1,
#             }

#     ctrl = DummyController()
#     tele = PicoLowLevelLink(controller=ctrl,
#                             uart_id=0,
#                             baud=115200,
#                             tx_pin=0,
#                             rx_pin=1,
#                             battery_adc_pin=None,
#                             estop_manager=None,
#                             debug=True)

#     while True:
#         # 1) Handle incoming commands from Pi 5
#         tele.poll_cmd()

#         # 2) Run your motor control / PID loop here
#         #    (not shown; depends on your project)

#         # 3) Send telemetry to Pi 5 as needed
#         tele.send()

#         # Small sleep to avoid 100% CPU
#         time.sleep_ms(5)
