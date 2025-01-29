# pid_controller.py

import time

class PIDController:
    def __init__(self, Kp, Ki, Kd, sample_time):
        """
        :param Kp, Ki, Kd: PID constants
        :param sample_time: in seconds, e.g. 0.05 for 20 Hz
        """
        self.Kp = Kp
        self.Ki = Ki
        self.Kd = Kd
        self.sample_time = sample_time

        # Internal PID state
        self.integral = 0.0
        self.prev_error = 0.0
        self.prev_time = time.ticks_ms()

        # Output limits
        self.output_min = -255
        self.output_max = 255

        self.target_speed = 0.0  # now this is in m/s

    def reset(self):
        """ Reset internal PID state (integrator, prev_error, etc.) """
        self.integral = 0.0
        self.prev_error = 0.0
        self.prev_time = time.ticks_ms()

    def set_target(self, target_m_s):
        """ Set a new target speed in m/s """
        self.target_speed = target_m_s

    def update(self, current_speed_m_s):
        """
        Called every sample_time (or close).
        :param current_speed_m_s: measured speed in m/s
        :return: motor PWM command (range -255..255 in this example)
        """
        now = time.ticks_ms()
        dt_ms = time.ticks_diff(now, self.prev_time)
        if dt_ms < (self.sample_time * 1000):
            # Not enough time has passed; skip PID update
            return None  # or return last output if you prefer

        self.prev_time = now
        dt = dt_ms / 1000.0

        # PID error
        error = self.target_speed - current_speed_m_s

        # Integrator
        self.integral += error * dt

        # Derivative
        derivative = (error - self.prev_error) / dt if dt != 0 else 0

        # PID output
        output = (self.Kp * error) + (self.Ki * self.integral) + (self.Kd * derivative)

        # Clamp output
        if output > self.output_max:
            output = self.output_max
        elif output < self.output_min:
            output = self.output_min

        # Save state
        self.prev_error = error

        return output
