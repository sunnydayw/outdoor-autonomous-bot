# test_encoder.py
from machine import Pin
import time

class Encoder:
    def __init__(self, pin_num, pull=Pin.PULL_UP, ticks_per_rev=90):
        self.encoder_count = 0
        self.pin = Pin(pin_num, Pin.IN, pull)
        self.pin.irq(trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING, handler=self._callback)
        self.ticks_per_rev = ticks_per_rev
        
        # Variables for RPM calculation.
        self.last_time = time.ticks_ms()
        self.last_count = 0

    def _callback(self, pin):
        self.encoder_count += 1

    def reset(self):
        self.encoder_count = 0
        self.last_time = time.ticks_ms()
        self.last_count = 0
        
    def read(self):
        return self.encoder_count

    def get_rpm(self):
        """
        Calculate and return the RPM based on the ticks counted since the last call.
        This method computes the difference in encoder counts and elapsed time,
        then calculates RPM. After computing, it updates the internal last_count
        and last_time for the next measurement.
        """
        current_time = time.ticks_ms()
        dt_ms = time.ticks_diff(current_time, self.last_time)
        if dt_ms <= 0:
            return 0.0  # Avoid division by zero or negative intervals
        dt_sec = dt_ms / 1000.0
        current_count = self.encoder_count
        ticks = current_count - self.last_count
        
        # Update for the next measurement cycle.
        self.last_count = current_count
        self.last_time = current_time
        
        # Calculate revolutions per second and convert to RPM.
        rps = (ticks / self.ticks_per_rev) / dt_sec
        rpm = rps * 60.0
        return rpm