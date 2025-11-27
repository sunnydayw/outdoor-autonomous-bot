# encoder.py

import time
from machine import Pin
import config


class Encoder:
    """
    Quadrature encoder reader with smoothed RPM estimation.

    - Uses IRQ on channel A and reads channel B to determine direction.
    - Maintains a sliding time window of recent tick deltas to compute RPM.
    - Exposes basic diagnostics for system health / status flags.
    """

    # Minimum time between RPM updates, in milliseconds.
    _MIN_UPDATE_MS = 5

    # Maximum number of samples kept in the sliding window (safety bound).
    _MAX_SAMPLES = 64

    def __init__(self,
                 pin_a_num,
                 pin_b_num,
                 pull=Pin.PULL_UP,
                 ticks_per_rev=config.TICKS_PER_REV,
                 window_ms=config.WINDOW_MS):
        """
        :param pin_a_num: GPIO number for encoder channel A.
        :param pin_b_num: GPIO number for encoder channel B.
        :param pull:      Pin pull configuration (default: Pin.PULL_UP).
        :param ticks_per_rev: Encoder ticks per output shaft revolution.
        :param window_ms: Time window (ms) used to smooth RPM.
        """
        # --- Raw tick count (signed) ---
        self._count = 0

        # --- GPIO setup ---
        self._pin_a = Pin(pin_a_num, Pin.IN, pull)
        self._pin_b = Pin(pin_b_num, Pin.IN, pull)

        # Attach IRQ on A channel edges. B is sampled in the handler.
        self._pin_a.irq(trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING,
                        handler=self._on_edge)

        # --- Configuration ---
        self._ticks_per_rev = ticks_per_rev
        self._window_ms     = window_ms

        # --- State for RPM calculation ---
        # Each sample: (timestamp_ms, delta_ticks, dt_ms)
        self._samples    = []
        self._last_time  = time.ticks_ms()
        self._last_count = 0
        self._rpm        = 0.0

        # --- Diagnostics state ---
        self._exec_time_us     = 0         # Duration of last update_rpm() call
        self._last_update_ms   = self._last_time
        self._last_edge_ms     = None      # Time of last encoder edge
        self._last_delta_ticks = 0         # Last tick delta between updates
        self._no_pulses_window = False     # True if no ticks in current window

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def ticks(self):
        """Total encoder ticks since last reset (signed)."""
        return self._count

    @property
    def rpm(self):
        """Latest smoothed RPM (absolute value, rounded)."""
        return round(abs(self._rpm), 2)

    @property
    def signed_rpm(self):
        """Latest smoothed RPM with sign preserved (rounded)."""
        return round(self._rpm, 2)

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    def reset(self):
        """
        Zero tick count and clear RPM history.

        Note:
        - Does NOT change GPIO or IRQ configuration.
        - Also resets diagnostics that depend on history.
        """
        self._count      = 0
        self._samples.clear()
        now              = time.ticks_ms()
        self._last_time  = now
        self._last_count = 0
        self._rpm        = 0.0

        # Diagnostics reset
        self._exec_time_us     = 0
        self._last_update_ms   = now
        self._last_edge_ms     = None
        self._last_delta_ticks = 0
        self._no_pulses_window = False

    def update_rpm(self):
        """
        Recompute RPM based on encoder activity within the last `window_ms`.

        Should be called from the main loop at a reasonable rate
        (e.g. 10–100 Hz). Returns the current smoothed RPM (absolute).

        :return: float, |RPM| rounded to 2 decimal places.
        """
        start_us = time.ticks_us()

        now_ms = time.ticks_ms()
        dt_ms  = time.ticks_diff(now_ms, self._last_time)

        # If called too frequently, keep the last RPM value.
        if dt_ms < self._MIN_UPDATE_MS:
            self._exec_time_us = time.ticks_diff(time.ticks_us(), start_us)
            return self.rpm

        # Compute tick delta since last update.
        # NOTE: _count is updated in IRQ context; reading it here is generally
        # acceptable for this application, but can be wrapped in a small
        # critical section if absolute atomicity is required.
        curr_count = self._count
        delta      = curr_count - self._last_count

        # Record sample.
        self._samples.append((now_ms, delta, dt_ms))
        self._last_count       = curr_count
        self._last_time        = now_ms

        # Bound the number of samples for safety (avoid unbounded growth).
        if len(self._samples) > self._MAX_SAMPLES:
            self._samples.pop(0)

        # Drop samples outside the sliding time window.
        while self._samples and \
              time.ticks_diff(now_ms, self._samples[0][0]) > self._window_ms:
            self._samples.pop(0)

        # Aggregate ticks and time over the current window.
        total_ticks   = sum(s[1] for s in self._samples)
        total_time_ms = sum(s[2] for s in self._samples)

        if total_time_ms > 0:
            # ticks → revolutions → minutes
            revs = total_ticks / self._ticks_per_rev
            mins = (total_time_ms / 1000.0) / 60.0
            # Guard against division by zero (paranoia)
            self._rpm = revs / mins if mins > 0 else 0.0
        else:
            # Not enough time elapsed: treat as no motion for this window.
            self._rpm = 0.0

        # Diagnostics: did we see any pulses in this window?
        self._no_pulses_window = (total_ticks == 0)
        self._last_update_ms   = now_ms
        self._last_delta_ticks = delta
        
        # Record execution time for diagnostics.
        self._exec_time_us = time.ticks_diff(time.ticks_us(), start_us)

        return self.rpm

    def get_diagnostics(self):
        """
        Return a diagnostics snapshot for this encoder.

        This is intended to feed a higher-level SystemStatus / health monitor.

        Fields:
            ticks:             Current tick count.
            rpm:               Latest signed RPM (float).
            samples_in_window: Number of samples used for RPM smoothing.
            window_ms:         Configured smoothing window.
            last_update_age_ms:Time since last successful update_rpm() call.
            last_edge_age_ms:  Time since last encoder edge (None if never).
            last_delta_ticks:  Tick delta at last update.
            no_pulses_window:  True if no ticks seen in current window.
            exec_time_us:      Duration of last update_rpm() in microseconds.
            stale_rpm:         True if last_update_age_ms is much larger than
                               the smoothing window (update_rpm not called
                               often enough or loop stalled).
        """
        now_ms = time.ticks_ms()

        last_update_age_ms = time.ticks_diff(now_ms, self._last_update_ms)

        if self._last_edge_ms is not None:
            last_edge_age_ms = time.ticks_diff(now_ms, self._last_edge_ms)
        else:
            last_edge_age_ms = None

        # Consider RPM "stale" if we haven't updated in ~3 windows.
        stale_rpm = last_update_age_ms > (3 * self._window_ms)

        return {
            "ticks":              self._count,
            "rpm":                self.signed_rpm,
            "samples_in_window":  len(self._samples),
            "window_ms":          self._window_ms,
            "last_update_age_ms": last_update_age_ms,
            "last_edge_age_ms":   last_edge_age_ms,
            "last_delta_ticks":   self._last_delta_ticks,
            "no_pulses_window":   self._no_pulses_window,
            "exec_time_us":       self._exec_time_us,
            "stale_rpm":          stale_rpm,
        }

    # ------------------------------------------------------------------
    # IRQ handler
    # ------------------------------------------------------------------

    def _on_edge(self, pin):
        """
        IRQ callback on every edge of channel A.

        We sample both A and B to determine direction:

            A == B  → forward  (increment count)
            A != B  → backward (decrement count)

        This is a standard quadrature decoding rule when using A as the
        primary interrupt source.
        """
        a = self._pin_a.value()
        b = self._pin_b.value()

        if a == b:
            self._count += 1  # Forward
        else:
            self._count -= 1  # Backward

        # Record time of last edge for diagnostics.
        self._last_edge_ms = time.ticks_ms()
