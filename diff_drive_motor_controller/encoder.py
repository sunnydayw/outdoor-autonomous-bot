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
        self._encoder_count = 0  # Use underscore for private variables
        self._pin = Pin(pin_num, Pin.IN, pull)
        self._pin.irq(trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING, handler=self._callback)
        
        # Configuration
        self._ticks_per_rev = ticks_per_rev
        
        # Variables for RPM calculation
        self._last_time = time.ticks_ms()
        self._last_count = 0
        self._rpm = 0
        
        # Performance monitoring
        self._min_dt = float('inf')  # Track minimum time between updates
        self._max_dt = 0             # Track maximum time between updates
        self._last_update_time = 0   # Track when RPM was last computed
        
    @property
    def ticks(self):
        """Return the current encoder tick count atomically."""
        return self._encoder_count
    
    @property
    def rpm(self):
        """Return the last calculated RPM value."""
        return self._rpm
    
    @property
    def update_stats(self):
        """Return timing statistics for debugging."""
        return {
            'min_dt_ms': self._min_dt,
            'max_dt_ms': self._max_dt,
            'time_since_update_ms': time.ticks_diff(time.ticks_ms(), self._last_update_time)
        }

    def _callback(self, pin):
        """Interrupt callback to count encoder ticks."""
        self._encoder_count += 1

    def reset(self):
        """Reset encoder count and timing variables."""
        self._encoder_count = 0
        self._last_time = time.ticks_ms()
        self._last_count = 0
        self._rpm = 0
        self._min_dt = float('inf')
        self._max_dt = 0
        self._last_update_time = 0

    def update_rpm(self):
        """
        Calculate and return the RPM based on the tick difference and elapsed time.
        Returns the last known RPM if called too frequently.
        """
        current_time = time.ticks_ms()
        dt_ms = time.ticks_diff(current_time, self._last_time)
        
        # Return cached value if called too frequently
        if dt_ms < 5:
            return self._rpm
            
        # Update timing statistics
        self._min_dt = min(self._min_dt, dt_ms)
        self._max_dt = max(self._max_dt, dt_ms)
        self._last_update_time = current_time
        
        # Calculate RPM
        dt_sec = dt_ms / 1000.0
        ticks = self._encoder_count - self._last_count
        
        # Update tracking variables
        self._last_count = self._encoder_count
        self._last_time = current_time
        
        # Calculate new RPM
        self._rpm = int((ticks * 60.0) / (self._ticks_per_rev * dt_sec))
        
        return self._rpm