"""
encoder.py
----------
Encoder module for reading motor encoder ticks and computing RPM.
"""

from machine import Pin
import time

class Encoder:
    def __init__(self, pin_num, pull=Pin.PULL_UP, ticks_per_rev=90):
        """
        Initialize the encoder.
        
        :param pin_num: GPIO pin number for the encoder signal.
        :param pull: Pull configuration (default: Pin.PULL_UP).
        :param ticks_per_rev: Number of encoder ticks per wheel revolution.
        """
        self.encoder_count = 0
        self.pin = Pin(pin_num, Pin.IN, pull)
        self.pin.irq(trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING, handler=self._callback)
        self.ticks_per_rev = ticks_per_rev
        
        # Variables for RPM calculation.
        self.last_time = time.ticks_ms()
        self.last_count = 0

    def _callback(self, pin):
        """Interrupt callback to count encoder ticks."""
        self.encoder_count += 1

    def reset(self):
        """Reset encoder count and timing variables."""
        self.encoder_count = 0
        self.last_time = time.ticks_ms()
        self.last_count = 0

    def read(self):
        """
        Return the current encoder tick count.
        
        :return: Encoder tick count.
        """
        return self.encoder_count

    def get_rpm(self):
        """
        Calculate and return the RPM based on the tick difference and elapsed time.
        After computing, update the internal last_count and last_time for the next measurement.
        
        :return: Calculated RPM.
        """
        current_time = time.ticks_ms()
        dt_ms = time.ticks_diff(current_time, self.last_time)
        if dt_ms <= 0:
            return 0.0  # Avoid division by zero.
        dt_sec = dt_ms / 1000.0
        current_count = self.encoder_count
        ticks = current_count - self.last_count
        
        # Update measurement variables.
        self.last_count = current_count
        self.last_time = current_time
        
        # Compute revolutions per second and convert to RPM.
        rps = (ticks / self.ticks_per_rev) / dt_sec
        rpm = rps * 60.0
        return rpm
