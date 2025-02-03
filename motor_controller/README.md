High Level Project layout
PicoROSBridge/
  ├─ main.py               (entry point, runs on boot if you want)
  ├─ commands.py           (defines command strings or a command dictionary)
  ├─ motor_driver.py       (motor driver control in MicroPython)
  ├─ encoder_driver.py     (encoder reading in MicroPython)
  ├─ pid_controller.py
  ├─ ...
  └─ README.md


here are some parameters we have
hardware raspberry Pi Pico 2 wireless
coding - micropython
encoder pin = 20
direction pin=19 high and low
brake_pin=21 pwm signal, 0 no break and break power apply proportional based on pwm
speed_pin=18 pwm signal.
each rotation is 45 tickmark
let write a simple code to rotate the wheel exactly one rotation


The wheel keep overshoot the target, lets add an simple PID control to it