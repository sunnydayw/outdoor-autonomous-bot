from machine import Pin
from time import ticks_ms, ticks_diff, ticks_add, sleep_ms

from driver  import TB6612Driver
from pid     import PIDController
from motor   import Motor
from encoder import Encoder
import config
from differential_drivetrain import DiffDriveController

# --- Safety: keep the H-bridge disabled until we’re ready
stby = Pin(config.MOTOR_STBY_PIN, Pin.OUT, value=0)

# --- Heartbeat LED (tries on-board alias, else config.LED_PIN)
LED = None
try:
    LED = Pin("LED", Pin.OUT)   # e.g. RP2040
except Exception:
    if hasattr(config, "LED_PIN"):
        LED = Pin(config.LED_PIN, Pin.OUT)
if LED:
    LED.value(0)  # start OFF

# Build TB6612 driver
driver = TB6612Driver(
    in1_a       = config.MOTOR1_IN1_PIN,
    in2_a       = config.MOTOR1_IN2_PIN,
    pwm_a       = config.MOTOR1_PWM_PIN,
    in1_b       = config.MOTOR2_IN1_PIN,
    in2_b       = config.MOTOR2_IN2_PIN,
    pwm_b       = config.MOTOR2_PWM_PIN,
    standby_pin = config.MOTOR_STBY_PIN,   # pass pin number, not Pin()
    freq        = config.PWM_FREQ
)

# Encoders
enc_left  = Encoder(config.ENC_1A_PIN, config.ENC_1B_PIN)
enc_right = Encoder(config.ENC_2A_PIN, config.ENC_2B_PIN)

# PID controllers
pid_left  = PIDController(config.PID["Kp"], config.PID["Ki"], config.PID["Kd"],
                          Kff=config.Kff, offset=config.offset,
                          slewrate=config.SLEW_MAX_DELTA,
                          duty_min=config.MIN_DUTY, duty_max=config.MAX_DUTY)
pid_right = PIDController(config.PID["Kp"], config.PID["Ki"], config.PID["Kd"],
                          Kff=config.Kff, offset=config.offset,
                          slewrate=config.SLEW_MAX_DELTA,
                          duty_min=config.MIN_DUTY, duty_max=config.MAX_DUTY)

# Motors (lower min_loop_ms a bit so 100 Hz loop always clears the gate)
motor_left  = Motor(driver, 'A', enc_left,  pid_left,  invert=False, min_loop_ms=5)
motor_right = Motor(driver, 'B', enc_right, pid_right, invert=False, min_loop_ms=5)

dd = DiffDriveController(motor_left, motor_right)

# --- Rates
CTRL_PERIOD_MS   = 100     # ~10 Hz control loop 
STATUS_PERIOD_MS = 200    # 5 Hz console status
LED_PERIOD_MS    = 500    # 2 Hz blink

# --- Pretty status print (stronger diagnostics)
def print_status(now_ms):
    ddr = dd.get_diagnostics()            # controller diag (target_rpm, timeout, loop_time_us, cmd)
    spL = ddr["target_rpm"]["left"]
    spR = ddr["target_rpm"]["right"]

    # Measured RPM: use encoder directly (note: your Encoder.rpm is ABS & rounded to 2 decimals)
    measL = motor_left.encoder.update_rpm()
    measR = motor_right.encoder.update_rpm()

    # Live error (don’t rely on controller.last_error)
    errL_live = spL - measL
    errR_live = spR - measR

    L = motor_left.get_diagnostics()      # has last_output, last_error (may be stale), etc.
    R = motor_right.get_diagnostics()

    # Saturation & slew flags inferred without touching PID code
    MIN_DUTY = config.MIN_DUTY
    MAX_DUTY = config.MAX_DUTY
    last_out_L = float(L["last_output"])
    last_out_R = float(R["last_output"])

    satL = (last_out_L <= MIN_DUTY + 1) or (last_out_L >= MAX_DUTY - 1)
    satR = (last_out_R <= MIN_DUTY + 1) or (last_out_R >= MAX_DUTY - 1)

    # If last_error is stuck but err_live changes, your PID.compute() isn’t being hit each loop.
    # If duty_fp hardly changes but err_live changes, you’re clamped (slew or min/max).
    print(
        "t={:>7} | v={:.2f} w={:.2f} | spRPM L:{:.2f} R:{:.2f} | rpm L:{:.2f} R:{:.2f} | "
        "err_live L:{:.2f} R:{:.2f} | duty_fp L:{:.1f} R:{:.1f} | sat L:{} R:{} | "
        "pid_err(stored) L:{:.2f} R:{:.2f} | loop={}us timeout={}".format(
            now_ms,
            ddr["cmd"]["linear_mps"], ddr["cmd"]["angular_rps"],
            spL, spR,
            measL, measR,
            errL_live, errR_live,
            last_out_L, last_out_R,
            satL, satR,
            L["last_error"], R["last_error"],
            ddr["loop_time_us"], ddr["timeout"]
        )
    )

# --- Main
try:
    stby.value(1)  # Enable H-bridge only when ready

    next_tick    = ticks_add(ticks_ms(), CTRL_PERIOD_MS)
    last_status  = ticks_ms()
    next_led     = ticks_add(ticks_ms(), LED_PERIOD_MS)
    led_state    = 0

    # Optional: print a header once
    print("Running… CTRL={}ms STATUS={}ms".format(CTRL_PERIOD_MS, STATUS_PERIOD_MS))

    while True:
        dd.update_cmd_vel(0.5, 0.0)
        dd.update_motors()

        now = ticks_ms()

        # Heartbeat LED (non-blocking)
        if LED and ticks_diff(now, next_led) >= 0:
            led_state ^= 1
            LED.value(led_state)
            next_led = ticks_add(next_led, LED_PERIOD_MS)

        # Periodic diagnostics
        if ticks_diff(now, last_status) >= STATUS_PERIOD_MS:
            last_status = now
            print_status(now)

        # Fixed-rate scheduling (wraparound-safe)
        rem = ticks_diff(next_tick, now)
        if rem > 0:
            sleep_ms(rem)
        else:
            next_tick = now
        next_tick = ticks_add(next_tick, CTRL_PERIOD_MS)

except KeyboardInterrupt:
    pass
finally:
    dd.stop_motors()   # matches DiffDriveController API
    stby.value(0)
    if LED:
        LED.value(0)
    print("Stopped safely.")

