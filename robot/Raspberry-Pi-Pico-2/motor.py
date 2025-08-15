# motor.py
import time
from driver import TB6612Driver
from pid import PIDController

class Motor:
    """
    High‐level motor that uses one channel (A or B) of a TB6612Driver.
    """
    def __init__(
        self,
        driver: TB6612Driver,
        channel: str,               # 'A' or 'B'
        encoder,
        controller: PIDController,
        invert: bool = False,
        min_loop_ms: int = 10
    ):
        self.driver     = driver
        self.channel    = channel.upper()
        self.encoder    = encoder
        self.controller = controller
        self.invert     = invert

        self._target_rpm = 0.0
        self._last_time  = time.ticks_ms()
        self._min_loop   = min_loop_ms

    @property
    def target_rpm(self) -> float:
        return self._target_rpm

    @target_rpm.setter
    def target_rpm(self, rpm: float):
        # immediately set direction on the right channel
        self.driver.apply_direction(self.channel, rpm, invert=self.invert)
        self._target_rpm = abs(rpm)
        if rpm == 0:
            self.driver.set_duty(self.channel, 0)  # ensure PWM=0 immediately
            
    def step(self):
        """
        One control‐loop iteration: read encoder, compute PID, write PWM.
        """
        now   = time.ticks_ms()
        dt_ms = time.ticks_diff(now, self._last_time)
        if dt_ms < self._min_loop or self._target_rpm == 0:
            return
        dt = dt_ms / 1000.0

        # measure
        current = self.encoder.update_rpm()
        # compute new duty
        duty    = self.controller.compute(self._target_rpm, current, dt)
        # apply
        self.driver.set_duty(self.channel, duty)

        self._last_time = now

    def drive_distance(self, distance_m: float, rpm: float, timeout_s: float = None):
        pulses = int(distance_m / self.encoder.distance_per_pulse)
        self.encoder.reset()
        self.target_rpm = rpm

        start = time.time()
        while abs(self.encoder.ticks) < pulses:
            self.step()
            if timeout_s and (time.time() - start) >= timeout_s:
                break
            time.sleep_ms(10)

        self.driver.brake(self.channel)

    def brake(self):
        self.driver.brake(self.channel)

    def get_diagnostics(self) -> dict:
        return {
            "channel":      self.channel,
            "target_rpm":   self._target_rpm,
            "current_rpm":  self.encoder.update_rpm(),
            "last_error":   self.controller.last_error,
            "integral":     self.controller.integral,
            "last_output":  self.controller.last_output
        }
