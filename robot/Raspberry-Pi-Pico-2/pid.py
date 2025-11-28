# pid.py
class PIDController:
    """
    PID + feed-forward controller with optional slew-rate limiting
    and simple integral anti-windup.
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
        duty_max: int = 65535,
        integral_limit: float = None,
    ):
        """
        :param Kp, Ki, Kd:       PID gains.
        :param Kff:              Feed-forward gain on target (open-loop term).
        :param offset:           Constant offset added to output (e.g. deadband).
        :param slewrate:         Max change in output per call (duty units).
        :param duty_min, duty_max: Output clamp in duty units (e.g. 0..65535).
        :param integral_limit:   Optional clamp |integral| <= integral_limit.
        """
        self.Kp = Kp
        self.Ki = Ki
        self.Kd = Kd
        self.Kff = Kff
        self.offset = offset

        self.slewrate       = slewrate
        self.duty_min       = duty_min
        self.duty_max       = duty_max
        self.integral_limit = integral_limit

        # Internal state
        self.integral    = 0.0
        self.last_error  = 0.0
        self.last_output = duty_min

    def reset(self) -> None:
        """
        Reset controller state (integral, last error, last output).

        Call this when:
        - you change modes (e.g. from stopped to moving),
        - you change gains significantly,
        - or after a fault / emergency stop.
        """
        self.integral    = 0.0
        self.last_error  = 0.0
        self.last_output = self.duty_min

    def compute(self, target: float, current: float, dt: float) -> int:
        """
        Compute new duty for given error over dt seconds.

        :param target:  Desired value (e.g. target RPM).
        :param current: Measured value (e.g. current RPM).
        :param dt:      Time step in seconds (> 0).
        :return:        New duty (int) in [duty_min, duty_max].
        """
        error = target - current

        # Integrator
        self.integral += error * dt
        if self.integral_limit is not None:
            if self.integral > self.integral_limit:
                self.integral = self.integral_limit
            elif self.integral < -self.integral_limit:
                self.integral = -self.integral_limit

        # Derivative
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
