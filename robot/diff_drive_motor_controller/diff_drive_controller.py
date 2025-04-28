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
        
        # Desired velocities
        self._linear = 0.0
        self._angular = 0.0
        self._last_cmd_time = time.ticks_ms()
        
        # Configuration
        self.cmd_vel_timeout = CMD_VEL_TIMEOUT
        
        # Performance tracking
        self._last_target_rpm = (0, 0)
        self._last_actual_rpm = (0, 0)
        self._last_status_update = time.ticks_ms()

        # Timeout flag for monitoring.
        self._timeout_flag = False
        # Loop time for update_motors (in us).
        self._last_loop_time = 0

    def update_cmd_vel(self, linear: float, angular: float):
        """
        Update desired velocities from a cmd_vel command.
        :param linear: Linear velocity (m/s).
        :param angular: Angular velocity (rad/s).
        """
        self._linear = linear
        self._angular = angular
        self._last_cmd_time = time.ticks_ms()
        
    def compute_wheel_rpms(self):
        """
        Convert current linear and angular velocities into target RPMs for each wheel.

        Differential drive kinematics:
            v_left  = linear - (angular * WHEEL_SEPARATION / 2)
            v_right = linear + (angular * WHEEL_SEPARATION / 2)
        Then, convert wheel speed (m/s) to RPM:
            RPM = (v / (2 * π * WHEEL_RADIUS)) * 60
        """
        v_left = self._linear - (self._angular * WHEEL_SEPARATION / 2)
        v_right = self._linear + (self._angular * WHEEL_SEPARATION / 2)
        
        rpm_left = (v_left * 60) / WHEEL_CIRCUMFERENCE
        rpm_right = (v_right * 60) / WHEEL_CIRCUMFERENCE
        
        self._last_target_rpm = (rpm_left, rpm_right)
        return round(rpm_left, 2), round(rpm_right, 2)
    
    def stop_motors(self):
        """Safely stop both motors."""
        self.left_motor.set_target_rpm(0)
        self.right_motor.set_target_rpm(0)
        self.left_motor.brake()
        self.right_motor.brake()

    def update_motors(self):
        """
        Compute and set motor speeds based on cmd_vel.
        Includes motor synchronization and timeout handling.
        """
        start_loop = time.ticks_us()
        current_time = time.ticks_ms()
        
        # Check for command timeout
        if time.ticks_diff(current_time, self._last_cmd_time) > self.cmd_vel_timeout:
            self._timeout_flag = True
            self.stop_motors()
            return
    
        # If a valid command is present, clear any previous timeout flag.
        self._timeout_flag = False

        # Compute target RPMs
        rpm_left, rpm_right = self.compute_wheel_rpms()
        
        # Update both motors simultaneously
        self.left_motor.set_target_rpm(rpm_left)
        self.right_motor.set_target_rpm(rpm_right)
        
        # Update both motors
        self.left_motor.update()
        self.right_motor.update()
        
        # Store actual RPMs for monitoring
        self._last_actual_rpm = (self.left_motor.current_rpm, self.right_motor.current_rpm)

        # Calculate loop time.
        self._last_loop_time = time.ticks_diff(time.ticks_us(), start_loop)

    def get_diagnostics(self):
        """Return current motor status for monitoring."""
        return {
            'timeout': self._timeout_flag,
            'loop_time': self._last_loop_time
        }