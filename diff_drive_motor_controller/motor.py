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

        # Set PID gains (cast to float for precision).
        self.Kp = float(PID["Kp"])
        self.Ki = float(PID["Ki"])
        self.Kd = float(PID["Kd"])

        # Feed-forward parameters
        self.Kff = Kff
        self.offset = offset

        # Control state variables (using float precision).
        self.target_rpm = 0.0
        self.integral = 0.0
        self.last_error = 0.0
        self.last_output = 0.0
        self.last_time = time.ticks_ms()
        self._update_loop_time = 0 
        self._current_rpm = 0.0  # Cached RPM value

        # PID term storage for diagnostics.
        self.p_term = 0.0
        self.i_term = 0.0
        self.d_term = 0.0

    @property
    def update_loop_time(self):
        """Return the execution time of the last update loop in milliseconds."""
        return self._update_loop_time
    
    @property 
    def current_rpm(self):
        """Return the current RPM of the motor."""
        return self._current_rpm
    
    def get_latest_rpm(self):
        """Force an update of the encoder and return the latest RPM."""
        self._current_rpm = self.encoder.update_rpm()
        return self._current_rpm
    
    def set_target_rpm(self, rpm: float):
        """
        Set the desired RPM for this motor.
        :param rpm: Target RPM (float). The absolute value is stored with two decimal precision.
        """
        # Set direction based on RPM sign
        target_direction = 1 if rpm >= 0 else 0

        # Flip direction if the motor is inverted
        if self.invert:
            target_direction = not target_direction  # Flip 0 → 1, 1 → 0

        if target_direction != self.current_direction:
            self.current_direction = target_direction
            self.direction.value(self.current_direction)

        # Store the target RPM as a positive float rounded to 2 decimal places.
        self.target_rpm = round(abs(rpm), 2)

    def update_pid(self, kp=None, ki=None, kd=None):
        """
        Update the PID coefficients.
        
        :param kp: New proportional gain (optional).
        :param ki: New integral gain (optional).
        :param kd: New derivative gain (optional).
        """
        if kp is not None:
            self.Kp = kp
        if ki is not None:
            self.Ki = ki
        if kd is not None:
            self.Kd = kd

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
        start_time = time.ticks_us()
        # Update and cache RPM
        self._current_rpm = self.encoder.update_rpm()

        current_time = time.ticks_ms()
        dt_ms = time.ticks_diff(current_time, self.last_time)

        # Ensure enough time has passed before updating
        if dt_ms < 10 or self.target_rpm == 0:
            return

        dt_sec = dt_ms / 1000.0  # Convert to seconds

        # --- PID Error Terms ---
        error = self.target_rpm - self._current_rpm

        # --- Prevent Integral Windup ---
        if abs(error) < 40:  # Only integrate if error is reasonable
            self.integral += error * dt_sec
        # self.integral = max(min(self.integral, 100), -100)  # Clamp integral

        # --- Derivative Calculation ---
        derivative = (error - self.last_error) / dt_sec
        
        # --- Compute Individual PID Terms for Diagnostics ---
        self.p_term = self.Kp * error
        self.i_term = self.Ki * self.integral
        self.d_term = self.Kd * derivative

        # --- Compute PID Output ---
        pid_output = int(self.p_term + self.i_term + self.d_term)

        # --- Feed-Forward Term ---
        #   feed_forward = Kff * (desired_rpm) + offset
        feed_forward = int((self.Kff * self.target_rpm) + self.offset)

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
        self._update_loop_time = time.ticks_diff(time.ticks_us(), start_time)

    def get_diagnostics(self):
        """
        Return a dictionary of motor diagnostics data for monitoring.
        Includes target RPM, current RPM, each PID term, the output, and loop time.
        """
        return {
            "target_rpm": round(self.target_rpm, 2),
            "current_rpm": round(self._current_rpm, 2),
            "p_term": round(self.p_term, 2),
            "i_term": round(self.i_term, 2),
            "d_term": round(self.d_term, 2),
            "output": int(self.last_output),
            "loop_time": self._update_loop_time
        }