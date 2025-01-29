# encoder_driver.py

from machine import Pin
import time

# ----------------------------------------------------------------
# 1) Physical constants for conversion to m/s and distance
# ----------------------------------------------------------------
TICKS_PER_REV = 45
WHEEL_DIAMETER_M = 0.254  # 10 inches in meters
WHEEL_CIRCUMFERENCE_M = 3.14159 * WHEEL_DIAMETER_M  # ~0.798 m
DIST_PER_TICK = WHEEL_CIRCUMFERENCE_M / TICKS_PER_REV  # ~0.0177 m

# ----------------------------------------------------------------
# 2) Pin assignments
# ----------------------------------------------------------------
LEFT_ENC_PIN  = 20
RIGHT_ENC_PIN = 21

left_enc_pin  = Pin(LEFT_ENC_PIN,  Pin.IN, Pin.PULL_UP)
right_enc_pin = Pin(RIGHT_ENC_PIN, Pin.IN, Pin.PULL_UP)

# ----------------------------------------------------------------
# 3) Global counters & speed/distance storage
# ----------------------------------------------------------------
left_count  = 0
right_count = 0

left_speed_m_s  = 0.0
right_speed_m_s = 0.0

left_distance_m  = 0.0
right_distance_m = 0.0

# We'll track previous poll time/count for each wheel
prev_poll_time = 0
prev_left_count = 0
prev_right_count= 0

# ----------------------------------------------------------------
# 4) Interrupt callbacks
# ----------------------------------------------------------------
def _left_count_cb(pin):
    """Interrupt routine for left encoder rising edge."""
    global left_count
    left_count += 1

def _right_count_cb(pin):
    """Interrupt routine for right encoder rising edge."""
    global right_count
    right_count += 1

# ----------------------------------------------------------------
# 5) Initialization
# ----------------------------------------------------------------
def init_encoders():
    """
    Call once at startup to:
      - Reset all counters
      - Attach interrupts
      - Initialize time references
    """
    global left_count, right_count
    global left_speed_m_s, right_speed_m_s
    global left_distance_m, right_distance_m
    global prev_left_count, prev_right_count, prev_poll_time

    left_count  = 0
    right_count = 0

    left_speed_m_s  = 0.0
    right_speed_m_s = 0.0
    left_distance_m  = 0.0
    right_distance_m = 0.0

    prev_left_count  = 0
    prev_right_count = 0
    prev_poll_time   = time.ticks_ms()

    # Attach interrupts for rising edge
    left_enc_pin.irq( trigger=Pin.IRQ_RISING,  handler=_left_count_cb )
    right_enc_pin.irq(trigger=Pin.IRQ_RISING,  handler=_right_count_cb )

# ----------------------------------------------------------------
# 6) Polling function for speed/distance calculation
# ----------------------------------------------------------------
def poll_encoders():
    """
    Call periodically (e.g. ~10x per second) to:
      1) Check how many new pulses have arrived since last poll
      2) Compute speed in m/s
      3) Update total distance
    """
    global left_count, right_count
    global left_speed_m_s, right_speed_m_s
    global left_distance_m, right_distance_m
    global prev_left_count, prev_right_count, prev_poll_time

    now_ms = time.ticks_ms()
    dt_ms = time.ticks_diff(now_ms, prev_poll_time)

    # Only compute speed if enough time has elapsed
    if dt_ms >= 100:  # e.g. every 100 ms => 10 Hz
        dt_s = dt_ms / 1000.0

        # 1) Pulses since last poll
        delta_left  = left_count  - prev_left_count
        delta_right = right_count - prev_right_count

        # 2) Speed (m/s) = (pulses * dist_per_pulse) / dt
        left_speed_m_s  = (delta_left  * DIST_PER_TICK) / dt_s
        right_speed_m_s = (delta_right * DIST_PER_TICK) / dt_s

        # 3) Distance = total_counts * dist_per_pulse
        left_distance_m  = left_count  * DIST_PER_TICK
        right_distance_m = right_count * DIST_PER_TICK

        # Store for next iteration
        prev_left_count  = left_count
        prev_right_count = right_count
        prev_poll_time   = now_ms

# ----------------------------------------------------------------
# 7) Accessor functions
# ----------------------------------------------------------------
def read_encoder(motor_index):
    """Return the raw pulse count for LEFT(0) or RIGHT(1)."""
    return left_count if motor_index == 0 else right_count

def reset_encoder(motor_index):
    global left_count, right_count
    if motor_index == 0:
        left_count = 0
    else:
        right_count = 0

def reset_encoders():
    global left_count, right_count
    left_count = 0
    right_count = 0

def get_speed_m_s(motor_index):
    """Return the most recently calculated speed (m/s)."""
    return left_speed_m_s if motor_index == 0 else right_speed_m_s

def get_distance_m(motor_index):
    """Return total distance traveled in meters."""
    return left_distance_m if motor_index == 0 else right_distance_m
