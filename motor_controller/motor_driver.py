# motor_driver.py

from machine import Pin, PWM


# ----------------------------------------------------------------
# Motor configuration
# ----------------------------------------------------------------
PWM_FREQUENCY = 20000

# If you truly want the full range (0..65535), you can define:
FULL_RANGE_DUTY = 65535
MAX_DUTY = int(65535/4) # Max 16-bit PWM duty cycle value
MIN_DUTY = 655*15  # Minimum duty cycle to keep the motor running

# Pin assignments (adjust to your wiring)
LEFT_SPEED_PIN  = 18
LEFT_DIR_PIN    = 19
LEFT_BRAKE_PIN  = 21

RIGHT_SPEED_PIN = 13
RIGHT_DIR_PIN   = 12
RIGHT_BRAKE_PIN = 10

class Motor:
    def __init__(self, dir_pin, brake_pin, speed_pin):
        # Direction is a digital OUT
        self.dir_pin = Pin(dir_pin, Pin.OUT)
        
        # brake is a PWM
        self.brake_pwm = PWM(Pin(brake_pin))
        self.brake_pwm.freq(PWM_FREQUENCY)
        self.brake_pwm.duty_u16(0)  # 0 => release brake (coast)
        
        # Speed pin is PWM
        self.speed_pwm = PWM(Pin(speed_pin))
        self.speed_pwm.freq(PWM_FREQUENCY)
        self.speed_pwm.duty_u16(0)
        
    # ------------------------------------------------------------
    # 1) Set speed by raw duty or 'speed' (like old code -255..255)
    # ------------------------------------------------------------
    def set_speed(self, speed):
        """
        :param speed: integer in [-255..255]
                      negative => reverse
        """
        # Clip
        if speed > 255: speed = 255
        if speed < -255: speed = -255

        forward = (speed >= 0)
        abs_speed = abs(speed)

        # Direction
        self.dir_pin.value(1 if forward else 0)

        # Release brake (coast) for this example
        self.brake_pwm.duty_u16(0)

        # Scale 0..255 => 0..65535
        duty_val = abs_speed * 257  # 255 * 257 = ~65535
        if duty_val > MAX_DUTY:
            duty_val = MAX_DUTY

        # Optionally enforce a minimum duty to avoid stalling
        if duty_val < MIN_DUTY and duty_val > 0:
            duty_val = MIN_DUTY

        self.speed_pwm.duty_u16(int(duty_val))

    # ------------------------------------------------------------
    # 2) Set speed by percentage (0..100)
    # ------------------------------------------------------------
    def set_speed_percent(self, percent, forward=True):
        """
        :param percent: 0..100
        :param forward: True => forward, False => reverse
        """
        if percent < 0:   percent = 0
        if percent > 100: percent = 100

        self.dir_pin.value(1 if forward else 0)
        self.brake_pwm.duty_u16(0)  # release brake

        # Convert percentage to duty
        duty_val = int((percent / 100.0) * FULL_RANGE_DUTY)
        if duty_val > MAX_DUTY:
            duty_val = MAX_DUTY
        if duty_val < MIN_DUTY and duty_val > 0:
            duty_val = MIN_DUTY

        self.speed_pwm.duty_u16(duty_val)

    # ------------------------------------------------------------
    # 3) Stop (coast)
    # ------------------------------------------------------------
    def stop(self):
        """Set speed to 0 (coast)."""
        self.speed_pwm.duty_u16(0)
        self.brake_pwm.duty_u16(0)

    # ------------------------------------------------------------
    # 4) Brake with percentage
    # ------------------------------------------------------------
    def brake(self, percent=100):
        """
        :param percent: 0..100 (% brake force)
            - 0% = No braking (coast)
            - 100% = Full braking (max duty cycle)
        """
        if percent < 0:
            percent = 0
        if percent > 100:
            percent = 100

        # Convert % to 16-bit duty cycle
        duty_val = int((percent / 100.0) * FULL_RANGE_DUTY)

        # Stop the speed PWM
        self.speed_pwm.duty_u16(0)

        # Apply braking force
        self.brake_pwm.duty_u16(duty_val)


    # ------------------------------------------------------------
    # 5) Run at a specified speed for a given time, then stop & brake
    # ------------------------------------------------------------
    def run_for_time(self, speed_percent, ms, forward=True, brake_percent=100):
        """
        Run the motor at the given speed (0-100%) for 'ms' milliseconds,
        then stop and apply braking.

        :param speed_percent: Speed as a percentage (0-100%)
        :param ms: Time in milliseconds to run
        :param forward: Direction (True = forward, False = reverse)
        :param brake_percent: Brake force after stopping (0-100%)
                            - 0% = No braking (coast)
                            - 100% = Full braking (immediate stop)
        """
        # Set speed before starting
        self.set_speed_percent(speed_percent, forward)

        start_time = time.ticks_ms()
        
        while time.ticks_diff(time.ticks_ms(), start_time) < ms:
            time.sleep_ms(1)  # Prevent CPU overuse

        # Stop the motor after time is up
        self.stop()

        # Apply braking force
        self.brake(brake_percent)


    # ------------------------------------------------------------
    # 6) Run at a given speed until a certain encoder count is reached
    # ------------------------------------------------------------
    def run_for_counts(self, motor_index, speed_percent, target_counts, encoder_func, forward=True, brake_percent=100):
        """
        Run the motor at the given speed (0-100%) until reaching the specified encoder count.
        Then stop and apply braking.

        :param motor_index: 0 or 1 (if your encoder_driver needs it)
        :param speed_percent: Speed as a percentage (0-100%)
        :param target_counts: Number of counts to move from the current position
        :param encoder_func: Function to read encoder count (e.g. encoder_driver.read_encoder)
        :param forward: Direction (True = forward, False = reverse)
        :param brake_percent: Brake force after stopping (0-100%)
                            - 0% = No braking (coast)
                            - 100% = Full braking (immediate stop)
        """
        # Get starting encoder count
        start_counts = encoder_func(motor_index)
        target = start_counts + target_counts

        # Set motor speed and direction
        self.set_speed_percent(speed_percent, forward)

        # Loop until reaching the target encoder count
        while True:
            current_counts = encoder_func(motor_index)
            if forward and current_counts >= target:
                break
            if not forward and current_counts <= target:
                break
            time.sleep_ms(1)  # Small delay to check frequently

        # Stop the motor and apply braking
        self.stop()
        self.brake(brake_percent)



# ----------------------------------------------------------------
# Global references to each motor
# ----------------------------------------------------------------
motor_left = Motor(LEFT_DIR_PIN, LEFT_BRAKE_PIN, LEFT_SPEED_PIN)
motor_right= Motor(RIGHT_DIR_PIN, RIGHT_BRAKE_PIN, RIGHT_SPEED_PIN)


def init_motor_driver():
    """
    If you need to do any special driver init, do it here.
    For now, the Motor constructor does most of the config already.
    """
    pass


# ----------------------------------------------------------------
# Utility: Set motor speed by old style -255..255
# ----------------------------------------------------------------
def set_motor_speed(motor_index, speed):
    if motor_index == 0:
        motor_left.set_speed(speed)
    else:
        motor_right.set_speed(speed)

# ----------------------------------------------------------------
# Utility: Set BOTH motors speed by old style -255..255
# ----------------------------------------------------------------
def set_motor_speeds(left_speed, right_speed):
    motor_left.set_speed(left_speed)
    motor_right.set_speed(right_speed)