# differential_drivetrain.py
"""
DiffDriveController (ROS-style) for MicroPython.

- Accepts cmd_vel (linear m/s, angular rad/s) via update_cmd_vel()
- Converts to left/right wheel RPM using standard diff-drive kinematics
- Applies a cmd_vel timeout (in milliseconds) to stop motors if commands go stale
- Compatible with two motor API styles:
    1) target_rpm property + step()          (your Motor class)
    2) set_target_rpm(rpm) method + update() (common in other projects)
"""

import time
from config import WHEEL_CIRCUMFERENCE, WHEEL_SEPARATION, CMD_VEL_TIMEOUT

try:
    from proto import DriveFeedbackStatusFlags
except Exception:  # proto is optional during unit tests / simple runs
    class DriveFeedbackStatusFlags:
        COMMAND_TIMEOUT = 1 << 0


class DiffDriveController:
    """
    Differential drive controller that translates (v, ω) into wheel RPMs
    and drives two motor objects (left and right).
    """

    def __init__(self,
                 left_motor,
                 right_motor,
                 wheel_circumference=WHEEL_CIRCUMFERENCE,
                 wheel_separation=WHEEL_SEPARATION,
                 cmd_vel_timeout_ms=CMD_VEL_TIMEOUT):
        """
        :param left_motor:  Motor instance for the left wheel.
        :param right_motor: Motor instance for the right wheel.
        :param wheel_circumference: Wheel circumference [m].
        :param wheel_separation:    Distance between wheels [m].
        :param cmd_vel_timeout_ms:  Command timeout in milliseconds. If no
                                    cmd_vel is received within this period,
                                    both motors are stopped and a timeout flag
                                    is set in diagnostics / feedback.
        """
        self.left_motor = left_motor
        self.right_motor = right_motor

        # Geometry/config (meters)
        self._C = float(wheel_circumference)   # wheel circumference [m]
        self._L = float(wheel_separation)      # wheel separation  [m]

        # Timeout [ms]; None = no timeout
        if cmd_vel_timeout_ms is None:
            self._timeout_ms = None
        else:
            self._timeout_ms = int(cmd_vel_timeout_ms)

        # Command state (body velocities)
        self._linear = 0.0     # m/s
        self._angular = 0.0    # rad/s
        self._last_cmd_time = time.ticks_ms()

        # Telemetry
        self._last_target_rpm = (0.0, 0.0)
        self._last_actual_rpm = (0.0, 0.0)
        self._timeout_flag = False
        self._last_loop_time_us = 0
        self._last_linear_vel = 0.0
        self._last_angular_vel = 0.0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def update_cmd_vel(self, linear: float, angular: float) -> None:
        """
        Update desired body velocities.

        :param linear:  Linear velocity [m/s].
        :param angular: Angular velocity [rad/s].
        """
        self._linear = float(linear)
        self._angular = float(angular)
        self._last_cmd_time = time.ticks_ms()

    def compute_wheel_rpms(self):
        """
        Compute left/right wheel RPM from commanded (v, ω).

        Kinematics:
            v_l = v - (ω * L / 2)
            v_r = v + (ω * L / 2)
            RPM = (v / C) * 60

        Returns:
            (rpm_l, rpm_r) rounded to 2 decimals for human-friendly display.
        """
        v_l = self._linear - (self._angular * self._L * 0.5)
        v_r = self._linear + (self._angular * self._L * 0.5)

        rpm_l = (v_l * 60.0) / self._C
        rpm_r = (v_r * 60.0) / self._C

        # Keep full precision internally for diagnostics / control.
        self._last_target_rpm = (rpm_l, rpm_r)

        return round(rpm_l, 2), round(rpm_r, 2)

    def stop_motors(self, brake: bool = True) -> None:
        """
        Safely stop both motors, set setpoints to zero, and optionally brake.

        Note:
            - For your Motor class, target_rpm = 0 immediately zeroes PWM.
            - The extra step/update call is kept for compatibility with
              other motor implementations that only apply zero on update().
        """
        self._set_target_rpm(self.left_motor, 0.0)
        self._set_target_rpm(self.right_motor, 0.0)

        # Ensure at least one control-loop iteration for compatible motors.
        self._step_motor(self.left_motor)
        self._step_motor(self.right_motor)

        if brake:
            self._brake_motor(self.left_motor)
            self._brake_motor(self.right_motor)

        # Telemetry reset
        self._last_target_rpm = (0.0, 0.0)
        self._last_actual_rpm = (0.0, 0.0)
        self._last_linear_vel = 0.0
        self._last_angular_vel = 0.0

    def update_motors(self) -> None:
        """
        Main control-loop entry point.

        - Enforces cmd_vel timeout.
        - Computes wheel RPM setpoints.
        - Pushes them to the motors and advances their control loops.
        - Updates internal telemetry (measured RPM, v, ω, loop timing).
        """
        start_us = time.ticks_us()
        now_ms = time.ticks_ms()

        # --- Timeout handling ---
        if (self._timeout_ms is not None) and \
           (time.ticks_diff(now_ms, self._last_cmd_time) > self._timeout_ms):
            self._timeout_flag = True
            self.stop_motors(brake=True)
            self._last_loop_time_us = time.ticks_diff(time.ticks_us(), start_us)
            return

        self._timeout_flag = False

        # --- Compute setpoints (RPM) ---
        rpm_l, rpm_r = self.compute_wheel_rpms()

        # Push setpoints to motors (direction handled inside Motor).
        self._set_target_rpm(self.left_motor, rpm_l)
        self._set_target_rpm(self.right_motor, rpm_r)

        # Advance each motor control loop (step/update).
        self._step_motor(self.left_motor)
        self._step_motor(self.right_motor)

        # --- Capture actuals if available ---
        l_rpm = self._read_motor_rpm(self.left_motor)
        r_rpm = self._read_motor_rpm(self.right_motor)
        self._last_actual_rpm = (l_rpm, r_rpm)
        self._last_linear_vel, self._last_angular_vel = \
            self._compute_body_velocities(l_rpm, r_rpm)

        self._last_loop_time_us = time.ticks_diff(time.ticks_us(), start_us)

    def get_diagnostics(self) -> dict:
        """
        Return a small status dict suitable for printing/logging.
        """
        return {
            "timeout": self._timeout_flag,
            "loop_time_us": self._last_loop_time_us,
            "target_rpm": {
                "left": self._last_target_rpm[0],
                "right": self._last_target_rpm[1],
            },
            "actual_rpm": {
                "left": self._last_actual_rpm[0],
                "right": self._last_actual_rpm[1],
            },
            "cmd": {
                "linear_mps": self._linear,
                "angular_rps": self._angular,
            },
            "body": {
                "linear_mps": self._last_linear_vel,
                "angular_rps": self._last_angular_vel,
            },
        }

    def get_drive_feedback(self) -> dict:
        """
        Return a telemetry-friendly snapshot of the drivetrain state.

        Uses encoder ticks (if available) and status flags for higher-level
        planners or logging.
        """
        # Encoders are optional; we fall back to 0 if missing.
        left_enc = getattr(self.left_motor, "encoder", None)
        right_enc = getattr(self.right_motor, "encoder", None)
        left_ticks = getattr(left_enc, "ticks", 0)
        right_ticks = getattr(right_enc, "ticks", 0)

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

    # ------------------------------------------------------------------
    # Compatibility helpers
    # ------------------------------------------------------------------

    def _set_target_rpm(self, motor, rpm: float) -> None:
        """
        Support either set_target_rpm(rpm) or target_rpm property.
        """
        if hasattr(motor, "set_target_rpm"):
            motor.set_target_rpm(rpm)
        else:
            motor.target_rpm = rpm  # your Motor

    def _step_motor(self, motor) -> None:
        """
        Advance the motor control loop.

        Supported patterns:
            - motor.step()
            - motor.update()
        """
        if hasattr(motor, "step"):
            motor.step()
        elif hasattr(motor, "update"):
            motor.update()

    def _brake_motor(self, motor) -> None:
        """Brake motor if it exposes a brake() method."""
        if hasattr(motor, "brake"):
            motor.brake()

    def _read_motor_rpm(self, motor) -> float:
        """
        Read motor wheel RPM from its encoder, if available.
        """
        enc = getattr(motor, "encoder", None)
        if enc is None:
            return 0.0
        if hasattr(enc, "signed_rpm"):
            return enc.signed_rpm
        return getattr(enc, "rpm", 0.0)

    def _compute_body_velocities(self, l_rpm: float, r_rpm: float):
        """
        Convert wheel RPMs back to body linear / angular velocities.
        """
        v_l = self._rpm_to_linear(l_rpm)
        v_r = self._rpm_to_linear(r_rpm)
        linear = 0.5 * (v_l + v_r)
        angular = (v_r - v_l) / self._L if self._L != 0 else 0.0
        return linear, angular

    def _rpm_to_linear(self, rpm: float) -> float:
        """Convert wheel RPM to linear speed [m/s]."""
        return (rpm * self._C) / 60.0
