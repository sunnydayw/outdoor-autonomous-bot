# motor.py
import time
from driver import TB6612Driver
from pid import PIDController


class Motor:
    """
    High-level motor controller using one TB6612 channel and a PID loop.

    Responsibilities:
        - Maintain a target wheel RPM using encoder feedback.
        - Optionally drive a fixed distance using encoder pulses.
        - Provide basic diagnostics for higher-level logic.
    """

    def __init__(
        self,
        driver: TB6612Driver,
        channel: str,               # 'A' or 'B'
        encoder,
        controller: PIDController,
        invert: bool = False,
        min_loop_ms: int = 10,
    ):
        """
        :param driver:     TB6612Driver instance controlling the H-bridge.
        :param channel:    'A' or 'B' (TB6612 channel selection).
        :param encoder:    Encoder object providing update_rpm(), ticks, etc.
        :param controller: PIDController instance (operates in duty units).
        :param invert:     If True, flips logical direction for this motor.
        :param min_loop_ms:Minimum time (ms) between control loop steps.
        """
        channel = channel.upper()
        if channel not in ("A", "B"):
            raise ValueError("channel must be 'A' or 'B' (got %r)" % channel)

        self.driver     = driver
        self.channel    = channel
        self.encoder    = encoder
        self.controller = controller
        self.invert     = invert

        self._target_rpm = 0.0
        self._last_time  = time.ticks_ms()
        self._min_loop   = min_loop_ms

    # ------------------------------------------------------------------
    # Target RPM interface
    # ------------------------------------------------------------------

    @property
    def target_rpm(self) -> float:
        """Current target RPM magnitude for this motor."""
        return self._target_rpm

    @target_rpm.setter
    def target_rpm(self, rpm: float) -> None:
        """
        Set target RPM (signed).

        - The sign of rpm determines direction.
        - The magnitude |rpm| is used as the speed setpoint.
        - When rpm == 0, the motor is commanded to stop (PWM = 0) and
          the PID controller is reset to avoid integral windup.
        """
        # Immediately set direction on the right channel.
        self.driver.apply_direction(self.channel, rpm, invert=self.invert)

        # Store magnitude as target; direction handled by H-bridge.
        self._target_rpm = abs(rpm)

        if rpm == 0.0:
            # Explicitly stop the motor and reset PID state.
            self.driver.set_duty(self.channel, 0)
            if hasattr(self.controller, "reset"):
                self.controller.reset()

    # ------------------------------------------------------------------
    # Control loop
    # ------------------------------------------------------------------

    def step(self) -> None:
        """
        One control-loop iteration: read encoder, compute PID, write PWM.

        Call this periodically from the main loop, ideally at a rate
        higher than the mechanical bandwidth (e.g. 20–100 Hz).
        """
        now   = time.ticks_ms()
        dt_ms = time.ticks_diff(now, self._last_time)

        # Rate limiting and idle case: no control action if target is zero.
        if dt_ms < self._min_loop or self._target_rpm == 0.0:
            return

        dt = dt_ms / 1000.0  # seconds

        # Measure current wheel speed (absolute RPM).
        current_rpm = self.encoder.update_rpm()

        # Compute new duty command (0..65535).
        duty = self.controller.compute(self._target_rpm, current_rpm, dt)

        # Apply duty to the selected channel.
        self.driver.set_duty(self.channel, duty)

        self._last_time = now

    # ------------------------------------------------------------------
    # Distance-based move
    # ------------------------------------------------------------------

    def drive_distance(self, distance_m: float, rpm: float, timeout_s: float = None) -> None:
        """
        Drive a given linear distance using encoder ticks.

        :param distance_m: Distance to travel in meters (absolute value used).
                           Direction is determined by the sign of `rpm`.
        :param rpm:        Signed RPM command. Sign sets direction; magnitude
                           sets speed target.
        :param timeout_s:  Optional timeout in seconds; if exceeded, the move
                           is aborted and the motor is braked.

        Requirements:
            - `encoder.distance_per_pulse` must be defined and > 0.
        """
        if not hasattr(self.encoder, "distance_per_pulse"):
            raise AttributeError("encoder must define distance_per_pulse for drive_distance().")

        if self.encoder.distance_per_pulse <= 0:
            raise ValueError("encoder.distance_per_pulse must be > 0.")

        # Number of encoder pulses corresponding to requested distance.
        pulses = int(abs(distance_m) / self.encoder.distance_per_pulse)

        # Reset encoder count and controller state.
        self.encoder.reset()
        if hasattr(self.controller, "reset"):
            self.controller.reset()

        # Set target RPM (direction from rpm sign).
        self.target_rpm = rpm

        start_ms = time.ticks_ms()

        # Blocking loop: run control until distance reached or timeout.
        while abs(self.encoder.ticks) < pulses:
            self.step()

            if timeout_s is not None:
                elapsed_ms = time.ticks_diff(time.ticks_ms(), start_ms)
                if elapsed_ms >= int(timeout_s * 1000):
                    break

            # Simple pacing to avoid a busy loop; the control rate is still
            # governed by min_loop_ms in step().
            time.sleep_ms(5)

        # Stop the motor at the end of the move.
        self.target_rpm = 0.0
        self.driver.brake(self.channel)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def brake(self) -> None:
        """
        Command this motor channel to coast/stop via the driver.
        """
        self.target_rpm = 0.0
        self.driver.brake(self.channel)

    def emergency_stop(self) -> None:
        """
        Emergency stop for this motor.

        Note:
            - This assumes TB6612Driver.emergency_stop() stops both channels
              and disables the driver for safety.
            - If you want per-motor emergency stop only, call brake().
        """
        self.target_rpm = 0.0
        if hasattr(self.driver, "emergency_stop"):
            self.driver.emergency_stop()
        else:
            # Fallback: brake just this channel.
            self.brake()

    def get_diagnostics(self) -> dict:
        """
        Return a diagnostics snapshot for this motor.

        Fields:
            channel:       TB6612 channel ('A' or 'B').
            target_rpm:    Current RPM setpoint (magnitude).
            current_rpm:   Latest measured RPM (absolute, if encoder supports it).
            last_error:    Last PID error (if available).
            integral:      Current PID integral term.
            last_output:   Last PID output (duty units).
        """
        # Prefer using encoder.rpm property if available to avoid
        # disturbing the sample window when diagnostics are polled.
        if hasattr(self.encoder, "rpm"):
            current_rpm = self.encoder.rpm
        else:
            current_rpm = self.encoder.update_rpm()

        return {
            "channel":     self.channel,
            "target_rpm":  self._target_rpm,
            "current_rpm": current_rpm,
            "last_error":  getattr(self.controller, "last_error", None),
            "integral":    getattr(self.controller, "integral", None),
            "last_output": getattr(self.controller, "last_output", None),
        }
