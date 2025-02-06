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
from config import PWM_FREQ, FULL_DUTY, MAX_DUTY, PID, Kff, offset, SLEW_MAX_DELTA

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

        # Set initial motor direction
        # if self.invert is False, then self.current_direction is assigned 1
        self.current_direction = 1 if not self.invert else 0
        self.direction.value(self.current_direction)

        # Set PID gains.
        self.Kp = PID["Kp"]
        self.Ki = PID["Ki"]
        self.Kd = PID["Kd"]

        # Feed-forward parameters
        self.Kff = Kff
        self.offset = offset

        # Control state variables
        self.target_rpm = 0
        self.integral = 0
        self.last_error = 0
        self.last_output = 0
        self.last_time = time.ticks_ms()

    def set_target_rpm(self, rpm: int):
        """
        Set the desired RPM for this motor.
        :param rpm: Target RPM.
        """
        # Set direction based on RPM sign
        target_direction = 1 if rpm >= 0 else 0

        # Flip direction if the motor is inverted
        if self.invert:
            target_direction = not target_direction  # Flip 0 → 1, 1 → 0

        if target_direction != self.current_direction:
            self.current_direction = target_direction
            self.direction.value(self.current_direction)

        self.target_rpm = abs(rpm)

    def brake(self):
        """Stop the motor using active braking for 1 second."""
        self.speed_pwm.duty_u16(0)
        self.brake_pwm.duty_u16(FULL_DUTY)
        time.sleep(1)
        self.brake_pwm.duty_u16(0)

    def update(self):
        """
        Call this regularly (e.g. in a loop) to update motor PWM based on 
        the current encoder reading and the target RPM using PID + feed-forward.
        """
        current_rpm = self.encoder.update_rpm()
        current_time = time.ticks_ms()
        dt_ms = time.ticks_diff(current_time, self.last_time)

        # Ensure enough time has passed before updating
        if dt_ms < 10 or self.target_rpm == 0:
            return

        dt_sec = dt_ms / 1000.0  # Convert to seconds

        # --- PID Error Terms ---
        error = self.target_rpm - current_rpm

        # --- Prevent Integral Windup ---
        if abs(error) < 100:  # Only integrate if error is reasonable
            self.integral += error * dt_sec
        self.integral = max(min(self.integral, 500), -500)  # Clamp integral

        # --- Compute PID Output ---
        derivative = (error - self.last_error) / dt_sec
        pid_output = (self.Kp * error) + (self.Ki * self.integral) + (self.Kd * derivative)

        # --- Feed-Forward Term ---
        #   feed_forward = Kff * (desired_rpm) + offset
        feed_forward = (self.Kff * self.target_rpm) + self.offset

        # --- Combine PID and Feed-Forward ---
        raw_output = int(feed_forward + pid_output)

        # --- Apply Slew Rate Limiting ---
        delta = raw_output - self.last_output
        if delta > SLEW_MAX_DELTA:
            raw_output = self.last_output + SLEW_MAX_DELTA
        elif delta < -SLEW_MAX_DELTA:
            raw_output = self.last_output - SLEW_MAX_DELTA

        # --- Clamp to PWM Range ---
        # output = int(max(min(output, MAX_DUTY), MIN_DUTY)) # might not want to calmp the minium for now
        output = min(raw_output, MAX_DUTY)

        # --- Set PWM ---
        self.speed_pwm.duty_u16(int(output))

        # Update variables
        self.last_error = error
        self.last_output = output
        self.last_time = current_time