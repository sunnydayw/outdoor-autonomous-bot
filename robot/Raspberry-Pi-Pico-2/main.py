# main.py
#
# Top-level control loop for the robot base on Pico.
#
# Responsibilities:
#   - Initialize hardware (drive system, UART link, optional IMU).
#   - Run the drive control loop at a fixed period.
#   - Optionally accept cmd_vel from Pi 5 via UART, or drive locally for testing.
#   - Maintain a heartbeat LED.
#   - Print diagnostics periodically for first-run troubleshooting.

from machine import Pin, I2C
from time import ticks_ms, ticks_diff, ticks_add, sleep_ms
import config

from drive_system import DriveSystem
from pico_uart_comm import PicoVelocityReceiver
from MPU6050 import MPU6050


# ===================== configuration knobs =====================

DEBUG_PRINT            = True    # Console diagnostics on/off
USE_UART_CMD           = True    # True = listen to Pi's cmd_vel; False = local test command
LOCAL_V_CMD            = 0.20    # m/s (used only if USE_UART_CMD=False)
LOCAL_W_CMD            = 0.00    # rad/s (used only if USE_UART_CMD=False)

# Periods
CTRL_PERIOD_MS   = 50     # ~20 Hz drive control loop
STATUS_PERIOD_MS = 500    # 2 Hz console diagnostics
LED_PERIOD_MS    = 500    # 2 Hz heartbeat
CMD_KEEPALIVE_MS = 200    # Refresh local cmd_vel (only if USE_UART_CMD=False)

# UART config (all from config.py)
UART_ID        = config.UART_ID
UART_BAUDRATE  = config.UART_BAUDRATE
UART_TX_PIN    = config.UART_TX_PIN
UART_RX_PIN    = config.UART_RX_PIN

# ===================== hardware setup =====================

# Heartbeat LED: try on-board "LED", else config.LED_PIN if defined.
LED = None
try:
    LED = Pin("LED", Pin.OUT)   # RP2040 boards
except Exception:
    if hasattr(config, "LED_PIN"):
        LED = Pin(config.LED_PIN, Pin.OUT)
if LED:
    LED.value(0)  # start OFF

# Drive system bundle (motors, driver, encoders, diff-drive controller)
drive = DriveSystem()

# Optional IMU (not used yet in this loop, but wired for future use)
imu = None
try:
    i2c = I2C(
        config.I2C_ID,
        scl=Pin(config.I2C_SCL_PIN),
        sda=Pin(config.I2C_SDA_PIN),
        freq=config.I2C_FREQ,
    )
    imu = MPU6050(i2c)
    imu.wake()
except Exception as e:
    imu = None
    if DEBUG_PRINT:
        print("IMU init failed or not present:", e)

# UART link to the Pi 5 (controller is the DriveSystem)
uart_link = PicoVelocityReceiver(
    controller=drive,
    uart_id=UART_ID,
    baud=UART_BAUDRATE,
    tx_pin=UART_TX_PIN,
    rx_pin=UART_RX_PIN,
    debug=False,                    # set True for verbose UART debug
)


# ===================== diagnostics helper =====================

