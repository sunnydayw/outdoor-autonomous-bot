# main.py
from machine import Pin, I2C
from time import ticks_ms, ticks_diff, ticks_add, sleep_ms

from driver  import TB6612Driver
from pid     import PIDController
from motor   import Motor
from encoder import Encoder
from differential_drivetrain import DiffDriveController
from robot_telemetry import RobotTelemetry
from MPU6050 import MPU6050
import config

# ===================== knobs =====================
DEBUG_PRINT            = False   # console diagnostics on/off
TELEMETRY_DEBUG_FRAME  = False   # True = big debug frame, False = compact frame
USE_UART_CMD           = True    # True = listen to host's cmd_vel; False = local test command
LOCAL_V_CMD            = 0.50    # m/s (used only if USE_UART_CMD=False)
LOCAL_W_CMD            = 0.00    # rad/s (used only if USE_UART_CMD=False)

# Rates
CTRL_PERIOD_MS   = 50    # ~20 Hz control loop
STATUS_PERIOD_MS = 200   # 5 Hz console status (only if DEBUG_PRINT)
LED_PERIOD_MS    = 500   # 2 Hz blink
TELEMETRY_MS     = 50    # 20 Hz telemetry
CMD_KEEPALIVE_MS = 100   # refresh local cmd_vel (only if USE_UART_CMD=False)

# ================= hardware bring-up =================
# Safety: keep the H-bridge disabled until we’re ready
stby = Pin(config.MOTOR_STBY_PIN, Pin.OUT, value=0)

# Heartbeat LED (tries on-board alias, else config.LED_PIN)
LED = None
try:
    LED = Pin("LED", Pin.OUT)   # RP2040 boards
except Exception:
    if hasattr(config, "LED_PIN"):
        LED = Pin(config.LED_PIN, Pin.OUT)
if LED:
    LED.value(0)  # start OFF

# TB6612 driver
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

# PID controllers (tune with your FF)
pid_left  = PIDController(config.PID["Kp"], config.PID["Ki"], config.PID["Kd"],
                          Kff=config.Kff, offset=config.offset,
                          slewrate=config.SLEW_MAX_DELTA,
                          duty_min=config.MIN_DUTY, duty_max=config.MAX_DUTY)
pid_right = PIDController(config.PID["Kp"], config.PID["Ki"], config.PID["Kd"],
                          Kff=config.Kff, offset=config.offset,
                          slewrate=config.SLEW_MAX_DELTA,
                          duty_min=config.MIN_DUTY, duty_max=config.MAX_DUTY)

# Motors (small gate so 100 Hz loop always runs PID)
motor_left  = Motor(driver, 'A', enc_left,  pid_left,  invert=False, min_loop_ms=5)
motor_right = Motor(driver, 'B', enc_right, pid_right, invert=False, min_loop_ms=5)

# Diff-drive controller
dd = DiffDriveController(motor_left, motor_right)

# I2C & IMU (adjust pins if you wired differently)
# If you already keep I2C pins in config, swap Pin(5)/Pin(4) for those.
imu = None


try:
    i2c = I2C(config.I2C_ID, scl=Pin(config.I2C_SCL_PIN), sda=Pin(config.I2C_SDA_PIN), freq=config.I2C_FREQ)
    imu = MPU6050(i2c)
    imu.wake()
except Exception as _e:
    imu = None  # run fine without IMU

# Telemetry (uses config.BATTERY_ADC_PIN for battery via divider)
tele = RobotTelemetry(motor_left, motor_right, dd,
                      uart_id=config.UART_ID, baud=config.UART_BAUDRATE, tx_pin=config.UART_TX_PIN, rx_pin=config.UART_RX_PIN,
                      battery_adc_pin=getattr(config, "BATTERY_ADC_PIN", None),
                      imu=imu,
                      debug=TELEMETRY_DEBUG_FRAME)

