"""
config.py
----------
Configuration file for the robot's motor control, encoder parameters, PID settings,
and robot geometry. All units are in SI unless noted otherwise.
"""
import math

# ===== PWM Settings =====
PWM_FREQ = 1000  # PWM frequency in Hz

# ===== Motor PWM Limits =====
FULL_DUTY = 65535          # Maximum duty cycle value (16-bit)
MAX_DUTY_PERCENT = 0.35    # Limit duty cycle to 35% of full power for safety
MAX_DUTY = int(MAX_DUTY_PERCENT * FULL_DUTY)
MIN_DUTY = 8000            # Minimum duty cycle to overcome motor deadband

# ===== PID Gains =====
PID = {
    "Kp": 7.0,    # Proportional gain
    "Ki": 15.0,   # Integral gain
    "Kd": 0.2     # Derivative gain
}

# ===== Feed-Forward Parameters =====
Kff = 135      # Feed-forward gain
offset = 6116  # Constant offset for feed-forward

# ===== Slew-Rate Limiter Parameter =====
SLEW_MAX_DELTA = 10000  # Maximum allowed change in PWM output per control loop iteration

# ===== Timeout Settings =====
CMD_VEL_TIMEOUT = 500    # Timeout (in milliseconds) for cmd_vel commands

# ===== Robot Geometry =====
# Given values: WHEEL_RADIUS = 10 inches, WHEEL_SEPARATION = 19 inches.
# Convert inches to meters (1 inch = 0.0254 m).
WHEEL_RADIUS_INCH = 10
WHEEL_SEPARATION_INCH = 19
WHEEL_RADIUS = WHEEL_RADIUS_INCH * 0.0254        # Wheel radius in meters (~0.254 m)
WHEEL_SEPARATION = WHEEL_SEPARATION_INCH * 0.0254  # Distance between wheels in meters (~0.4826 m)
WHEEL_CIRCUMFERENCE = 2 * math.pi *WHEEL_RADIUS

# ===== Motor Pin Assignments =====
# Adjust these based on your wiring.
LEFT_MOTOR_SPEED_PIN = 18     
LEFT_MOTOR_DIRECTION_PIN = 19 
LEFT_MOTOR_ENCODER_PIN = 20   
LEFT_MOTOR_BRAKE_PIN = 21     

RIGHT_MOTOR_SPEED_PIN = 13    
RIGHT_MOTOR_DIRECTION_PIN = 12
RIGHT_MOTOR_ENCODER_PIN = 11  
RIGHT_MOTOR_BRAKE_PIN = 10    
