# Minimal UART-only test harness for the Pico.
#
# Deploy this as main.py on the Pico to verify Pi -> Pico velocity frames.
# It listens on UART0 (pins 0/1), prints when a new command arrives,
# and blinks the onboard LED as a heartbeat.

from machine import Pin
from time import ticks_ms, ticks_diff, sleep_ms

from pico_uart_comm import PicoVelocityReceiver

# UART configuration (adjust if your wiring differs)
UART_ID = 0
UART_BAUDRATE = 115200
UART_TX_PIN = 0  # Pico TX to Pi RX
UART_RX_PIN = 1  # Pico RX to Pi TX


class TestController:
    """Tiny stand-in for the drive controller; just logs velocity updates."""

    def __init__(self):
        self.linear = 0.0
        self.angular = 0.0

    def update_cmd_vel(self, linear, angular):
        changed = (abs(linear - self.linear) > 1e-4) or (abs(angular - self.angular) > 1e-4)
        self.linear = linear
        self.angular = angular
        if changed:
            print("Got velocity command: v={:.3f} m/s, w={:.3f} rad/s".format(linear, angular))


def main():
    led = None
    try:
        led = Pin("LED", Pin.OUT)
        led.value(0)
    except Exception:
        led = None

    ctrl = TestController()
    uart_link = PicoVelocityReceiver(
        controller=ctrl,
        uart_id=UART_ID,
        baud=UART_BAUDRATE,
        tx_pin=UART_TX_PIN,
        rx_pin=UART_RX_PIN,
        debug=True,
    )

    print("UART test starting (baud={}, tx={}, rx={})".format(UART_BAUDRATE, UART_TX_PIN, UART_RX_PIN))

    heartbeat_ms = 500
    next_beat = ticks_ms() + heartbeat_ms

    while True:
        uart_link.poll()

        now = ticks_ms()
        if led and ticks_diff(now, next_beat) >= 0:
            led.toggle()
            next_beat = now + heartbeat_ms

        sleep_ms(5)


if __name__ == "__main__":
    main()