# ================= helpers =================
def print_status(now_ms):
    ddr = dd.get_diagnostics()
    spL = ddr["target_rpm"]["left"]; spR = ddr["target_rpm"]["right"]
    measL = motor_left.encoder.update_rpm()
    measR = motor_right.encoder.update_rpm()
    errL_live = spL - measL; errR_live = spR - measR
    L = motor_left.get_diagnostics(); R = motor_right.get_diagnostics()
    MIN_DUTY = config.MIN_DUTY; MAX_DUTY = config.MAX_DUTY
    last_out_L = float(L["last_output"]); last_out_R = float(R["last_output"])
    satL = (last_out_L <= MIN_DUTY + 1) or (last_out_L >= MAX_DUTY - 1)
    satR = (last_out_R <= MIN_DUTY + 1) or (last_out_R >= MAX_DUTY - 1)
    print(
        "t={:>7} | v={:.2f} w={:.2f} | spRPM L:{:.2f} R:{:.2f} | rpm L:{:.2f} R:{:.2f} | "
        "err L:{:.2f} R:{:.2f} | duty L:{:.0f} R:{:.0f} | sat L:{} R:{} | loop={}us timeout={}".format(
            now_ms,
            ddr["cmd"]["linear_mps"], ddr["cmd"]["angular_rps"],
            spL, spR, measL, measR, errL_live, errR_live,
            last_out_L, last_out_R, satL, satR,
            ddr["loop_time_us"], ddr["timeout"]
        )
    )

# ================= main loop =================
try:
    stby.value(1)  # enable H-bridge when ready

    # seed local command if we're not using UART control
    if not USE_UART_CMD:
        dd.update_cmd_vel(LOCAL_V_CMD, LOCAL_W_CMD)

    next_ctrl   = ticks_add(ticks_ms(), CTRL_PERIOD_MS)
    next_stat   = ticks_ms()
    next_led    = ticks_add(ticks_ms(), LED_PERIOD_MS)
    next_tele   = ticks_add(ticks_ms(), TELEMETRY_MS)
    next_cmd    = ticks_add(ticks_ms(), CMD_KEEPALIVE_MS)
    led_state   = 0

    if DEBUG_PRINT:
        print("Running… CTRL={}ms STATUS={}ms TELE={}ms UART@115200".format(
            CTRL_PERIOD_MS, STATUS_PERIOD_MS, TELEMETRY_MS))

    while True:
        # 1) Control
        dd.update_motors()

        # 2) UART cmd_vel (host -> Pico)
        tele.poll_cmd()  # parses frames starting with 0xCC33

        # 3) Keep-alive if we're driving locally instead of UART
        now = ticks_ms()
        if not USE_UART_CMD and ticks_diff(now, next_cmd) >= 0:
            dd.update_cmd_vel(LOCAL_V_CMD, LOCAL_W_CMD)
            next_cmd = ticks_add(next_cmd, CMD_KEEPALIVE_MS)

        # 4) Telemetry (Pico -> host)
        if ticks_diff(now, next_tele) >= 0:
            tele.send()  # compact or debug frame (switch via TELEMETRY_DEBUG_FRAME)
            next_tele = ticks_add(next_tele, TELEMETRY_MS)

        # 5) Heartbeat LED
        if LED and ticks_diff(now, next_led) >= 0:
            led_state ^= 1
            LED.value(led_state)
            next_led = ticks_add(next_led, LED_PERIOD_MS)

        # 6) Optional console diagnostics
        if DEBUG_PRINT and ticks_diff(now, next_stat) >= 0:
            next_stat = ticks_add(next_stat, STATUS_PERIOD_MS)
            print_status(now)
            # in your main loop, every 1000 ms:
            ddr = dd.get_diagnostics()
            print("Pico cmd:", ddr["cmd"])  # shows linear_mps, angular_rps

        # 7) Pacing (wraparound-safe)
        rem = ticks_diff(next_ctrl, now)
        if rem > 0:
            sleep_ms(rem)
        else:
            next_ctrl = now
        next_ctrl = ticks_add(next_ctrl, CTRL_PERIOD_MS)

except KeyboardInterrupt:
    pass
finally:
    dd.stop_motors()
    stby.value(0)
    if LED:
        LED.value(0)
    print("Stopped safely.")

