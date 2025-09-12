# robot_telemetry.py
import time, struct
from machine import UART, Pin, ADC
import config

# --- helpers for safe scaling to int16/uint16
def _to_i16(x):
    x = int(round(x))
    if x < -32768: x = -32768
    if x >  32767: x =  32767
    return x

def _to_u16(x):
    x = int(round(x))
    if x < 0: x = 0
    if x > 65535: x = 65535
    return x

class RobotTelemetry:
    """
    Compact telemetry + optional debug. Sends over UART and listens for cmd_vel.
    Designed for your Motor / DiffDriveController stack.
    """

    # delimiters
    TELEMETRY_START = 0xAA55
    CMD_START       = 0xCC33

    def __init__(self,
                 left_motor, right_motor, controller,
                 uart_id=1, baud=115200, tx_pin=8, rx_pin=9,
                 battery_adc_pin=None,
                 imu=None,         # pass an MPU6050 instance or None
                 debug=False):
        self.left  = left_motor
        self.right = right_motor
        self.ctrl  = controller
        self.uart  = UART(uart_id, baudrate=baud, tx=Pin(tx_pin), rx=Pin(rx_pin))
        self.msg_counter = 0
        self.debug = debug
        self.imu = imu

        # battery ADC (optional)
        adc_pin = battery_adc_pin if battery_adc_pin is not None else getattr(config, "BATTERY_ADC_PIN", None)
        self.adc = ADC(Pin(adc_pin)) if adc_pin is not None else None

        # small RX buffer for framing control packets
        self._rx_buf = bytearray()

        # Precomputed struct formats (little-endian)
        # Compact telemetry (34 bytes total):
        # <HBHIB 2h H 3h 3h 2h H
        #  ^  ^  ^   ^  ^  ^  ^ checksum (u16)
        #  |  |  |   |  |  |  +- v_mmps, w_mradps (i16 each)
        #  |  |  |   |  |  +---- gyro x,y,z (deci-dps, i16)
        #  |  |  |   |  +------- accel x,y,z (mg, i16)
        #  |  |  |   +---------- battery mV (u16)
        #  |  |  +-------------- wheel RPM L,R (i16)
        #  |  +----------------- timestamp (u32), timeout flag (u8)
        #  +-------------------- start (u16), length (u8), counter (u16)
        self._fmt_tel_wo_crc = '<HBHIB2hH3h3h2h'
        self._TEL_LEN = 34

        # Simple cmd_vel control: <HBH 2h H> = 11 bytes
        # start (u16), len (u8), count (u16), v_mmps (i16), w_mradps (i16), checksum (u16)
        self._fmt_cmd = '<HBH2hH'
        self._CMD_LEN = 11

    # ---------- public API ----------
    def send(self):
        """Send either compact or debug message."""
        if self.debug:
            self._send_debug()
        else:
            self._send_compact()

    def poll_cmd(self):
        """Non-blocking: read any available bytes, parse frames, update cmd_vel."""
        if self.uart.any():
            self._rx_buf += self.uart.read() or b''

        # hunt for start delimiter
        while True:
            if len(self._rx_buf) < 3:
                return  # need at least start(2)+len(1)

            # scan for 0xCC33 (little-endian bytes 0x33,0xCC)
            idx = self._rx_buf.find(b'\x33\xCC')
            if idx < 0:
                # no start found; drop old bytes, keep tail
                if len(self._rx_buf) > 64:
                    self._rx_buf = self._rx_buf[-64:]
                return
            # align to start
            if idx > 0:
                self._rx_buf = self._rx_buf[idx:]

            if len(self._rx_buf) < self._CMD_LEN:
                return  # not enough yet

            frame = self._rx_buf[:self._CMD_LEN]
            self._rx_buf = self._rx_buf[self._CMD_LEN:]

            try:
                start, length, count, v_mmps, w_mradps, crc_recv = struct.unpack(self._fmt_cmd, frame)
            except Exception:
                print("Unpack err:", e, "len", len(frame))
                continue
            if start != self.CMD_START or length != self._CMD_LEN:
                continue

            crc_calc = (sum(frame[:-2]) & 0xFFFF)
            if crc_calc != crc_recv:
                continue  # bad frame, drop

            # units: mm/s and mrad/s → SI (m/s, rad/s)
            v = v_mmps / 1000.0
            w = w_mradps / 1000.0
            self.ctrl.update_cmd_vel(v, w)

    # ---------- internals ----------
    def _checksum(self, b):
        return sum(b) & 0xFFFF

    def _read_battery_mv(self):
        """Return battery in millivolts (uint16), or 0 if no ADC."""
        if not self.adc:
            return 0
        raw = self.adc.read_u16()  # 0..65535 across 0..3.3V on Pico
        v_adc = (raw / 65535.0) * 3.3  # volts
        v_in  = v_adc * 11.0           # 10k(top):1k(bottom) divider
        return _to_u16(int(round(v_in * 1000.0)))  # mV

    def _read_imu_scaled(self):
        """Return accel mg (x,y,z) and gyro deci-dps (x,y,z). Zeros if no IMU."""
        if not self.imu:
            return (0,0,0), (0,0,0)
        try:
            ax, ay, az = self.imu.read_accel_data()  # in g
            gx, gy, gz = self.imu.read_gyro_data()   # in deg/s
        except Exception:
            return (0,0,0), (0,0,0)

        amg = (_to_i16(ax*1000.0), _to_i16(ay*1000.0), _to_i16(az*1000.0))
        gdps10 = (_to_i16(gx*10.0), _to_i16(gy*10.0), _to_i16(gz*10.0))  # deci-dps, fits ±3276.7 dps
        return amg, gdps10

    def _send_compact(self):
        ts = time.ticks_ms()
        self.msg_counter = (self.msg_counter + 1) & 0xFFFF

        diag = self.ctrl.get_diagnostics()
        timeout_flag = 1 if diag.get("timeout", False) else 0

        # RPMs (int16). Your encoder.rpm is abs; that’s fine for telemetry.
        rpm_l = _to_i16(self.left.encoder.rpm)
        rpm_r = _to_i16(self.right.encoder.rpm)

        batt_mv = self._read_battery_mv()
        (ax,ay,az), (gx,gy,gz) = self._read_imu_scaled()

        # commanded velocities (for context)
        v_mmps = _to_i16(diag["cmd"]["linear_mps"] * 1000.0)
        w_mrad = _to_i16(diag["cmd"]["angular_rps"] * 1000.0)

        payload = struct.pack(self._fmt_tel_wo_crc,
                              self.TELEMETRY_START, self._TEL_LEN, self.msg_counter,
                              ts, timeout_flag,
                              rpm_l, rpm_r,
                              batt_mv,
                              ax, ay, az,
                              gx, gy, gz,
                              v_mmps, w_mrad)

        crc = struct.pack('<H', self._checksum(payload))
        self.uart.write(payload + crc)

    def _send_debug(self):
        """
        A fatter frame with extra controller/motor internals.
        Keeping it simple: pack a few signed shorts to avoid floats.
        Layout (64 bytes total):
          start(u16), len(u8), count(u16), ts(u32), flags(u8),
          sp_l(i16), sp_r(i16), rpm_l(i16), rpm_r(i16),
          duty_l(i16), duty_r(i16), err_l(i16), err_r(i16),
          batt_mV(u16),
          ax,ay,az(i16 each), gx,gy,gz(i16 each),
          v_mmps(i16), w_mrad(i16),
          loop_us(u16),
          crc(u16)
        """
        ts = time.ticks_ms()
        self.msg_counter = (self.msg_counter + 1) & 0xFFFF
        diag = self.ctrl.get_diagnostics()

        timeout_flag = 1 if diag.get("timeout", False) else 0
        sp_l = _to_i16(diag["target_rpm"]["left"])
        sp_r = _to_i16(diag["target_rpm"]["right"])
        rpm_l = _to_i16(self.left.encoder.rpm)
        rpm_r = _to_i16(self.right.encoder.rpm)

        L = self.left.get_diagnostics()
        R = self.right.get_diagnostics()
        duty_l = _to_i16(L["last_output"])
        duty_r = _to_i16(R["last_output"])
        err_l  = _to_i16(L["last_error"])
        err_r  = _to_i16(R["last_error"])

        batt_mv = self._read_battery_mv()
        (ax,ay,az), (gx,gy,gz) = self._read_imu_scaled()
        v_mmps = _to_i16(diag["cmd"]["linear_mps"] * 1000.0)
        w_mrad = _to_i16(diag["cmd"]["angular_rps"] * 1000.0)
        loop_us = _to_u16(diag.get("loop_time_us", 0))

        # pack manually to keep code readable
        fmt_wo_crc = '<HBHIB8hH6h3hH'
        #              start len cnt ts flag spL spR rpmL rpmR dutyL dutyR errL errR batt ax ay az gx gy gz v_mmps w_mrad loopus
        payload = struct.pack(fmt_wo_crc,
                              self.TELEMETRY_START, 64, self.msg_counter, ts, timeout_flag,
                              sp_l, sp_r, rpm_l, rpm_r, duty_l, duty_r, err_l, err_r,
                              batt_mv,
                              ax, ay, az, gx, gy, gz,
                              v_mmps, w_mrad,
                              loop_us)

        crc = struct.pack('<H', self._checksum(payload))
        self.uart.write(payload + crc)
