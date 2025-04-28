# test_config.py
# Configuration file for the robot's motor control, encoders, and PID settings.

# ===== PWM Settings =====
PWM_FREQ = 10000  # PWM frequency in Hz

# ===== Motor PWM Limits =====
FULL_DUTY = 65535  # Maximum duty cycle value for 16-bit PWM
MAX_DUTY_PERCENT = 0.75  # Limit duty cycle to 35% of full power for safety
MAX_DUTY = int(MAX_DUTY_PERCENT * FULL_DUTY)  # Calculate maximum duty cycle value
MIN_DUTY = 8000  # Minimum duty cycle to overcome motor deadband

# ===== PID Gains =====
# PID controller gains for acceleration and cruising control.
PID = {
    "Kp": 7.0,  # Proportional gain
    "Ki": 15.0,   # Integral gain
    "Kd": 0.2   # Derivative gain
}
# ===== Feed-Forward Parameter =====
# Feed-forward term to provide a baseline PWM based on desired velocity.
Kff = 135
offset = 6116

# ===== Slew-Rate Limiter Parameter =====
SLEW_MAX_DELTA = 10000  # Maximum change in PWM output per control loop iteration

# ===== Motor Pin Assignments =====
# Define pin assignments for the left and right motors.

# Left Motor
LEFT_MOTOR_SPEED_PIN = 18    # PWM pin for controlling speed
LEFT_MOTOR_DIRECTION_PIN = 19  # Pin for controlling direction (forward/reverse)
LEFT_MOTOR_ENCODER_PIN = 20   # Pin for reading encoder signals
LEFT_MOTOR_BRAKE_PIN = 21     # Pin for engaging/disengaging the brake

# Right Motor
RIGHT_MOTOR_SPEED_PIN = 13    # PWM pin for controlling speed
RIGHT_MOTOR_DIRECTION_PIN = 12  # Pin for controlling direction (forward/reverse)
RIGHT_MOTOR_ENCODER_PIN = 11   # Pin for reading encoder signals
RIGHT_MOTOR_BRAKE_PIN = 10     # Pin for engaging/disengaging the brake

# ===== Timeout Settings =====
# Maximum runtime for the robot in milliseconds.
# This is a safety feature to prevent the robot from running indefinitely.
MAX_RUN_TIME_MS = 30000  # 30 seconds


# ===== Motor Parameters =====
TICKS_PER_REV = 90