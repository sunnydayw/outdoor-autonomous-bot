# motor.py
import time
from machine import Pin, PWM
from test_config import *

class Motor:
    def __init__(self, direction_pin, speed_pin, brake_pin, encoder, reverse_dir = False):
        self.direction = Pin(direction_pin, Pin.OUT)
        self.speed_pwm = PWM(Pin(speed_pin))
        self.brake_pwm = PWM(Pin(brake_pin))
        self.encoder = encoder
        self.reverse_dir = reverse_dir  # Store the physical installation flag

        # Initialize PWM channels
        self.speed_pwm.freq(PWM_FREQ)
        self.brake_pwm.freq(PWM_FREQ)
        self.brake_pwm.duty_u16(0)  # Ensure brake is released

        # Set initial motor direction (default forward)
        # For a motor installed in reverse, the default is flipped.
        self.direction.value(0 if reverse_dir else 1)

        # Set PID gains from configuration
        self.Kp = PID["Kp"]
        self.Ki = PID["Ki"]
        self.Kd = PID["Kd"]

    def set_power(self, percent_power):
        """
        Open-loop control: Set the motor power to a specified percentage.
        percent_power: Desired power in percent (0 to 100), relative to FULL_DUTY.
        The value is converted to a duty cycle. Also, if the computed duty is nonzero
        but below MIN_DUTY, it will be bumped up to MIN_DUTY.
        """
        # Optionally, you might want to restrict the maximum percentage (e.g., to MAX_DUTY_PERCENT*100)
        # Here we assume percent_power is relative to FULL_DUTY.
        desired_duty = int((percent_power / 100.0) * FULL_DUTY)
        # Optionally clip to a maximum duty (using MAX_DUTY from test_config)
        if desired_duty > MAX_DUTY:
            desired_duty = MAX_DUTY
        if desired_duty > 0 and desired_duty < MIN_DUTY:
            desired_duty = MIN_DUTY
        self.speed_pwm.duty_u16(desired_duty)

    def rotate_counts(self, target_counts):
        # Reset the encoder count before starting motion
        self.encoder.reset()

        # PID state initialization
        integral = 0.0
        last_error = target_counts  # since encoder starts at 0
        last_time = time.ticks_ms()
        max_integral = 10000  # anti-windup limit

        start_time = time.ticks_ms()

        while self.encoder.read() < target_counts and time.ticks_diff(time.ticks_ms(), start_time) < MAX_RUN_TIME_MS:
            current_time = time.ticks_ms()
            dt = time.ticks_diff(current_time, last_time) / 1000.0  # seconds
            if dt <= 0:
                dt = 0.01
            last_time = current_time

            error = target_counts - self.encoder.read()

            integral += error * dt
            # Clamp the integral to avoid windup
            if integral > max_integral:
                integral = max_integral
            elif integral < -max_integral:
                integral = -max_integral

            derivative = (error - last_error) / dt
            last_error = error

            pid_correction = PID["Kp"] * error + PID["Ki"] * integral + PID["Kd"] * derivative

            # Compute the feed-forward contribution
            feed_forward = Kff * target_counts + 10 # offset

            # Total computed output (in PWM units)
            total_output = feed_forward + pid_correction

            # Enforce PWM limits
            if output < 0:
                output = 0
            if output > MAX_DUTY:
                output = MAX_DUTY

            self.speed_pwm.duty_u16(int(output))
            time.sleep(0.02)

        # End-of-motion: stop motor and apply brake
        self.speed_pwm.duty_u16(0)
        self.brake_pwm.duty_u16(65535)
        time.sleep(0.5)
        self.brake_pwm.duty_u16(0)

    def set_rpm(self, target_rpm, run_time=None):
        """
        Blocking closed-loop control: Run the motor at the specified RPM using PID with feed-forward.
        Negative target_rpm indicates reverse motion (taking into account the reverse_dir flag).
        This function blocks until run_time seconds have elapsed.
        """
        # Determine motor direction.
        if target_rpm < 0:
            desired_direction = 0 if not self.reverse_dir else 1
            target_rpm = -target_rpm  # Use absolute value for control calculations.
        else:
            desired_direction = 1 if not self.reverse_dir else 0
        self.direction.value(desired_direction)
        self.encoder.reset()

        # Initialize PID state variables.
        integral = 0.0
        last_error = 0.0
        start_time = time.ticks_ms()
        last_time = start_time

        # For slew-rate limiting.
        last_output = 0

        while run_time is None or time.ticks_diff(time.ticks_ms(), start_time) < run_time * 1000:
            current_time = time.ticks_ms()
            dt = time.ticks_diff(current_time, last_time) / 1000.0
            if dt < 0.02:
                continue
            last_time = current_time

            measured_rpm = self.encoder.get_rpm()
            error = target_rpm - measured_rpm

            integral += error * dt
            derivative = (error - last_error) / dt
            last_error = error

            pid_output = self.Kp * error + self.Ki * integral + self.Kd * derivative
            feed_forward = Kff * target_rpm + offset
            output = feed_forward + pid_output

            if output < 0:
                output = 0
            if output > FULL_DUTY:
                output = FULL_DUTY
            elif 0 < output < MIN_DUTY:
                output = MIN_DUTY

            # Apply slew-rate limiting.
            delta = output - last_output
            if delta > SLEW_MAX_DELTA:
                output = last_output + SLEW_MAX_DELTA
            elif delta < -SLEW_MAX_DELTA:
                output = last_output - SLEW_MAX_DELTA
            last_output = output

            self.speed_pwm.duty_u16(int(output))
            time.sleep_ms(20)

        # Stop the motor.
        self.speed_pwm.duty_u16(0)
        self.brake_pwm.duty_u16(FULL_DUTY)
        time.sleep(0.5)
        self.brake_pwm.duty_u16(0)