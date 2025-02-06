"""
diff_drive_controller.py
-------------------------
DiffDriveController module.
This module implements a ROS-style differential drive controller that accepts cmd_vel
commands (linear and angular velocities) and converts them into individual wheel RPM commands.
It also implements a cmd_vel timeout feature to stop the motors if no new command is received.
"""

import time
from config import WHEEL_CIRCUMFERENCE, WHEEL_SEPARATION, CMD_VEL_TIMEOUT

class DiffDriveController:
    def __init__(self, left_motor, right_motor):
        """
        Initialize the differential drive controller.
        
        :param left_motor: Motor instance for the left wheel.
        :param right_motor: Motor instance for the right wheel.
        """
        self.left_motor = left_motor
        self.right_motor = right_motor

        # Desired cmd_vel velocities.
        self.linear = 0.0    # Linear velocity in m/s.
        self.angular = 0.0   # Angular velocity in rad/s.
        self.last_cmd_time = time.ticks_ms()

        # Timeout for cmd_vel (in milliseconds).
        self.cmd_vel_timeout = CMD_VEL_TIMEOUT

        # Tracking for debugging and PID tuning
        self.last_target_rpm = (0, 0)
        self.last_actual_rpm = (0, 0)
        self.last_status_update = time.ticks_ms()

    def update_cmd_vel(self, linear, angular):
        """
        Update desired velocities from a cmd_vel command.
        
        :param linear: Linear velocity (m/s).
        :param angular: Angular velocity (rad/s).
        """
        self.linear = linear
        self.angular = angular
        self.last_cmd_time = time.ticks_ms()

    def compute_wheel_rpms(self):
        """
        Convert current linear and angular velocities into target RPMs for each wheel.
        Differential drive kinematics:
            v_left  = linear - (angular * WHEEL_SEPARATION / 2)
            v_right = linear + (angular * WHEEL_SEPARATION / 2)
        Then, convert wheel speed (m/s) to RPM:
            RPM = (v / (2 * π * WHEEL_RADIUS)) * 60
        
        :return: Tuple (rpm_left, rpm_right)
        """
        v_left = self.linear - (self.angular * WHEEL_SEPARATION / 2)
        v_right = self.linear + (self.angular * WHEEL_SEPARATION / 2)
        rpm_left = int((v_left * 60) / WHEEL_CIRCUMFERENCE)
        rpm_right = int((v_right * 60) / WHEEL_CIRCUMFERENCE)
        
        self.last_target_rpm = (rpm_left, rpm_right)  # Store for status reporting
        return rpm_left, rpm_right
    
    def update_motors(self):
        """
        Compute and set motor speeds based on cmd_vel.
        If timeout occurs, stop motors.
        """
        # Check if command has timed out
        current_time = time.ticks_ms()
        if time.ticks_diff(current_time, self.last_cmd_time) > self.cmd_vel_timeout:
            self.left_motor.set_target_rpm(0)
            self.right_motor.set_target_rpm(0)
            self.left_motor.brake()
            self.right_motor.brake()
            return

        # Compute new wheel RPMs
        rpm_left, rpm_right = self.compute_wheel_rpms()

        # Send commands to motors
        self.left_motor.set_target_rpm(rpm_left)
        self.right_motor.set_target_rpm(rpm_right)
        self.left_motor.update()
        self.right_motor.update()

        # Store last actual RPMs for monitoring
        self.last_actual_rpm = (self.left_motor.encoder.read_rpm(), self.right_motor.encoder.read_rpm())

    def get_status(self, print_status=False, STATUS_UPDATE_INTERVAL=500):
        """
        Return a dictionary of current control parameters for debugging.
        Updates only if STATUS_UPDATE_INTERVAL has elapsed.
        
        :param print_status: If True, prints the status.
        """
        current_time = time.ticks_ms()
        if time.ticks_diff(current_time, self.last_status_update) < STATUS_UPDATE_INTERVAL:
            return  # Skip update if interval hasn't passed

        self.last_status_update = current_time  # Update last update time
        timed_out = time.ticks_diff(current_time, self.last_cmd_time) > self.cmd_vel_timeout

        status = {
            "target_rpm_left": round(self.last_target_rpm[0], 2),
            "target_rpm_right": round(self.last_target_rpm[1], 2),
            "actual_rpm_left": round(self.last_actual_rpm[0], 2),
            "actual_rpm_right": round(self.last_actual_rpm[1], 2),
            "cmd_vel_timeout": timed_out
        }

        if print_status:
            print(f"[STATUS] Left: {status['actual_rpm_left']} RPM / {status['target_rpm_left']} Target, "
                  f"Right: {status['actual_rpm_right']} RPM / {status['target_rpm_right']} Target, "
                  f"Timeout: {status['cmd_vel_timeout']}")

        return status