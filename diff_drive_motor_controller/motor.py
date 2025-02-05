"""
motor.py
---------
Motor control module.
Provides a Motor class with methods for open-loop and closed-loop control.
Closed-loop control uses a PID controller with feed-forward and includes a slew-rate limiter.
Both blocking and asynchronous (non-blocking) set_rpm functions are provided.
"""

import time
from machine import Pin, PWM
from config import PWM_FREQ, FULL_DUTY, MIN_DUTY, MAX_DUTY, PID, Kff, offset, SLEW_MAX_DELTA

class Motor:
    def __init__(self, direction_pin, speed_pin, brake_pin, encoder, invert=False):
        """
        Initialize the Motor.
        
        :param direction_pin: GPIO pin for motor direction control.
        :param speed_pin: GPIO pin for PWM speed control.
        :param brake_pin: GPIO pin for brake control.
        :param encoder: Encoder instance for feedback.
        :param invert: Boolean, set True if motor direction is reversed.
        """
        self.direction = Pin(direction_pin, Pin.OUT)
        self.speed_pwm = PWM(Pin(speed_pin))
        self.brake_pwm = PWM(Pin(brake_pin))
        self.encoder = encoder
        self.invert = invert

        # Initialize PWM channels.
        self.speed_pwm.freq(PWM_FREQ)
        self.brake_pwm.freq(PWM_FREQ)
        self.brake_pwm.duty_u16(0)  # Release brake.

        # Set initial motor direction.
        self.direction.value(0 if invert else 1)

        # Set PID gains.
        self.Kp = PID["Kp"]
        self.Ki = PID["Ki"]
        self.Kd = PID["Kd"]

        # Feed-forward parameters
        self.Kff = Kff
        self.offset = offset

        # Control state variables
        self.target_rpm = 0.0
        self.integral = 0.0
        self.last_error = 0.0
        self.last_output = 0.0
        self.last_time = time.ticks_ms()

    def set_target_rpm(self, rpm):
        """
        Set the desired RPM for this motor.
        :param rpm: Target RPM.
        """
        # Set direction based on RPM sign
        if rpm < 0:
            desired_direction = 0 if not self.invert else 1
            target_rpm = -rpm  # Use absolute value.
        else:
            desired_direction = 1 if not self.invert else 0
        self.direction.value(desired_direction)

        self.target_rpm = abs(rpm)

    def brake(self):
        # Stop the motor.
        self.speed_pwm.duty_u16(0)
        self.brake_pwm.duty_u16(FULL_DUTY)
        time.sleep(0.5)
        self.brake_pwm.duty_u16(0)

    def update(self):
        """
        Call this regularly (e.g. in a loop) to update motor PWM based on 
        the current encoder reading and the target RPM using PID + feed-forward.
        """
        current_rpm = self.encoder.get_rpm()
        current_time = time.ticks_ms()
        dt = time.ticks_diff(current_time, self.last_time) / 1000.0  # Seconds

        if dt <= 0.01 or self.target_rpm == 0:
            return

        # --- PID Error Terms ---
        error = self.target_rpm - current_rpm
        self.integral += error * dt
        derivative = (error - self.last_error) / dt

        # --- PID Control Output ---
        pid_output = (self.Kp * error) + (self.Ki * self.integral) + (self.Kd * derivative)

        # --- Feed-Forward Term ---
        #   feed_forward = Kff * (desired_rpm) + offset
        feed_forward = (self.Kff * self.target_rpm) + self.offset

        # --- Combine PID and Feed-Forward ---
        raw_output = feed_forward + pid_output

        # --- Slew-Rate Limit ---
        delta = raw_output - self.last_output
        if delta > SLEW_MAX_DELTA:
            output = SLEW_MAX_DELTA
        elif delta < -SLEW_MAX_DELTA:
            output = -SLEW_MAX_DELTA
        output = self.last_output + delta

        # --- Clamp to PWM Range ---
        #   Could be positive or negative (for direction).
        # output = int(max(min(output, MAX_DUTY), MIN_DUTY)) # might not want to calmp the minium for now
        output = int(min(output, MAX_DUTY))

        # --- Set PWM ---
        self.speed_pwm.duty_u16(int(output))

        # Update variables
        self.last_error = error
        self.last_output = output
        self.last_time = current_time