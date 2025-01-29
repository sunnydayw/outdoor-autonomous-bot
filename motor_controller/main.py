'''
The goal of this code is meant to run on an Pico Pi and handle:
Driving motors (via various driver boards).
Reading encoders (for odometry).
Performing PID control for a differential-drive robot wheel velocities.
Optionally driving servos (like a camera servo).
Reading basic sensors (like ultrasonic sensors).
Communicating with a ROS node over serial.

User can Enable/disable features via #define directives (for motor drivers, encoder drivers, or servo usage).


'''

# main.py

import sys
import time
from commands import *
import motor_driver
import encoder_driver

def setup():
    motor_driver.init_motor_driver()
    encoder_driver.init_encoders()
    print("MicroPython ROS Bridge started.")

def loop():
    # poll encoders to update speed/distance calculations
    encoder_driver.poll_encoders()

    # check for input from USB serial
    if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
        line = sys.stdin.readline().strip()
        if line:
            process_command(line)

def process_command(line):
    # e.g. "m 100 -50"
    parts = line.split()
    cmd = parts[0]

    if cmd == CMD_SET_SPEEDS:   # 'm'
        if len(parts) < 3:
            print("ERR: need 2 args for 'm'")
            return
        left_speed = int(parts[1])
        right_speed= int(parts[2])
        motor_driver.set_motor_speeds(left_speed, right_speed)
        print("OK set speeds", left_speed, right_speed)

    elif cmd == CMD_READ_ENCODERS:  # 'e'
        left_count = encoder_driver.read_encoder(LEFT)
        right_count= encoder_driver.read_encoder(RIGHT)
        print(left_count, right_count)

    elif cmd == CMD_RESET_ENCODERS: # 'r'
        encoder_driver.reset_encoders()
        print("OK reset encoders")

    else:
        print("Unknown cmd:", cmd)


# Since MicroPython doesn't have a standard "main()", we do:
if __name__ == "__main__":
    import select  # needed for non-blocking input in this example
    setup()
    
    while True:
        loop()
        time.sleep(0.01)  # 10ms loop
