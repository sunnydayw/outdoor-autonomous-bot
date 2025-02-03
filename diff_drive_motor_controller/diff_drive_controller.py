"""
diff_drive_controller.py
-------------------------
DiffDriveController module.
This module implements a ROS-style differential drive controller that accepts cmd_vel
commands (linear and angular velocities) and converts them into individual wheel RPM commands.
It also implements a cmd_vel timeout feature to stop the motors if no new command is received.
"""

import time
import math
import uasyncio as asyncio
from config import WHEEL_RADIUS, WHEEL_SEPARATION, CMD_VEL_TIMEOUT

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
        rpm_left = (v_left * 60) / (2 * math.pi * WHEEL_RADIUS)
        rpm_right = (v_right * 60) / (2 * math.pi * WHEEL_RADIUS)
        return rpm_left, rpm_right

    async def control_loop(self):
        """
        Non-blocking control loop that:
          - Checks for cmd_vel timeout (stopping motors if no command is received).
          - Converts desired cmd_vel into target wheel RPMs.
          - Commands the motors using their asynchronous set_rpm_async() functions.
        """
        while True:
            current_time = time.ticks_ms()
            # If no new cmd_vel command within timeout, stop motors.
            if time.ticks_diff(current_time, self.last_cmd_time) > self.cmd_vel_timeout:
                await asyncio.gather(
                    self.left_motor.set_rpm_async(0, run_time=0.05),
                    self.right_motor.set_rpm_async(0, run_time=0.05)
                )
            else:
                rpm_left, rpm_right = self.compute_wheel_rpms()
                await asyncio.gather(
                    self.left_motor.set_rpm_async(rpm_left, run_time=0.05),
                    self.right_motor.set_rpm_async(rpm_right, run_time=0.05)
                )
            await asyncio.sleep_ms(50)
