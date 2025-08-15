# pid.py
class PIDController:
    """
    PID + feed-forward controller with optional slew-rate limiting.
    """
    def __init__(
        self,
        Kp: float,
        Ki: float,
        Kd: float,
        Kff: float = 0.0,
        offset: float = 0.0,
        slewrate: float = None,
        duty_min: int = 0,
        duty_max: int = 65535
    ):
        self.Kp = Kp
        self.Ki = Ki
        self.Kd = Kd
        self.Kff = Kff
        self.offset = offset

        self.slewrate  = slewrate
        self.duty_min  = duty_min
        self.duty_max  = duty_max

        # internal state
        self.integral    = 0.0
        self.last_error  = 0.0
        self.last_output = duty_min

    def compute(self, target: float, current: float, dt: float) -> int:
        """
        Compute new duty for given error over dt seconds.
        """
        error = target - current
        self.integral += error * dt
        derivative = (error - self.last_error) / dt if dt > 0 else 0.0

        # PID terms
        p_out = self.Kp * error
        i_out = self.Ki * self.integral
        d_out = self.Kd * derivative

        pid = p_out + i_out + d_out
        ff  = self.Kff * target + self.offset

        raw = pid + ff

        # Slew-rate limiting
        if self.slewrate is not None:
            delta = raw - self.last_output
            if delta > self.slewrate:
                raw = self.last_output + self.slewrate
            elif delta < -self.slewrate:
                raw = self.last_output - self.slewrate

        # Clamp to allowed duty range
        out = int(max(min(raw, self.duty_max), self.duty_min))

        # Save state for next call
        self.last_error  = error
        self.last_output = out

        return out
