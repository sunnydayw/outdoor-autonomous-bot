# encoder.py

import time
from machine import Pin
import config

class Encoder:
    def __init__(self,
                 pin_a_num,
                 pin_b_num,
                 pull=Pin.PULL_UP,
                 ticks_per_rev=config.TICKS_PER_REV,
                 window_ms=config.WINDOW_MS):
        """
        Quadrature decoder on two GPIOs.
        :param pin_a_num: GPIO for channel A.
        :param pin_b_num: GPIO for channel B.
        :param ticks_per_rev: encoder ticks per output shaft revolution.
        :param window_ms: smoothing window for RPM calc.
        """
        # raw count
        self._count = 0

        # pins
        self._pin_a = Pin(pin_a_num, Pin.IN, pull)
        self._pin_b = Pin(pin_b_num, Pin.IN, pull)

        # attach IRQ on A and B channel edges
        self._pin_a.irq(trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING,
                        handler=self._on_edge)
        
        # config
        self._ticks_per_rev = ticks_per_rev
        self._window_ms     = window_ms

        # for RPM calculation
        self._samples    = []  # list of (ts_ms, delta_ticks, dt_ms)
        self._last_time  = time.ticks_ms()
        self._last_count = 0
        self._rpm        = 0.0
        self._exec_time  = 0

    @property
    def ticks(self):
        """Total encoder ticks since last reset."""
        return self._count

    @property
    def rpm(self):
        """Most recent RPM, smoothed over the window."""
        return round(abs(self._rpm), 2)

    @property
    def signed_rpm(self):
        """Return the signed RPM (useful for computing linear velocity)."""
        return round(self._rpm, 2)

    def reset(self):
        """Zero count and RPM history."""
        self._count      = 0
        self._last_time  = time.ticks_ms()
        self._last_count = 0
        self._rpm        = 0.0
        self._samples.clear()

    def _on_edge(self, pin):
        """
        Called on every edge of channel A.
        Use the state of B to determine direction.
        """
        a = self._pin_a.value()
        b = self._pin_b.value()
        # if A==B → forward; else → backward
        if a == b:
            self._count += 1  # “forward”
        else:
            self._count -= 1

    def update_rpm(self):
        """
        Recompute RPM based on ticks in the last `window_ms`.
        Returns the smoothed RPM.
        """
        start_us = time.ticks_us()
        now_ms   = time.ticks_ms()
        dt_ms    = time.ticks_diff(now_ms, self._last_time)

        # too-frequent calls keep last value
        if dt_ms < 5:
            return self.rpm

        # how many ticks since last sample
        delta = self._count - self._last_count

        # record new sample
        self._samples.append((now_ms, delta, dt_ms))
        self._last_count = self._count
        self._last_time  = now_ms

        # Remove samples that are older than the sliding window
        while self._samples and \
              time.ticks_diff(now_ms, self._samples[0][0]) > self._window_ms:
            self._samples.pop(0)

        # sum over window
        total_ticks   = sum(s[1] for s in self._samples)
        total_time_ms = sum(s[2] for s in self._samples)

        if total_time_ms > 0:
            # ticks → revolutions → minutes
            revs    = total_ticks / self._ticks_per_rev
            mins    = total_time_ms / 1000.0 / 60.0
            self._rpm = revs / mins

        # record execution time for diagnostics
        self._exec_time = time.ticks_diff(time.ticks_us(), start_us)
        return self.rpm

    def get_diagnostics(self):
        """Return how long update_rpm() takes, in µs."""
        return self._exec_time
