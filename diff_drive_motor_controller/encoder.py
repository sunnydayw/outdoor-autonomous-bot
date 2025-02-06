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
        
        # Variables for RPM calculation.
        self.ticks_per_rev = ticks_per_rev
        self.last_time = time.ticks_ms()
        self.last_count = 0
        self.rpm = 0  # Store latest RPM

    @property
    def read_ticks(self):
        """Return the current encoder tick count atomically."""
        return self.encoder_count
    
    def _callback(self, pin):
        """Interrupt callback to count encoder ticks."""
        self.encoder_count += 1

    def reset(self):
        """Reset encoder count and timing variables."""
        self.encoder_count = 0
        self.last_time = time.ticks_ms()
        self.last_count = 0
        self.rpm = 0 

    def update_rpm(self):
        """
        Calculate and return the RPM based on the tick difference and elapsed time.
        After computing, update the internal last_count and last_time for the next measurement.
        
        :return: Calculated RPM.
        """
        current_time = time.ticks_ms()
        dt_ms = time.ticks_diff(current_time, self.last_time)

        if dt_ms <= 5:
            return self.rpm  # Avoid division by zero
        
        dt_sec = dt_ms / 1000.0
        ticks = self.encoder_count - self.last_count
        
        # Update internal tracking variables
        self.last_count = self.encoder_count
        self.last_time = current_time
        
        # Ensure RPM is output as integer
        self.rpm = int((ticks * 60.0) / (self.ticks_per_rev * dt_sec))

        return self.rpm
