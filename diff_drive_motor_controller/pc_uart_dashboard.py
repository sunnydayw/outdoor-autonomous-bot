import sys
import struct
import time
from collections import deque
from threading import Thread

import serial
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import Qt
import pyqtgraph as pg

# ----------------------
# Global PyQtGraph Config: white background, black foreground.
pg.setConfigOption('background', 'w')
pg.setConfigOption('foreground', 'k')

# ----------------------
# TelemetryReader Thread
# Message structure (40 bytes):
#   uint16: Start Delimiter (0xAA55)
#   uint8:  Message Length (40)
#   uint16: Message Counter
#   uint32: Timestamp (ms)
#   uint8:  Timeout Flag
#   7 x int16: Left Motor diagnostics (target_rpm, actual_rpm, p, i, d, term, loop_time)
#   7 x int16: Right Motor diagnostics (same order)
#   uint16: Checksum
FMT_NO_CHECKSUM = '<HBHIB7h7h'
FMT_FULL = FMT_NO_CHECKSUM + 'H'
MSG_SIZE = struct.calcsize(FMT_FULL)
START_DELIMITER = 0xAA55

class TelemetryReader(Thread):
    def __init__(self, port, baudrate=115200):
        super().__init__()
        self.ser = serial.Serial(port, baudrate=baudrate, timeout=0.5)
        self.running = True

        # Rolling buffers for ~30 sec (maxlen adjustable; here ~1500 samples if ~50Hz)
        self.data_buffers = {
            'time': deque(maxlen=1500),
            'left_target_rpm': deque(maxlen=1500),
            'left_actual_rpm': deque(maxlen=1500),
            'right_target_rpm': deque(maxlen=1500),
            'right_actual_rpm': deque(maxlen=1500),
            'left_p': deque(maxlen=1500),
            'left_i': deque(maxlen=1500),
            'left_d': deque(maxlen=1500),
            'left_term': deque(maxlen=1500),
            'left_pwm': deque(maxlen=1500),
            'right_p': deque(maxlen=1500),
            'right_i': deque(maxlen=1500),
            'right_d': deque(maxlen=1500),
            'right_term': deque(maxlen=1500),
            'right_pwm': deque(maxlen=1500),
            'left_loop_time': deque(maxlen=1500),
            'right_loop_time': deque(maxlen=1500),
            'timeout_flag': deque(maxlen=1500),
            'msg_counter': deque(maxlen=1500),
        }
        self.last_msg_counter = None
        self.base_time = None  # Used to compute relative time

    def run(self):
        while self.running:
            data = self.ser.read(MSG_SIZE)
            if len(data) < MSG_SIZE:
                continue  # Incomplete message, skip

            try:
                unpacked = struct.unpack(FMT_FULL, data)
            except Exception as e:
                print("Unpack error:", e)
                continue

            header = unpacked[0]
            if header != START_DELIMITER:
                print("Bad header:", header)
                continue

            msg_counter = unpacked[2]
            timestamp = unpacked[3]  # in ms from the controller
            timeout_flag = unpacked[4]
            left_vals = unpacked[5:12]   # (target_rpm, actual_rpm, p, i, d, term, loop_time)
            right_vals = unpacked[12:19]

            # Check checksum (simple additive over all bytes except final 2 bytes)
            calc_checksum = sum(data[:-2]) & 0xFFFF
            recv_checksum = unpacked[19]
            if calc_checksum != recv_checksum:
                print("Checksum error: calc", calc_checksum, "recv", recv_checksum)
                continue

            # Establish base_time at the first message and compute relative time.
            if self.base_time is None:
                self.base_time = timestamp
            t_sec = (timestamp - self.base_time) / 1000.0

            self.data_buffers['time'].append(t_sec)
            self.data_buffers['left_target_rpm'].append(left_vals[0])
            self.data_buffers['left_actual_rpm'].append(left_vals[1])
            self.data_buffers['right_target_rpm'].append(right_vals[0])
            self.data_buffers['right_actual_rpm'].append(right_vals[1])
            self.data_buffers['left_p'].append(left_vals[2])
            self.data_buffers['left_i'].append(left_vals[3])
            self.data_buffers['left_d'].append(left_vals[4])
            self.data_buffers['left_term'].append(left_vals[5])
            self.data_buffers['left_pwm'].append(left_vals[5])  # Adjust if PWM is separate.
            self.data_buffers['left_loop_time'].append(left_vals[6])
            self.data_buffers['right_p'].append(right_vals[2])
            self.data_buffers['right_i'].append(right_vals[3])
            self.data_buffers['right_d'].append(right_vals[4])
            self.data_buffers['right_term'].append(right_vals[5])
            self.data_buffers['right_pwm'].append(right_vals[5])
            self.data_buffers['right_loop_time'].append(right_vals[6])
            self.data_buffers['timeout_flag'].append(timeout_flag)
            self.data_buffers['msg_counter'].append(msg_counter)

    def clear_data(self):
        # Clear all buffers and reset the base time so that new time starts at 0.
        for key in self.data_buffers:
            self.data_buffers[key].clear()
        self.base_time = None

    def stop(self):
        self.running = False
        self.ser.close()

