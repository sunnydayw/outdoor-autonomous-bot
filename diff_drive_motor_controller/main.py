"""
main.py
---------
Main application for the differential drive robot.
This module initializes the motors, encoders, and the diff drive controller,
and starts the asynchronous control loop.
It also contains a simulated cmd_vel publisher for testing purposes.

For final deployment, you may replace the simulated cmd_vel source with a wired
serial communication link or network interface, depending on your robot's setup.
Both the Raspberry Pi and the Pico support network communication, and for a final
setup you might use a direct serial (UART) connection between the devices.
"""

import uasyncio as asyncio
from motor import Motor  # Motor class with both blocking and async methods.
from encoder import Encoder
from diff_drive_controller import DiffDriveController
from config import (LEFT_MOTOR_DIRECTION_PIN, LEFT_MOTOR_SPEED_PIN, LEFT_MOTOR_BRAKE_PIN, LEFT_MOTOR_ENCODER_PIN,
                    RIGHT_MOTOR_DIRECTION_PIN, RIGHT_MOTOR_SPEED_PIN, RIGHT_MOTOR_BRAKE_PIN, RIGHT_MOTOR_ENCODER_PIN)

# Create encoder instances for left and right wheels.
left_encoder = Encoder(LEFT_MOTOR_ENCODER_PIN, ticks_per_rev=90)
right_encoder = Encoder(RIGHT_MOTOR_ENCODER_PIN, ticks_per_rev=90)

# Create Motor instances.
left_motor = Motor(LEFT_MOTOR_DIRECTION_PIN, LEFT_MOTOR_SPEED_PIN, LEFT_MOTOR_BRAKE_PIN, left_encoder, reverse_dir=False)
right_motor = Motor(RIGHT_MOTOR_DIRECTION_PIN, RIGHT_MOTOR_SPEED_PIN, RIGHT_MOTOR_BRAKE_PIN, right_encoder, reverse_dir=True)

# Create the differential drive controller.
controller = DiffDriveController(left_motor, right_motor)

async def simulate_cmd_vel():
    """
    Simulated cmd_vel publisher.
    For testing, this coroutine publishes a constant linear velocity (in m/s) and angular velocity (in rad/s)
    every 100 ms. Replace this with your actual communication code (e.g., serial or network) in the final setup.
    """
    while True:
        linear = 0.2   # m/s (adjust as needed)
        angular = 0.0  # rad/s (nonzero for turning)
        controller.update_cmd_vel(linear, angular)
        await asyncio.sleep(0.1)

async def main():
    # Run the simulated cmd_vel publisher and the diff drive control loop concurrently.
    await asyncio.gather(
        simulate_cmd_vel(),
        controller.control_loop()
    )

asyncio.run(main())
