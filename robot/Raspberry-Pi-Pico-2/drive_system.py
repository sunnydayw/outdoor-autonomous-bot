# drive_system.py
"""
DriveSystem

Convenience wrapper that assembles the complete drive stack:
    - TB6612 motor driver
    - Encoders
    - PID controllers
    - Motor wrappers
    - Differential drive controller

All hardware configuration is pulled from the global `config` module, so
`main.py` can stay small and focused on behavior.
"""

import config
from driver import TB6612Driver
from encoder import Encoder
from motor import Motor
from pid import PIDController
from differential_drivetrain import DiffDriveController


class DriveSystem:
    """Bundle the drive electronics and expose a simple high-level API."""

    def __init__(self,
                 cfg=config,
                 invert_left: bool = False,
                 invert_right: bool = False,
                 min_loop_ms: int = 5):
        self.cfg = cfg

        # --- Low-level driver (TB6612) ---
        self.driver = TB6612Driver(
            in1_a=cfg.MOTOR1_IN1_PIN,
            in2_a=cfg.MOTOR1_IN2_PIN,
            pwm_a=cfg.MOTOR1_PWM_PIN,
            in1_b=cfg.MOTOR2_IN1_PIN,
            in2_b=cfg.MOTOR2_IN2_PIN,
            pwm_b=cfg.MOTOR2_PWM_PIN,
            standby_pin=cfg.MOTOR_STBY_PIN,
            freq=cfg.PWM_FREQ,
        )

        # --- Encoders ---
        self.left_encoder = Encoder(cfg.ENC_1A_PIN, cfg.ENC_1B_PIN)
        self.right_encoder = Encoder(cfg.ENC_2A_PIN, cfg.ENC_2B_PIN)

        # --- PID Controllers (cloned config) ---
        pid_kwargs = dict(
            Kp=cfg.PID["Kp"],
            Ki=cfg.PID["Ki"],
            Kd=cfg.PID["Kd"],
            Kff=getattr(cfg, "Kff", 0.0),
            offset=getattr(cfg, "offset", 0.0),
            slewrate=getattr(cfg, "SLEW_MAX_DELTA", None),
            duty_min=getattr(cfg, "MIN_DUTY", 0),
            duty_max=getattr(cfg, "MAX_DUTY", 65535),
            integral_limit=getattr(cfg, "INTEGRAL_LIMIT", None),
        )

        self.left_pid = PIDController(**pid_kwargs)
        self.right_pid = PIDController(**pid_kwargs)

        # --- High-level motors ---
        self.left_motor = Motor(
            self.driver, 'A',
            self.left_encoder,
            self.left_pid,
            invert=invert_left,
            min_loop_ms=min_loop_ms,
        )
        self.right_motor = Motor(
            self.driver, 'B',
            self.right_encoder,
            self.right_pid,
            invert=invert_right,
            min_loop_ms=min_loop_ms,
        )

        # --- Differential drive controller ---
        self.controller = DiffDriveController(
            self.left_motor,
            self.right_motor,
            wheel_circumference=cfg.WHEEL_CIRCUMFERENCE,
            wheel_separation=cfg.WHEEL_SEPARATION,
            cmd_vel_timeout_ms=cfg.CMD_VEL_TIMEOUT,
        )

    # ------------------------------------------------------------------
    # High-level facade API
    # ------------------------------------------------------------------

    def set_cmd_vel(self, linear_mps: float, angular_rps: float) -> None:
        """
        Set desired body velocities for the robot.

        :param linear_mps:  Linear velocity [m/s].
        :param angular_rps: Angular velocity [rad/s].
        """
        self.controller.update_cmd_vel(linear_mps, angular_rps)

    def update(self) -> None:
        """
        Run one control-loop iteration for the drive stack.

        Call this regularly in main (e.g. 20–100 Hz).
        """
        self.controller.update_motors()

    def stop(self, brake: bool = True) -> None:
        """
        Stop the robot by stopping both motors.

        :param brake: If True, request motor brake after stopping.
        """
        self.controller.stop_motors(brake=brake)

    def emergency_stop(self) -> None:
        """
        Emergency stop entire drive system (if supported by driver).

        - Attempts driver.emergency_stop() if available.
        - Otherwise falls back to stop() with brake=True.
        """
        if hasattr(self.driver, "emergency_stop"):
            self.driver.emergency_stop()
        else:
            self.stop(brake=True)

    def get_drive_feedback(self) -> dict:
        """Return a telemetry snapshot of the drive state."""
        return self.controller.get_drive_feedback()

    def get_diagnostics(self) -> dict:
        """Return diagnostics from the diff-drive controller."""
        return self.controller.get_diagnostics()
