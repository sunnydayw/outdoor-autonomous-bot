from machine import Pin
import time

class Encoder:
    """Encoder class to handle speed and distance calculations."""
    
    TICKS_PER_REV = 45
    WHEEL_DIAMETER_M = 0.254  # 10 inches in meters
    WHEEL_CIRCUMFERENCE_M = 3.14159 * WHEEL_DIAMETER_M  # ~0.798 m
    DIST_PER_TICK = WHEEL_CIRCUMFERENCE_M / TICKS_PER_REV  # ~0.0177 m

    def __init__(self, pin_number):
        """Initialize an encoder with a specific pin."""
        self.pin = Pin(pin_number, Pin.IN, Pin.PULL_UP)
        self.count = 0
        self.speed_m_s = 0.0
        self.distance_m = 0.0
        self.prev_count = 0
        self.prev_time = time.ticks_ms()

        # Attach interrupt
        self.pin.irq(trigger=Pin.IRQ_RISING, handler=self._count_cb)

    def _count_cb(self, pin):
        """Interrupt routine for counting encoder ticks."""
        self.count += 1

    def poll(self):
        """Calculate speed and update distance, should be called periodically."""
        now = time.ticks_ms()
        dt_ms = time.ticks_diff(now, self.prev_time)

        if dt_ms >= 100:  # Every 100 ms (10 Hz)
            dt_s = dt_ms / 1000.0
            delta_count = self.count - self.prev_count

            # Calculate speed (m/s) and distance
            self.speed_m_s = (delta_count * self.DIST_PER_TICK) / dt_s
            self.distance_m = self.count * self.DIST_PER_TICK

            # Update for next iteration
            self.prev_count = self.count
            self.prev_time = now

    def reset(self):
        """Reset encoder count and distance."""
        self.count = 0
        self.distance_m = 0.0

    def get_count(self):
        return self.count

    def get_speed(self):
        return self.speed_m_s

    def get_distance(self):
        return self.distance_m


# ----------------------------------------------------------------
# Global references to encoders
# ----------------------------------------------------------------
left_encoder = None
right_encoder = None

def init_encoders(left_pin=20, right_pin=21):
    """Initialize left and right encoders."""
    global left_encoder, right_encoder

    left_encoder = Encoder(left_pin)
    right_encoder = Encoder(right_pin)
    print("[ENCODER] Encoders initialized on pins:", left_pin, "and", right_pin)

def poll_encoders():
    """Poll both encoders to update speed and distance."""
    if left_encoder is not None and right_encoder is not None:
        left_encoder.poll()
        right_encoder.poll()

def reset_encoders():
    """Reset both encoders."""
    if left_encoder is not None and right_encoder is not None:
        left_encoder.reset()
        right_encoder.reset()
        print("[ENCODER] Both encoders have been reset!")
