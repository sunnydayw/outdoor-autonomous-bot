"""
config.py
----------
Configuration file for the robot's motor control, encoder parameters, PID settings,
and robot geometry. All units are in SI unless noted otherwise.
"""
import math

# ===== PWM Settings =====
PWM_FREQ = 10000  # PWM frequency in Hz

# ===== Motor PWM Limits =====
FULL_DUTY = 65535          # Maximum duty cycle value (16-bit)
MIN_DUTY = 3500            # Minimum duty cycle to overcome motor deadband
MAX_DUTY_PERCENT = 0.8    # Limit duty cycle to percent of full power for safety
MAX_DUTY = int(MAX_DUTY_PERCENT * FULL_DUTY)
# max rpm should be aroud 200
# ===== PID Gains =====
PID = {
    "Kp": 75.0,    # Proportional gain
    "Ki": 7.5,   # Integral gain
    "Kd": 2.5     # Derivative gain
}

# ===== Feed-Forward Parameters =====
Kff = 165     # Feed-forward gain
offset = 1789  # Constant offset for feed-forward

"""
How to get Kff and offset (60-second calibration):
Command two steady wheel speeds (e.g., 40 RPM and 100 RPM).
For each, wait 1–2 s, read the applied duty.
Compute:
Kff = (duty2 - duty1) / (rpm2 - rpm1)
offset = duty1 - Kff * rpm1
"""

# ===== Slew-Rate Limiter Parameter =====
SLEW_MAX_DELTA = 3000  # Maximum allowed change in PWM output per control loop iteration

# ===== Timeout Settings =====
CMD_VEL_TIMEOUT = 500    # Timeout (in milliseconds) for cmd_vel commands

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

# — Encoder pins — #
ENC_1A_PIN      = 18   # Motor 1 channel A
ENC_1B_PIN      = 19   # Motor 1 channel B
ENC_2A_PIN      = 20   # Motor 2 channel A
ENC_2B_PIN      = 21   # Motor 2 channel B

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

# === Battery Voltage Sensor ===
# ADC pin for reading battery voltage via voltage divider
# ADC2 on GP28 with 1:11 divider
BATTERY_ADC_PIN = 28  # GP28 / ADC2
VREF = 3.3
DIVIDER_RATIO = 1 / 11

# — RPM calculation window — #
WINDOW_MS       = 100  # how many ms of history to use for RPM smoothing

# — Encoder geometry — #
EDGE_FACTOR     = 2    # Quad encoder correction factor (2 for both rising and falling edges using single channel)
PULSES_PER_REV  = 13   # your encoder spec (already quad-corrected)
GEAR_RATIO      = 28   # motor rev : output rev
TICKS_PER_REV   = PULSES_PER_REV * GEAR_RATIO * EDGE_FACTOR  # 13 × 28 x 2 = 728 ticks/output rev

# ===== Robot Geometry =====
# Given values: WHEEL_RADIUS = 10 inches, WHEEL_SEPARATION = 19 inches.
# Convert inches to meters (1 inch = 0.0254 m).
WHEEL_RADIUS_INCH = 1.3
WHEEL_SEPARATION_INCH = 4.5
WHEEL_RADIUS = WHEEL_RADIUS_INCH * 0.0254        # Wheel radius in meters
WHEEL_SEPARATION = WHEEL_SEPARATION_INCH * 0.0254  # Distance between wheels in meters
WHEEL_CIRCUMFERENCE = 2 * math.pi *WHEEL_RADIUS

distance_per_pulse    = WHEEL_CIRCUMFERENCE / TICKS_PER_REV



