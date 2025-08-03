"""
config.py
----------
Configuration file for the robot's motor control, encoder parameters, PID settings,
and robot geometry. All units are in SI unless noted otherwise.
"""
import math
import machine

# ===== PWM Settings =====
PWM_FREQ = 10000  # PWM frequency in Hz

# ===== Motor PWM Limits =====
FULL_DUTY = 65535          # Maximum duty cycle value (16-bit)
MAX_DUTY_PERCENT = 0.65    # Limit duty cycle to percent of full power for safety
MAX_DUTY = int(MAX_DUTY_PERCENT * FULL_DUTY)
MIN_DUTY = 8000            # Minimum duty cycle to overcome motor deadband

# ===== PID Gains =====
PID = {
    "Kp": 135.0,    # Proportional gain
    "Ki": 150.0,   # Integral gain
    "Kd": 25.0     # Derivative gain
}

# ===== Feed-Forward Parameters =====
Kff = 0 #165      # Feed-forward gain
offset = 0 #6116  # Constant offset for feed-forward

# ===== Slew-Rate Limiter Parameter =====
SLEW_MAX_DELTA = 1000  # Maximum allowed change in PWM output per control loop iteration

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

# === I2C Configuration for IMU (MPU6050) ===
I2C_ID       = 1
I2C_SDA_PIN  = 26   # GP26
I2C_SCL_PIN  = 27   # GP27
I2C_FREQ     = 400000  # 400 kHz

# === UART Configuration for Communication with Raspberry Pi ===
UART_ID        = 0
UART_TX_PIN    = 0   # GP0
UART_RX_PIN    = 1   # GP1
UART_BAUDRATE  = 115200

# === Battery Voltage Sensor ===
# ADC pin for reading battery voltage via voltage divider
# ADC2 on GP28 with 1:11 divider
BATTERY_ADC_PIN = 28  # GP28 / ADC2
VREF = 3.3
DIVIDER_RATIO = 1 / 11

# — Encoder pins — #
ENC_1A_PIN      = 18   # Motor 1 channel A
ENC_1B_PIN      = 19   # Motor 1 channel B
ENC_2A_PIN      = 20   # Motor 2 channel A
ENC_2B_PIN      = 21   # Motor 2 channel B

# — Encoder geometry — #
EDGE_FACTOR     = 2    # Quad encoder correction factor (2 for both rising and falling edges using single channel)
PULSES_PER_REV  = 13   # your encoder spec (already quad-corrected)
GEAR_RATIO      = 28   # motor rev : output rev
TICKS_PER_REV   = PULSES_PER_REV * GEAR_RATIO*EDGE_FACTOR  # 13 × 28 x 2 = 728 ticks/output rev

# — RPM calculation window — #
WINDOW_MS       = 500  # how many ms of history to use for RPM smoothing

# === Motor Driver Standby ===
# STBY pin to enable/disable motor driver IC
MOTOR_STBY_PIN = 15  # GP15

# === Motor Control Pins ===
# Each motor has one PWM pin and two direction pins (IN1, IN2)
MOTOR1_PWM_PIN = 6   # GP6 (PWM)
MOTOR1_IN1_PIN = 8   # GP8
MOTOR1_IN2_PIN = 7   # GP7

MOTOR2_PWM_PIN = 10   # GP10 (PWM)
MOTOR2_IN1_PIN = 12   # GP12
MOTOR2_IN2_PIN = 11   # GP11