def print_diagnostics(now_ms: int) -> None:
    """
    Print a compact but useful diagnostics snapshot.

    This is aimed at first-run troubleshooting in Thonny:
        - commanded vs measured body velocities
        - left/right target RPM vs measured RPM
        - left/right PID duty and saturation
        - basic encoder info (ticks)
        - drive loop timing and timeout flag
    """
    dd = drive.controller.get_diagnostics()
    fb = drive.controller.get_drive_feedback()

    left = drive.left_motor.get_diagnostics()
    right = drive.right_motor.get_diagnostics()

    left_enc = drive.left_encoder
    right_enc = drive.right_encoder

    # Basic body command and measured velocities
    cmd_lin = dd["cmd"]["linear_mps"]
    cmd_ang = dd["cmd"]["angular_rps"]
    meas_lin = dd["body"]["linear_mps"]
    meas_ang = dd["body"]["angular_rps"]

    # Targets
    spL = dd["target_rpm"]["left"]
    spR = dd["target_rpm"]["right"]

    # Measured RPM from encoders
    measL = left_enc.rpm if hasattr(left_enc, "rpm") else 0.0
    measR = right_enc.rpm if hasattr(right_enc, "rpm") else 0.0

    errL = spL - measL
    errR = spR - measR

    # PID duty & saturation
    MIN_DUTY = getattr(config, "MIN_DUTY", 0)
    MAX_DUTY = getattr(config, "MAX_DUTY", 65535)

    dutyL = float(left["last_output"])
    dutyR = float(right["last_output"])

    satL = (dutyL <= MIN_DUTY + 1) or (dutyL >= MAX_DUTY - 1)
    satR = (dutyR <= MIN_DUTY + 1) or (dutyR >= MAX_DUTY - 1)

    # Encoder ticks
    ticksL = getattr(left_enc, "ticks", 0)
    ticksR = getattr(right_enc, "ticks", 0)

    loop_us = dd["loop_time_us"]
    timeout = dd["timeout"]

    print("\n=== DRIVE DIAGNOSTICS @ t={} ms ===".format(now_ms))
    print("  CMD   : v_cmd = {:.3f} m/s,  w_cmd = {:.3f} rad/s".format(cmd_lin, cmd_ang))
    print("  MEAS  : v_meas = {:.3f} m/s, w_meas = {:.3f} rad/s".format(meas_lin, meas_ang))
    print("  RPM   : SP L = {:7.2f},   SP R = {:7.2f}".format(spL, spR))
    print("          MEAS L = {:7.2f}, MEAS R = {:7.2f}".format(measL, measR))
    print("          ERR  L = {:7.2f}, ERR  R = {:7.2f}".format(errL, errR))
    print("  DUTY  : L = {:7.0f} (sat={}), R = {:7.0f} (sat={})".format(dutyL, satL, dutyR, satR))
    print("  TICKS : L = {:d}, R = {:d}".format(ticksL, ticksR))
    print("  LOOP  : {} us, timeout = {}".format(loop_us, timeout))
    print("  FB    : v_meas = {:.3f} m/s, omega_meas = {:.3f} rad/s".format(
        fb["v_meas"], fb["omega_meas"]))
    print("          left_rpm = {:.2f}, right_rpm = {:.2f}".format(
        fb["left_rpm"], fb["right_rpm"]))
    print("          status_flags = 0x{:08X}".format(fb["status_flags"]))
    print("==========================================")

# ===================== main loop =====================

try:
    # Enable driver
    drive.driver.enable()

    # Seed local command if we're not using UART control
    if not USE_UART_CMD:
        drive.set_cmd_vel(LOCAL_V_CMD, LOCAL_W_CMD)

    now = ticks_ms()
    next_ctrl   = ticks_add(now, CTRL_PERIOD_MS)
    next_stat   = ticks_add(now, STATUS_PERIOD_MS)
    next_led    = ticks_add(now, LED_PERIOD_MS)
    next_cmd    = ticks_add(now, CMD_KEEPALIVE_MS)
    led_state   = 0

    if DEBUG_PRINT:
        print("Robot main loop starting.")
        print("  CTRL_PERIOD_MS   =", CTRL_PERIOD_MS)
        print("  STATUS_PERIOD_MS =", STATUS_PERIOD_MS)
        print("  UART baud        =", UART_BAUDRATE)
        print("  USE_UART_CMD     =", USE_UART_CMD)

    while True:
        now = ticks_ms()

        # 1) Primary drive control loop
        if ticks_diff(now, next_ctrl) >= 0:
            drive.update()
            next_ctrl = ticks_add(next_ctrl, CTRL_PERIOD_MS)

        # 2) Incoming UART commands from Pi
        if USE_UART_CMD:
            try:
                uart_link.poll()
            except Exception as e:
                print("UART error in poll():", e)
                # optionally clear buffer or count errors instead of stopping
        else:
            # Keep-alive for local command mode
            if ticks_diff(now, next_cmd) >= 0:
                drive.set_cmd_vel(LOCAL_V_CMD, LOCAL_W_CMD)
                next_cmd = ticks_add(next_cmd, CMD_KEEPALIVE_MS)

        # 3) Heartbeat LED
        if LED and ticks_diff(now, next_led) >= 0:
            led_state ^= 1
            LED.value(led_state)
            next_led = ticks_add(next_led, LED_PERIOD_MS)

        # 4) Console diagnostics
        if DEBUG_PRINT and ticks_diff(now, next_stat) >= 0:
            print_diagnostics(now)
            next_stat = ticks_add(next_stat, STATUS_PERIOD_MS)

        # 5) Small sleep to keep CPU usage reasonable
        sleep_ms(1)

except KeyboardInterrupt:
    pass

finally:
    # Safe shutdown
    try:
        drive.stop(brake=True)
        drive.driver.disable()
    except Exception:
        pass

    if LED:
        LED.value(0)

    print("Stopped safely.")
