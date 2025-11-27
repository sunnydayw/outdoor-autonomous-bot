# differential_drivetrain.py
"""
DiffDriveController (ROS-style) for MicroPython.

- Accepts cmd_vel (linear m/s, angular rad/s) via update_cmd_vel()
- Converts to left/right wheel RPM using standard diff-drive kinematics
- Applies a cmd_vel timeout to stop motors if commands go stale
- Compatible with two motor API styles:
    1) target_rpm property + step()          (your Motor class)
    2) set_target_rpm(rpm) method + update() (common in other projects)
"""

import time
from config import WHEEL_CIRCUMFERENCE, WHEEL_SEPARATION, CMD_VEL_TIMEOUT

try:
    from proto import DriveFeedbackStatusFlags
except Exception:  # pragma: no cover - proto is optional during unit tests
    class DriveFeedbackStatusFlags:
        COMMAND_TIMEOUT = 1 << 0

class DiffDriveController:
    def __init__(self, left_motor, right_motor,
                 wheel_circumference=WHEEL_CIRCUMFERENCE,
                 wheel_separation=WHEEL_SEPARATION,
                 cmd_vel_timeout=CMD_VEL_TIMEOUT):
        """
        :param left_motor: Motor instance for the left wheel
        :param right_motor: Motor instance for the right wheel
        """
        self.left_motor = left_motor
        self.right_motor = right_motor

        # geometry/config
        self._C = float(wheel_circumference)   # wheel circumference [m]
        self._L = float(wheel_separation)      # wheel separation  [m]

        # timeout
        if cmd_vel_timeout is None:
            self._timeout_ms = None
        else:
            self._timeout_ms = int(cmd_vel_timeout)

        # command state
        self._linear = 0.0     # m/s
        self._angular = 0.0    # rad/s
        self._last_cmd_time = time.ticks_ms()

        # telemetry
        self._last_target_rpm = (0.0, 0.0)
        self._last_actual_rpm = (0.0, 0.0)
        self._timeout_flag = False
        self._last_loop_time_us = 0
        self._last_linear_vel = 0.0
        self._last_angular_vel = 0.0

    # ---- public API ----
    def update_cmd_vel(self, linear, angular):
        """Update desired linear (m/s) and angular (rad/s) velocities."""
        self._linear = float(linear)
        self._angular = float(angular)
        self._last_cmd_time = time.ticks_ms()

    def compute_wheel_rpms(self):
        """
        v_l = v - (ω * L/2)
        v_r = v + (ω * L/2)
        RPM = (v / C) * 60
        """
        v_l = self._linear - (self._angular * self._L * 0.5)
        v_r = self._linear + (self._angular * self._L * 0.5)
        rpm_l = (v_l * 60.0) / self._C
        rpm_r = (v_r * 60.0) / self._C
        self._last_target_rpm = (rpm_l, rpm_r)
        # round only for human-friendly inspection; keep full precision in setters
        return round(rpm_l, 2), round(rpm_r, 2)

    def stop_motors(self, brake=True):
        """Safely stop both motors."""
        self._set_target_rpm(self.left_motor, 0.0)
        self._set_target_rpm(self.right_motor, 0.0)
        # step/update once to ensure PWM=0 is applied
        self._step_motor(self.left_motor)
        self._step_motor(self.right_motor)
        if brake:
            self._brake_motor(self.left_motor)
            self._brake_motor(self.right_motor)
        self._last_actual_rpm = (0.0, 0.0)
        self._last_linear_vel = 0.0
        self._last_angular_vel = 0.0

    def update_motors(self):
        """Compute and apply wheel RPMs; handles cmd_vel timeout."""
        start = time.ticks_us()
        now_ms = time.ticks_ms()

        # timeout
        if (self._timeout_ms is not None) and (time.ticks_diff(now_ms, self._last_cmd_time) > self._timeout_ms):
            self._timeout_flag = True
            self.stop_motors(brake=True)   # was brake=False
            self._last_target_rpm = (0.0, 0.0)  # optional: reflect setpoint=0 in diagnostics
            self._last_loop_time_us = time.ticks_diff(time.ticks_us(), start)
            return
        
        self._timeout_flag = False

        # compute setpoints
        rpm_l, rpm_r = self.compute_wheel_rpms()

        # push setpoints to motors (direction handled inside Motor)
        self._set_target_rpm(self.left_motor, rpm_l)
        self._set_target_rpm(self.right_motor, rpm_r)

        # advance each motor control loop
        self._step_motor(self.left_motor)
        self._step_motor(self.right_motor)

        # capture actuals if available
        l_rpm = self._read_motor_rpm(self.left_motor)
        r_rpm = self._read_motor_rpm(self.right_motor)
        self._last_actual_rpm = (l_rpm, r_rpm)
        self._last_linear_vel, self._last_angular_vel = self._compute_body_velocities(l_rpm, r_rpm)

        self._last_loop_time_us = time.ticks_diff(time.ticks_us(), start)

    def get_diagnostics(self):
        """Return a small status dict suitable for printing/logging."""
        return {
            "timeout": self._timeout_flag,
            "loop_time_us": self._last_loop_time_us,
            "target_rpm": {"left": self._last_target_rpm[0], "right": self._last_target_rpm[1]},
            "actual_rpm": {"left": self._last_actual_rpm[0], "right": self._last_actual_rpm[1]},
            "cmd": {"linear_mps": self._linear, "angular_rps": self._angular},
            "body": {"linear_mps": self._last_linear_vel, "angular_rps": self._last_angular_vel},
        }

    def get_drive_feedback(self):
        """Return a telemetry-friendly snapshot of the drivetrain state."""
        left_ticks = getattr(getattr(self.left_motor, "encoder", None), "ticks", 0)
        right_ticks = getattr(getattr(self.right_motor, "encoder", None), "ticks", 0)

        status_flags = 0
        if self._timeout_flag:
            status_flags |= DriveFeedbackStatusFlags.COMMAND_TIMEOUT

        return {
            "v_meas": self._last_linear_vel,
            "omega_meas": self._last_angular_vel,
            "left_ticks": left_ticks,
            "right_ticks": right_ticks,
            "left_rpm": self._last_actual_rpm[0],
            "right_rpm": self._last_actual_rpm[1],
            "status_flags": status_flags,
        }

    # ---- small compatibility helpers ----
    def _set_target_rpm(self, motor, rpm):
        # Support either set_target_rpm() or target_rpm property
        if hasattr(motor, "set_target_rpm"):
            motor.set_target_rpm(rpm)
        else:
            motor.target_rpm = rpm  # your Motor

    def _step_motor(self, motor):
        # Support step()
        if hasattr(motor, "step"):
            motor.step()

    def _brake_motor(self, motor):
        if hasattr(motor, "brake"):
            motor.brake()

    def _read_motor_rpm(self, motor):
        enc = getattr(motor, "encoder", None)
        if enc is None:
            return 0.0
        if hasattr(enc, "signed_rpm"):
            return enc.signed_rpm
        return getattr(enc, "rpm", 0.0)

    def _compute_body_velocities(self, l_rpm, r_rpm):
        v_l = self._rpm_to_linear(l_rpm)
        v_r = self._rpm_to_linear(r_rpm)
        linear = 0.5 * (v_l + v_r)
        angular = 0.0
        if self._L != 0:
            angular = (v_r - v_l) / self._L
        return linear, angular

    def _rpm_to_linear(self, rpm):
        return (rpm * self._C) / 60.0
