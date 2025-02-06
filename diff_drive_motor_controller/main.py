"""
main.py
-------
Example main program to demonstrate forward, backward, and in-place rotation
using the DiffDriveController, Motor, and Encoder classes.
"""

import time
from machine import Pin
from config import (
    LEFT_MOTOR_SPEED_PIN, LEFT_MOTOR_DIRECTION_PIN, LEFT_MOTOR_BRAKE_PIN, LEFT_MOTOR_ENCODER_PIN,
    RIGHT_MOTOR_SPEED_PIN, RIGHT_MOTOR_DIRECTION_PIN, RIGHT_MOTOR_BRAKE_PIN, RIGHT_MOTOR_ENCODER_PIN
)
from encoder import Encoder
from motor import Motor
from diff_drive_controller import DiffDriveController

def main():
    # --- Create Encoders ---
    left_encoder = Encoder(pin_num=LEFT_MOTOR_ENCODER_PIN, ticks_per_rev=90)
    right_encoder = Encoder(pin_num=RIGHT_MOTOR_ENCODER_PIN, ticks_per_rev=90)
    
    # --- Create Motors ---
    # NOTE: Depending on your physical wiring, you may need to set invert=True on one side
    # so that both wheels spin 'forward' with the same sign of target RPM.
    left_motor = Motor(
        speed_pin=LEFT_MOTOR_SPEED_PIN,
        direction_pin=LEFT_MOTOR_DIRECTION_PIN,
        brake_pin=LEFT_MOTOR_BRAKE_PIN,
        encoder=left_encoder,
        invert=True
    )
    right_motor = Motor(
        speed_pin=RIGHT_MOTOR_SPEED_PIN,
        direction_pin=RIGHT_MOTOR_DIRECTION_PIN,
        brake_pin=RIGHT_MOTOR_BRAKE_PIN,
        encoder=right_encoder,
        invert=False  # Often the right motor needs to be inverted, adjust as needed
    )

    # --- Create Differential Drive Controller ---
    diff_drive = DiffDriveController(left_motor, right_motor)

    def run_for_seconds(linear_m_s, angular_rad_s, duration_s=3):
        """
        Helper function to run a certain (linear, angular) command for `duration_s` seconds.
        """
        diff_drive.update_cmd_vel(linear=linear_m_s, angular=angular_rad_s)
        t_start = time.ticks_ms()
        while time.ticks_diff(time.ticks_ms(), t_start) < (duration_s * 1000):
            # Convert desired (linear, angular) to left/right wheel RPM
            rpm_left, rpm_right = diff_drive.compute_wheel_rpms()

            # Update each motor with the computed RPM setpoint
            left_motor.set_target_rpm(rpm_left)
            right_motor.set_target_rpm(rpm_right)

            # Run motor control loop
            left_motor.update()
            right_motor.update()

            time.sleep(0.01)  # 10 ms loop time (adjust as needed)

    try:
        # Test sequence: forward, stop, backward, stop, rotate in place

        print("Moving forward...")
        run_for_seconds(linear_m_s=0.2, angular_rad_s=0.0, duration_s=3)

        print("Stopping...")
        run_for_seconds(linear_m_s=0.0, angular_rad_s=0.0, duration_s=1)

        print("Moving backward...")
        run_for_seconds(linear_m_s=-0.2, angular_rad_s=0.0, duration_s=3)

        print("Stopping...")
        run_for_seconds(linear_m_s=0.0, angular_rad_s=0.0, duration_s=1)

        print("Rotating in place (counterclockwise)...")
        run_for_seconds(linear_m_s=0.0, angular_rad_s=1.0, duration_s=3)

        print("Stopping...")
        run_for_seconds(linear_m_s=0.0, angular_rad_s=0.0, duration_s=1)

        print("Done with test sequence.")

    except KeyboardInterrupt:
        print("Interrupted by user, stopping.")
        diff_drive.update_cmd_vel(0.0, 0.0)
        # Optionally brake motors:
        left_motor.brake()
        right_motor.brake()

if __name__ == "__main__":
    main()
