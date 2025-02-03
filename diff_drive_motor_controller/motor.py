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
from config import PWM_FREQ, FULL_DUTY, MIN_DUTY, MAX_DUTY, PID, Kff, offset, SLEW_MAX_DELTA, MAX_RUN_TIME_MS

class Motor:
    def __init__(self, direction_pin, speed_pin, brake_pin, encoder, reverse_dir=False):
        """
        Initialize the Motor.
        
        :param direction_pin: GPIO pin for motor direction control.
        :param speed_pin: GPIO pin for PWM speed control.
        :param brake_pin: GPIO pin for brake control.
        :param encoder: Encoder instance for feedback.
        :param reverse_dir: Boolean indicating if the motor is installed in reverse.
        """
        self.direction = Pin(direction_pin, Pin.OUT)
        self.speed_pwm = PWM(Pin(speed_pin))
        self.brake_pwm = PWM(Pin(brake_pin))
        self.encoder = encoder
        self.reverse_dir = reverse_dir

        # Initialize PWM channels.
        self.speed_pwm.freq(PWM_FREQ)
        self.brake_pwm.freq(PWM_FREQ)
        self.brake_pwm.duty_u16(0)  # Release brake.

        # Set initial motor direction.
        self.direction.value(0 if reverse_dir else 1)

        # Set PID gains.
        self.Kp = PID["Kp"]
        self.Ki = PID["Ki"]
        self.Kd = PID["Kd"]

    def set_power(self, percent_power):
        """
        Open-loop control: Set the motor power to a specified percentage.
        
        :param percent_power: Desired power level (0 to 100).
        """
        desired_duty = int((percent_power / 100.0) * FULL_DUTY)
        if desired_duty > MAX_DUTY:
            desired_duty = MAX_DUTY
        if 0 < desired_duty < MIN_DUTY:
            desired_duty = MIN_DUTY
        self.speed_pwm.duty_u16(desired_duty)

    def set_rpm(self, target_rpm, run_time=None):
        """
        Blocking closed-loop control: Run the motor at the specified RPM using PID with feed-forward.
        Negative target_rpm indicates reverse motion (adjusting for reverse_dir).
        This function blocks until run_time seconds have elapsed.
        
        :param target_rpm: Desired RPM (negative for reverse).
        :param run_time: Duration in seconds to run the control loop (None for indefinite).
        """
        if target_rpm < 0:
            desired_direction = 0 if not self.reverse_dir else 1
            target_rpm = -target_rpm  # Use absolute value.
        else:
            desired_direction = 1 if not self.reverse_dir else 0
        self.direction.value(desired_direction)
        self.encoder.reset()

        integral = 0.0
        last_error = 0.0
        start_time = time.ticks_ms()
        last_time = start_time
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

    async def set_rpm_async(self, target_rpm, run_time=None):
        """
        Asynchronous (non-blocking) closed-loop control: Run the motor at the specified RPM.
        Negative target_rpm indicates reverse motion. This coroutine yields control periodically.
        
        :param target_rpm: Desired RPM (negative for reverse).
        :param run_time: Duration in seconds for the control loop (None for indefinite).
        """
        import uasyncio as asyncio
        if target_rpm < 0:
            desired_direction = 0 if not self.reverse_dir else 1
            target_rpm = -target_rpm
        else:
            desired_direction = 1 if not self.reverse_dir else 0
        self.direction.value(desired_direction)
        self.encoder.reset()

        integral = 0.0
        last_error = 0.0
        start_time = time.ticks_ms()
        last_time = start_time
        last_output = 0

        while run_time is None or time.ticks_diff(time.ticks_ms(), start_time) < run_time * 1000:
            current_time = time.ticks_ms()
            dt = time.ticks_diff(current_time, last_time) / 1000.0
            if dt < 0.02:
                await asyncio.sleep_ms(10)
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

            delta = output - last_output
            if delta > SLEW_MAX_DELTA:
                output = last_output + SLEW_MAX_DELTA
            elif delta < -SLEW_MAX_DELTA:
                output = last_output - SLEW_MAX_DELTA
            last_output = output

            self.speed_pwm.duty_u16(int(output))
            await asyncio.sleep_ms(20)

        # Stop the motor.
        self.speed_pwm.duty_u16(0)
        self.brake_pwm.duty_u16(FULL_DUTY)
        await asyncio.sleep(500)
        self.brake_pwm.duty_u16(0)
