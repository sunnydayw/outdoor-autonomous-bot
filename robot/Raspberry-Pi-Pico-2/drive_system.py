"""drive_system.py

Convenience helpers that assemble the complete drive stack (driver, encoders,
PID controllers, motors, and the differential-drive controller) from the global
``config`` module.

It keeps the existing low-level classes decoupled while offering a compact,
readable way to bring the hardware online inside ``main.py`` or test scripts.
"""

from driver import TB6612Driver
from encoder import Encoder
from motor import Motor
from pid import PIDController
from differential_drivetrain import DiffDriveController
import config


class DriveSystem:
    """Bundle the drive electronics and expose a single controller handle."""

    def __init__(self,
                 cfg=config,
                 invert_left=False,
                 invert_right=False,
                 min_loop_ms=5):
        self.cfg = cfg

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

        self.left_encoder = Encoder(cfg.ENC_1A_PIN, cfg.ENC_1B_PIN)
        self.right_encoder = Encoder(cfg.ENC_2A_PIN, cfg.ENC_2B_PIN)

        pid_kwargs = dict(
            Kp=cfg.PID["Kp"],
            Ki=cfg.PID["Ki"],
            Kd=cfg.PID["Kd"],
            Kff=getattr(cfg, "Kff", 0.0),
            offset=getattr(cfg, "offset", 0.0),
            slewrate=getattr(cfg, "SLEW_MAX_DELTA", None),
            duty_min=getattr(cfg, "MIN_DUTY", 0),
            duty_max=getattr(cfg, "MAX_DUTY", 65535),
        )

        self.left_pid = PIDController(**pid_kwargs)
        self.right_pid = PIDController(**pid_kwargs)

        self.left_motor = Motor(self.driver, 'A', self.left_encoder,
                                self.left_pid, invert=invert_left,
                                min_loop_ms=min_loop_ms)
        self.right_motor = Motor(self.driver, 'B', self.right_encoder,
                                 self.right_pid, invert=invert_right,
                                 min_loop_ms=min_loop_ms)

        self.controller = DiffDriveController(
            self.left_motor,
            self.right_motor,
            wheel_circumference=cfg.WHEEL_CIRCUMFERENCE,
            wheel_separation=cfg.WHEEL_SEPARATION,
            cmd_vel_timeout=cfg.CMD_VEL_TIMEOUT,
        )

    # Convenience pass-throughs -------------------------------------------------
    def update(self):
        self.controller.update_motors()

    def stop(self):
        self.controller.stop_motors()

    def get_drive_feedback(self):
        return self.controller.get_drive_feedback()

    def get_diagnostics(self):
        return self.controller.get_diagnostics()
