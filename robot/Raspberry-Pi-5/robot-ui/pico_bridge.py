# pico_bridge.py  (RX-only logging)
import math, struct, serial, serial.tools.list_ports
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from sensor_msgs.msg import Imu, BatteryState
from std_msgs.msg import Int16

TEL_FMT = '<HBHIB2hH3h3h2hH'   # 34B telemetry from Pico
TEL_LEN = 34
CMD_FMT_NOCRC = '<HBH2h'       # start,len,count,v_mmps,w_mrad
CMD_LEN = 11

CANDIDATES = ["/dev/serial0", "/dev/ttyAMA0", "/dev/ttyAMA10", "/dev/ttyS0"]

def pick_port():
    for p in CANDIDATES:
        try:
            with open(p, 'rb'):
                return p
        except Exception:
            pass
    for p in serial.tools.list_ports.comports():
        if p.device.startswith(("/dev/ttyAMA", "/dev/ttyS")):
            return p.device
    raise RuntimeError("No UART port found")

class PicoBridge(Node):
    def __init__(self):
        super().__init__('pico_bridge')

        # ---- parameters ----
        self.declare_parameter('port', 'auto')
        self.declare_parameter('baud', 115200)
        self.declare_parameter('read_hz', 200.0)    # UART poll rate
        self.declare_parameter('rx_log', True)      # print RX telemetry lines?
        self.declare_parameter('rx_log_every', 20)  # print every N frames (1 = every frame)

        port = self.get_parameter('port').get_parameter_value().string_value
        baud = self.get_parameter('baud').get_parameter_value().integer_value
        read_hz = float(self.get_parameter('read_hz').value)
        self.rx_log = self.get_parameter('rx_log').get_parameter_value().bool_value
        self.rx_log_every = max(1, int(self.get_parameter('rx_log_every').value))

        if port == 'auto':
            port = pick_port()
        self.get_logger().info(f"Opening UART: {port} @ {baud}")
        self.ser = serial.Serial(port, baudrate=baud, timeout=0.01)

        self.buf = bytearray()
        self.tx_count = 0
        self.rx_count = 0

        # ROS I/O
        self.sub = self.create_subscription(Twist, '/cmd_vel', self.cmd_cb, 10)
        self.pub_rpm_l = self.create_publisher(Int16, 'left_wheel_rpm', 10)
        self.pub_rpm_r = self.create_publisher(Int16, 'right_wheel_rpm', 10)
        self.pub_batt  = self.create_publisher(BatteryState, 'battery_state', 10)
        self.pub_imu   = self.create_publisher(Imu, 'imu/data_raw', 10)

        # fast read timer (independent of control rate)
        self.timer = self.create_timer(1.0/max(read_hz,1.0), self.read_uart)
        self.get_logger().info(f"Read timer at {read_hz:.1f} Hz (RX-only logging)")


        # --- add params in PicoBridge.__init__ (near the others)

        self.declare_parameter('rx_warn_s', 2.0)   # warn if no valid frames for N seconds
        self.declare_parameter('rx_hex', False)    # dump raw RX bytes as hex
        self.no_rx_warn_s = float(self.get_parameter('rx_warn_s').value)
        self.rx_hex = self.get_parameter('rx_hex').get_parameter_value().bool_value
        self._last_rx_time = self.get_clock().now()

    # --- NO PRINTING HERE (TX silent) ---
    def cmd_cb(self, msg: Twist):
        v_mmps = int(round(msg.linear.x * 1000.0))   # m/s -> mm/s
        w_mrad = int(round(msg.angular.z * 1000.0))  # rad/s -> mrad/s
        head = struct.pack(CMD_FMT_NOCRC, 0xCC33, CMD_LEN, self.tx_count & 0xFFFF, v_mmps, w_mrad)
        crc  = struct.pack('<H', sum(head) & 0xFFFF)
        try:
            self.ser.write(head + crc)
            self.tx_count += 1
        except Exception as e:
            self.get_logger().error(f'UART write failed: {e}')

    def read_uart(self):
        try:
            self.buf += self.ser.read(256) or b''
            # --- in read_uart(), right after: self.buf += self.ser.read(256) or b''
            if self.rx_hex:
                # print the first 32 bytes of the chunk, if any
                if len(self.buf) > 0:
                    preview = self.buf[:32]
                    self.get_logger().info("RX raw: " + preview.hex())
        except Exception as e:
            self.get_logger().error(f'UART read failed: {e}')
            return

        while True:
            idx = self.buf.find(b'\x55\xAA')  # start=0xAA55 (LE in stream)
            if idx < 0:
                if len(self.buf) > 128:
                    self.buf = self.buf[-128:]
                return
            if len(self.buf) < idx + TEL_LEN:
                return
            frame = bytes(self.buf[idx:idx+TEL_LEN])
            del self.buf[:idx+TEL_LEN]

            try:
                (start, length, count, ts_ms, timeout_flag,
                 rpm_l, rpm_r, batt_mv,
                 ax_mg, ay_mg, az_mg,
                 gx_ddeci, gy_ddeci, gz_ddeci,
                 v_mmps, w_mrad, crc_recv) = struct.unpack(TEL_FMT, frame)
            except struct.error:
                continue

            if length != TEL_LEN or (sum(frame[:-2]) & 0xFFFF) != crc_recv:
                continue

            # --- when you successfully parse a frame (right before publish or right after):
            self._last_rx_time = self.get_clock().now()

            # publish topics
            self.pub_rpm_l.publish(Int16(data=rpm_l))
            self.pub_rpm_r.publish(Int16(data=rpm_r))

            batt = BatteryState()
            batt.voltage = batt_mv / 1000.0
            batt.current = float('nan'); batt.percentage = float('nan')
            self.pub_batt.publish(batt)

            g = 9.80665; dps = math.pi/180.0
            imu = Imu()
            imu.header.stamp = self.get_clock().now().to_msg()
            imu.linear_acceleration.x = ax_mg * g / 1000.0
            imu.linear_acceleration.y = ay_mg * g / 1000.0
            imu.linear_acceleration.z = az_mg * g / 1000.0
            imu.angular_velocity.x = (gx_ddeci/10.0) * dps
            imu.angular_velocity.y = (gy_ddeci/10.0) * dps
            imu.angular_velocity.z = (gz_ddeci/10.0) * dps
            self.pub_imu.publish(imu)

            # optional RX log
            self.rx_count += 1
            if self.rx_log and (self.rx_count % self.rx_log_every == 0):
                self.get_logger().info(
                    f"RX tele: rpm L={rpm_l} R={rpm_r}, batt={batt_mv} mV, "
                    f"accel(mg)=({ax_mg},{ay_mg},{az_mg}), gyro(0.1dps)=({gx_ddeci},{gy_ddeci},{gz_ddeci}), "
                    f"cmd(mm/s,mrad/s)=({v_mmps},{w_mrad}), timeout={bool(timeout_flag)}"
                )
            # --- at the very end of read_uart(), add a no-RX watchdog:
            now = self.get_clock().now()
            dt = (now.nanoseconds - self._last_rx_time.nanoseconds)/1e9
            if dt > self.no_rx_warn_s:
                self.get_logger().warn(f"No telemetry for {dt:.1f}s (port open? Pico sending?)")
                # avoid spamming every timer tick
                self._last_rx_time = now

def main():
    rclpy.init()
    node = PicoBridge()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
