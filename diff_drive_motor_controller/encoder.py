from machine import Pin
import time
from collections import deque

class Encoder:
    def __init__(self, pin_num, pull=Pin.PULL_UP, ticks_per_rev=90, window_ms=500):
        """
        Initialize the encoder.
        :param pin_num: GPIO pin number for the encoder signal.
        :param pull: Pull configuration (default: Pin.PULL_UP).
        :param ticks_per_rev: Number of encoder ticks per wheel revolution.
        """
        self._encoder_count = 0  # Use underscore for private variables
        self._pin = Pin(pin_num, Pin.IN, pull)
        self._pin.irq(trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING, handler=self._callback)
        
        # Configuration
        self._ticks_per_rev = ticks_per_rev
        
        # Sliding window settings (time in ms)
        self._window_ms = window_ms
        # Use a list to store samples: each sample is (timestamp, tick_delta, dt_ms)
        self._samples = []

        # Timing variables
        self._last_time = time.ticks_ms()
        self._last_count = 0
        self._rpm = 0.0
        
    @property
    def ticks(self):
        """Return the current encoder tick count atomically."""
        return self._encoder_count
    
    @property
    def rpm(self):
        """Return the last calculated RPM value."""
        return round(abs(self._rpm), 2)

    def _callback(self, pin):
        """Interrupt callback to count encoder ticks."""
        self._encoder_count += 1

    def reset(self):
        """Reset encoder count and timing variables."""
        self._encoder_count = 0
        self._last_time = time.ticks_ms()
        self._last_count = 0
        self._rpm = 0.0

    def update_rpm(self):
        """
        Calculate and return the RPM based on the tick difference and elapsed time.
        Returns the last known RPM if called too frequently.
        """
        current_time = time.ticks_ms()
        dt_ms = time.ticks_diff(current_time, self._last_time)
        
        # Return cached value if called too frequently
        if dt_ms < 5:
            return round(abs(self._rpm), 2)
            
        # Update timing statistics
        self._min_dt = min(self._min_dt, dt_ms)
        self._max_dt = max(self._max_dt, dt_ms)
        self._last_update_time = current_time
        
        # Calculate ticks count
        ticks = self._encoder_count - self._last_count

        # Append new sample: (timestamp, tick_delta, dt_ms)
        self._samples.append((current_time, ticks, dt_ms))

        # Update tracking variables
        self._last_count = self._encoder_count
        self._last_time = current_time
        
        # Remove samples that are older than the sliding window (1 second)
        while self._samples and time.ticks_diff(current_time, self._samples[0][0]) > self._window_ms:
            self._samples.pop(0)
        
        # Sum ticks and elapsed time over the current window
        total_ticks = sum(sample[1] for sample in self._samples)
        total_time_ms = sum(sample[2] for sample in self._samples)

        # Avoid division by zero and compute rpm
        if total_time_ms > 0:
            dt_sec = total_time_ms / 1000.0
            self._rpm = (total_ticks * 60.0) / (self._ticks_per_rev * dt_sec)
        
        return round(abs(self._rpm), 2)