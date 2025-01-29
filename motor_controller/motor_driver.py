from machine import Pin, PWM
import time

PWM_FREQUENCY = 20000
FULL_RANGE_DUTY = 65535
MAX_DUTY = FULL_RANGE_DUTY // 4
MIN_DUTY = 655 * 15

class Motor:
    """Motor driver class with PWM control."""

    def __init__(self, dir_pin, brake_pin, speed_pin):
        """Initialize motor with direction, brake, and speed pins."""
        self.dir_pin = Pin(dir_pin, Pin.OUT)
        
        self.brake_pwm = PWM(Pin(brake_pin))
        self.brake_pwm.freq(PWM_FREQUENCY)
        self.brake_pwm.duty_u16(0)  # Release brake
        
        self.speed_pwm = PWM(Pin(speed_pin))
        self.speed_pwm.freq(PWM_FREQUENCY)
        self.speed_pwm.duty_u16(0)

    def set_speed(self, speed):
        """Set motor speed in range -255 to 255."""
        speed = max(min(speed, 255), -255)  # Clamp speed
        forward = speed >= 0
        duty_val = abs(speed) * 257  # Scale 0..255 => 0..65535

        self.dir_pin.value(1 if forward else 0)
        self.brake_pwm.duty_u16(0)  # Release brake

        # Apply min/max duty constraints
        if duty_val > MAX_DUTY:
            duty_val = MAX_DUTY
        elif duty_val < MIN_DUTY and duty_val > 0:
            duty_val = MIN_DUTY

        self.speed_pwm.duty_u16(duty_val)

    def set_speed_percent(self, percent, forward=True):
        """Set speed as a percentage (0-100%)."""
        percent = max(min(percent, 100), 0)
        duty_val = int((percent / 100.0) * FULL_RANGE_DUTY)

        self.dir_pin.value(1 if forward else 0)
        self.brake_pwm.duty_u16(0)  # Release brake

        if duty_val > MAX_DUTY:
            duty_val = MAX_DUTY
        elif 0 < duty_val < MIN_DUTY:
            duty_val = MIN_DUTY

        self.speed_pwm.duty_u16(duty_val)

    def stop(self):
        """Stop motor (coast)."""
        self.speed_pwm.duty_u16(0)
        self.brake_pwm.duty_u16(0)

    def brake(self, percent=100):
        """Apply braking force (0-100%)."""
        percent = max(min(percent, 100), 0)
        self.speed_pwm.duty_u16(0)
        duty_val = int((percent / 100.0) * FULL_RANGE_DUTY)
        self.brake_pwm.duty_u16(duty_val)

    def run_for_time(self, speed_percent, ms, forward=True, brake_percent=100):
        """
        Run motor at speed for given time (milliseconds), then stop and brake.
        """
        self.set_speed_percent(speed_percent, forward)
        start_time = time.ticks_ms()

        while time.ticks_diff(time.ticks_ms(), start_time) < ms:
            time.sleep_ms(10)  # Simple delay
        
        self.stop()
        self.brake(brake_percent)

    def run_for_counts(self, encoder, speed_percent, target_counts, forward=True, brake_percent=100):
        """Run motor until reaching a given change in encoder counts."""
        start_counts = encoder.get_count()
        if forward:
            target = start_counts + target_counts
        else:
            target = start_counts - target_counts
        
        self.set_speed_percent(speed_percent, forward)

        while True:
            current_counts = encoder.get_count()
            if forward and current_counts >= target:
                break
            if not forward and current_counts <= target:
                break
            time.sleep_ms(5)

        self.stop()
        self.brake(brake_percent)


# ----------------------------------------------------------------
# Global references to motors
# ----------------------------------------------------------------
motor_left = None
motor_right = None

def init_motor_driver(left_dir_pin=19, left_brake_pin=21, left_speed_pin=18,
                      right_dir_pin=12, right_brake_pin=10, right_speed_pin=13):
    """Initialize both motors."""
    global motor_left, motor_right

    motor_left = Motor(left_dir_pin, left_brake_pin, left_speed_pin)
    motor_right = Motor(right_dir_pin, right_brake_pin, right_speed_pin)
    print("[MOTOR] Left and Right Motor drivers initialized!")

def set_motor_speed(left_speed, right_speed):
    """Set speed for both motors using -255..255 range."""
    if motor_left and motor_right:
        motor_left.set_speed(left_speed)
        motor_right.set_speed(right_speed)

def set_motor_speeds_percent(left_percent, right_percent, forward_left=True, forward_right=True):
    """Set speed for both motors using 0..100% range."""
    if motor_left and motor_right:
        motor_left.set_speed_percent(left_percent, forward_left)
        motor_right.set_speed_percent(right_percent, forward_right)