# ----------------------
# Dashboard GUI
class Dashboard(QtWidgets.QMainWindow):
    def __init__(self, telemetry_reader):
        super().__init__()
        self.telemetry = telemetry_reader
        self.setWindowTitle("Robot Telemetry Dashboard")
        self.resize(1400, 900)

        # Default x-axis window length (in seconds)
        self.x_window_length = 30

        # Main widget: three columns.
        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QtWidgets.QHBoxLayout(central_widget)

        # --- Left Column: Left Motor Data ---
        left_group = QtWidgets.QGroupBox("Left Motor")
        left_layout = QtWidgets.QVBoxLayout(left_group)
        
        # Left Motor RPM Plot (with legend)
        self.left_rpm_plot = pg.PlotWidget(title="RPM")
        self.left_rpm_plot.showGrid(x=True, y=True)
        self.left_rpm_plot.addLegend()
        self.left_rpm_target_curve = self.left_rpm_plot.plot(pen=pg.mkPen(color=(200, 0, 0), width=2), name="Target")
        self.left_rpm_actual_curve = self.left_rpm_plot.plot(pen=pg.mkPen(color=(200, 0, 0), width=2, style=Qt.DashLine), name="Actual")
        left_layout.addWidget(self.left_rpm_plot)

        # Left Motor PID and PWM Plots (4 plots: P, I, D, PWM)
        self.left_p_plot = pg.PlotWidget(title="P")
        self.left_p_plot.showGrid(x=True, y=True)
        self.left_p_curve = self.left_p_plot.plot(pen=pg.mkPen(color=(0, 150, 0), width=2))
        left_layout.addWidget(self.left_p_plot)
        
        self.left_i_plot = pg.PlotWidget(title="I")
        self.left_i_plot.showGrid(x=True, y=True)
        self.left_i_curve = self.left_i_plot.plot(pen=pg.mkPen(color=(0, 150, 150), width=2))
        left_layout.addWidget(self.left_i_plot)
        
        self.left_d_plot = pg.PlotWidget(title="D")
        self.left_d_plot.showGrid(x=True, y=True)
        self.left_d_curve = self.left_d_plot.plot(pen=pg.mkPen(color=(150, 0, 150), width=2))
        left_layout.addWidget(self.left_d_plot)
        
        self.left_pwm_plot = pg.PlotWidget(title="PWM")
        self.left_pwm_plot.showGrid(x=True, y=True)
        self.left_pwm_curve = self.left_pwm_plot.plot(pen=pg.mkPen(color=(255, 100, 0), width=2))
        left_layout.addWidget(self.left_pwm_plot)
        
        # --- Center Column: Right Motor Data ---
        right_group = QtWidgets.QGroupBox("Right Motor")
        right_layout = QtWidgets.QVBoxLayout(right_group)
        
        # Right Motor RPM Plot (with legend)
        self.right_rpm_plot = pg.PlotWidget(title="RPM")
        self.right_rpm_plot.showGrid(x=True, y=True)
        self.right_rpm_plot.addLegend()
        self.right_rpm_target_curve = self.right_rpm_plot.plot(pen=pg.mkPen(color=(0, 0, 200), width=2), name="Target")
        self.right_rpm_actual_curve = self.right_rpm_plot.plot(pen=pg.mkPen(color=(0, 0, 200), width=2, style=Qt.DashLine), name="Actual")
        right_layout.addWidget(self.right_rpm_plot)
        
        # Right Motor PID and PWM Plots (4 plots: P, I, D, PWM)
        self.right_p_plot = pg.PlotWidget(title="P")
        self.right_p_plot.showGrid(x=True, y=True)
        self.right_p_curve = self.right_p_plot.plot(pen=pg.mkPen(color=(0, 150, 0), width=2))
        right_layout.addWidget(self.right_p_plot)
        
        self.right_i_plot = pg.PlotWidget(title="I")
        self.right_i_plot.showGrid(x=True, y=True)
        self.right_i_curve = self.right_i_plot.plot(pen=pg.mkPen(color=(0, 150, 150), width=2))
        right_layout.addWidget(self.right_i_plot)
        
        self.right_d_plot = pg.PlotWidget(title="D")
        self.right_d_plot.showGrid(x=True, y=True)
        self.right_d_curve = self.right_d_plot.plot(pen=pg.mkPen(color=(150, 0, 150), width=2))
        right_layout.addWidget(self.right_d_plot)
        
        self.right_pwm_plot = pg.PlotWidget(title="PWM")
        self.right_pwm_plot.showGrid(x=True, y=True)
        self.right_pwm_curve = self.right_pwm_plot.plot(pen=pg.mkPen(color=(255, 100, 0), width=2))
        right_layout.addWidget(self.right_pwm_plot)
        
        # --- Right Column: Stats & Controls ---
        right_col_layout = QtWidgets.QVBoxLayout()
        
        # Display Controls group: clear data, reset scale, and x-axis window slider.
        display_group = QtWidgets.QGroupBox("Display Controls")
        display_layout = QtWidgets.QVBoxLayout(display_group)
        self.clear_data_button = QtWidgets.QPushButton("Clear Data")
        self.reset_scale_button = QtWidgets.QPushButton("Reset Scale (Current Window)")
        # Slider for x-axis window length (in seconds)
        self.x_window_slider = QtWidgets.QSlider(Qt.Horizontal)
        self.x_window_slider.setRange(5, 60)
        self.x_window_slider.setValue(self.x_window_length)
        self.x_window_slider.setTickInterval(5)
        self.x_window_slider.setTickPosition(QtWidgets.QSlider.TicksBelow)
        display_layout.addWidget(QtWidgets.QLabel("X-Axis Window (sec):"))
        display_layout.addWidget(self.x_window_slider)
        display_layout.addWidget(self.clear_data_button)
        display_layout.addWidget(self.reset_scale_button)
        right_col_layout.addWidget(display_group)
        
        # Stats group: Loop Times & Timeout and Message Counter Differences.
        stats_group = QtWidgets.QGroupBox("Loop & Message Stats")
        stats_layout = QtWidgets.QVBoxLayout(stats_group)
        
        self.loop_plot = pg.PlotWidget(title="Loop Times & Timeout Flag")
        self.loop_plot.showGrid(x=True, y=True)
        self.loop_plot.addLegend()
        self.left_loop_curve = self.loop_plot.plot(pen=pg.mkPen(color=(150, 0, 150), width=2), name="Left Loop")
        self.right_loop_curve = self.loop_plot.plot(pen=pg.mkPen(color=(0, 150, 150), width=2), name="Right Loop")
        self.timeout_curve = self.loop_plot.plot(pen=pg.mkPen(color=(0, 0, 0), width=2, style=Qt.DashLine), name="Timeout (scaled)")
        stats_layout.addWidget(self.loop_plot)
        
        self.msg_diff_plot = pg.PlotWidget(title="Msg Counter Diff")
        self.msg_diff_plot.showGrid(x=True, y=True)
        self.msg_diff_plot.addLegend()
        self.msg_diff_plot.setYRange(0.5, 1.5)
        self.msg_diff_plot.setFixedHeight(150)
        self.msg_diff_curve = self.msg_diff_plot.plot(pen=pg.mkPen(color=(255, 165, 0), width=2), name="Diff")
        stats_layout.addWidget(self.msg_diff_plot)
        right_col_layout.addWidget(stats_group)
        
        # Control Commands & Settings.
        control_group = QtWidgets.QGroupBox("Control Commands & Settings")
        control_layout = QtWidgets.QVBoxLayout(control_group)
        ctrl_motor_layout = QtWidgets.QHBoxLayout()
        
        left_ctrl = QtWidgets.QGroupBox("Left Control")
        left_ctrl_layout = QtWidgets.QFormLayout(left_ctrl)
        self.left_rpm_spin = QtWidgets.QSpinBox(); self.left_rpm_spin.setRange(0, 1000)
        self.left_p_spin = QtWidgets.QSpinBox(); self.left_p_spin.setRange(0, 100)
        self.left_i_spin = QtWidgets.QSpinBox(); self.left_i_spin.setRange(0, 100)
        self.left_d_spin = QtWidgets.QSpinBox(); self.left_d_spin.setRange(0, 100)
        left_ctrl_layout.addRow("Target RPM:", self.left_rpm_spin)
        left_ctrl_layout.addRow("P:", self.left_p_spin)
        left_ctrl_layout.addRow("I:", self.left_i_spin)
        left_ctrl_layout.addRow("D:", self.left_d_spin)
        ctrl_motor_layout.addWidget(left_ctrl)
        
        right_ctrl = QtWidgets.QGroupBox("Right Control")
        right_ctrl_layout = QtWidgets.QFormLayout(right_ctrl)
        self.right_rpm_spin = QtWidgets.QSpinBox(); self.right_rpm_spin.setRange(0, 1000)
        self.right_p_spin = QtWidgets.QSpinBox(); self.right_p_spin.setRange(0, 100)
        self.right_i_spin = QtWidgets.QSpinBox(); self.right_i_spin.setRange(0, 100)
        self.right_d_spin = QtWidgets.QSpinBox(); self.right_d_spin.setRange(0, 100)
        right_ctrl_layout.addRow("Target RPM:", self.right_rpm_spin)
        right_ctrl_layout.addRow("P:", self.right_p_spin)
        right_ctrl_layout.addRow("I:", self.right_i_spin)
        right_ctrl_layout.addRow("D:", self.right_d_spin)
        ctrl_motor_layout.addWidget(right_ctrl)
        control_layout.addLayout(ctrl_motor_layout)
        
        self.send_button = QtWidgets.QPushButton("Send Command")
        control_layout.addWidget(self.send_button)
        right_col_layout.addWidget(control_group)
        right_col_layout.addWidget(self.send_button)
        
        # Add the three columns.
        main_layout.addWidget(left_group)
        main_layout.addWidget(right_group)
        main_layout.addLayout(right_col_layout)
        
        # Timer for updating plots; update interval set by default 100 ms.
        self.update_timer = QtCore.QTimer()
        self.update_timer.timeout.connect(self.update_plots)
        self.update_timer.start(100)
        
        # Connect control signals.
        self.clear_data_button.clicked.connect(self.telemetry.clear_data)
        self.reset_scale_button.clicked.connect(self.reset_current_window_scales)
        self.x_window_slider.valueChanged.connect(self.update_x_window)
        self.send_button.clicked.connect(self.send_control_command)
    
    def safe_set_data(self, curve, x, y):
        if len(x) == len(y):
            curve.setData(x, y)
    
    def update_x_window(self, val):
        self.x_window_length = val
    
    def reset_current_window_scales(self):
        """
        Reset each plot's y-axis based on the data within the currently visible x-axis window.
        The x-axis window is defined as [current_time - x_window_length, current_time],
        where current_time is the most recent timestamp.
        """
        buffers = {k: list(v) for k, v in self.telemetry.data_buffers.items()}
        t = buffers.get('time', [])
        if not t:
            return
        current_time = t[-1]
        x_min = max(0, current_time - self.x_window_length)
        x_max = current_time
        # For each plot, filter the data points where t is within [x_min, x_max] and compute new y-range.
        plots_data = [
            (self.left_rpm_plot, 'left_target_rpm'),
            (self.left_rpm_plot, 'left_actual_rpm'),
            (self.left_p_plot, 'left_p'),
            (self.left_i_plot, 'left_i'),
            (self.left_d_plot, 'left_d'),
            (self.left_pwm_plot, 'left_pwm'),
            (self.right_rpm_plot, 'right_target_rpm'),
            (self.right_rpm_plot, 'right_actual_rpm'),
            (self.right_p_plot, 'right_p'),
            (self.right_i_plot, 'right_i'),
            (self.right_d_plot, 'right_d'),
            (self.right_pwm_plot, 'right_pwm'),
            (self.loop_plot, 'left_loop_time'),
            (self.loop_plot, 'right_loop_time')
        ]
        for plot, key in plots_data:
            y_vals = [y for (t_val, y) in zip(t, buffers.get(key, [])) if x_min <= t_val <= x_max]
            if y_vals:
                y_min, y_max = min(y_vals), max(y_vals)
                margin = (y_max - y_min) * 0.1 if (y_max - y_min) != 0 else 1
                plot.setYRange(y_min - margin, y_max + margin)
    
    def update_plots(self):
        buffers = {k: list(v) for k, v in self.telemetry.data_buffers.items()}
        t = buffers.get('time', [])
        if not t:
            return
        
        # Left Motor Plots.
        self.safe_set_data(self.left_rpm_target_curve, t, buffers['left_target_rpm'])
        self.safe_set_data(self.left_rpm_actual_curve, t, buffers['left_actual_rpm'])
        self.safe_set_data(self.left_p_curve, t, buffers['left_p'])
        self.safe_set_data(self.left_i_curve, t, buffers['left_i'])
        self.safe_set_data(self.left_d_curve, t, buffers['left_d'])
        self.safe_set_data(self.left_pwm_curve, t, buffers['left_pwm'])
        
        # Right Motor Plots.
        self.safe_set_data(self.right_rpm_target_curve, t, buffers['right_target_rpm'])
        self.safe_set_data(self.right_rpm_actual_curve, t, buffers['right_actual_rpm'])
        self.safe_set_data(self.right_p_curve, t, buffers['right_p'])
        self.safe_set_data(self.right_i_curve, t, buffers['right_i'])
        self.safe_set_data(self.right_d_curve, t, buffers['right_d'])
        self.safe_set_data(self.right_pwm_curve, t, buffers['right_pwm'])
        
        # Loop Times & Timeout.
        self.safe_set_data(self.left_loop_curve, t, buffers['left_loop_time'])
        self.safe_set_data(self.right_loop_curve, t, buffers['right_loop_time'])
        if len(t) == len(buffers['timeout_flag']):
            scaled_timeout = [flag * 1000 for flag in buffers['timeout_flag']]
            self.safe_set_data(self.timeout_curve, t, scaled_timeout)
        
        # Message Counter Differences.
        msg_list = buffers.get('msg_counter', [])
        if len(msg_list) >= 2:
            msg_diff = []
            for i in range(1, len(msg_list)):
                diff = (msg_list[i] - msg_list[i-1]) & 0xFFFF
                msg_diff.append(diff)
            t_diff = t[1:]
            self.safe_set_data(self.msg_diff_curve, t_diff, msg_diff)
        
        # Set x-axis range for all plots based on the slider's window length.
        current_time = t[-1]
        x_min = max(0, current_time - self.x_window_length)
        for plot in [self.left_rpm_plot, self.left_p_plot, self.left_i_plot, self.left_d_plot, self.left_pwm_plot,
                     self.right_rpm_plot, self.right_p_plot, self.right_i_plot, self.right_d_plot, self.right_pwm_plot,
                     self.loop_plot, self.msg_diff_plot]:
            plot.setXRange(x_min, current_time)
    
    def send_control_command(self):
        """
        Pack and send a control message to the Pico.
        Format (23 bytes total):
          uint16: Start Delimiter (0xCC33)
          uint8:  Message Length (23)
          uint16: Message Counter (0 for simplicity)
          int16: Left Target RPM
          int16: Right Target RPM
          int16: Left P, Left I, Left D
          int16: Right P, Right I, Right D
          uint16: Checksum (appended)
        """
        CTRL_START = 0xCC33
        ctrl_msg_counter = 0
        left_rpm = self.left_rpm_spin.value()
        right_rpm = self.right_rpm_spin.value()
        left_p = self.left_p_spin.value()
        left_i = self.left_i_spin.value()
        left_d = self.left_d_spin.value()
        right_p = self.right_p_spin.value()
        right_i = self.right_i_spin.value()
        right_d = self.right_d_spin.value()
        
        fmt = '<HBH8h'  # H, B, H then 8 int16 values.
        msg_length = struct.calcsize(fmt) + 2  # +2 for checksum.
        packed = struct.pack(fmt,
                             CTRL_START,
                             msg_length,
                             ctrl_msg_counter,
                             int(left_rpm),
                             int(right_rpm),
                             int(left_p),
                             int(left_i),
                             int(left_d),
                             int(right_p),
                             int(right_i),
                             int(right_d))
        checksum = sum(packed) & 0xFFFF
        packed_checksum = struct.pack('<H', checksum)
        ctrl_message = packed + packed_checksum
        self.telemetry.ser.write(ctrl_message)
        print("Control command sent.")

# ----------------------
# Main Application
def main():
    app = QtWidgets.QApplication(sys.argv)
    telemetry_reader = TelemetryReader(port='/dev/tty.usbserial-A505VA57')
    telemetry_reader.start()
    dashboard = Dashboard(telemetry_reader)
    dashboard.show()
    ret = app.exec_()
    telemetry_reader.stop()
    telemetry_reader.join()
    sys.exit(ret)

if __name__ == '__main__':
    main()
