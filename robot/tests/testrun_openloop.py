# test_motor_rpm.py
import time
from test_motor import Motor
from test_encoder import Encoder
from test_config import LEFT_MOTOR_DIRECTION_PIN, LEFT_MOTOR_SPEED_PIN, LEFT_MOTOR_BRAKE_PIN, LEFT_MOTOR_ENCODER_PIN

# Create an encoder instance.
# Make sure to pass the correct ticks_per_rev value (e.g., 90 if you count both edges on a 45 tick encoder)
encoder = Encoder(LEFT_MOTOR_ENCODER_PIN, ticks_per_rev=90)

# Create a Motor instance.
motor = Motor(LEFT_MOTOR_DIRECTION_PIN, LEFT_MOTOR_SPEED_PIN, LEFT_MOTOR_BRAKE_PIN, encoder, reverse_dir=False)

print("Starting open-loop motor RPM test:")
print("Power (%)    Average RPM")
encoder.reset()

# Iterate from 10% to 50% power in 1% increments.
for power in range(10, 51):
    print("Setting power to {}%".format(power))
    # Set motor open-loop power.
    motor.set_power(power)
    
    # Allow time for the motor to transition and settle.
    time.sleep(2)
    encoder.get_rpm()
    # Collect RPM data for a few seconds.
    sample_duration = 3  # seconds
    sample_start = time.ticks_ms()
    while time.ticks_diff(time.ticks_ms(), sample_start) < sample_duration * 1000:
        time.sleep(0.1)  # Sample every 100 ms.
    
    # Compute RPM.
    rpm = encoder.get_rpm()  # Get RPM from the encoder.
    print("{:3d}%        {:.2f} RPM".format(power, rpm))
    
    # Optionally, reset the encoder count to reduce accumulated error between tests.
    encoder.reset()

# Stop the motor after testing.
motor.set_power(0)
print("Test complete.")
