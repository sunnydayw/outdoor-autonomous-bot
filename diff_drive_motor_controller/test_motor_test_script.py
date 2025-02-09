import time
from machine import Pin
from config import (
    LEFT_MOTOR_SPEED_PIN, LEFT_MOTOR_DIRECTION_PIN, LEFT_MOTOR_BRAKE_PIN, LEFT_MOTOR_ENCODER_PIN,
    RIGHT_MOTOR_SPEED_PIN, RIGHT_MOTOR_DIRECTION_PIN, RIGHT_MOTOR_BRAKE_PIN, RIGHT_MOTOR_ENCODER_PIN
)
from encoder import Encoder
from motor import Motor
from diff_drive_controller import DiffDriveController

# --- Create Encoders ---
left_encoder = Encoder(pin_num=LEFT_MOTOR_ENCODER_PIN, ticks_per_rev=90)
right_encoder = Encoder(pin_num=RIGHT_MOTOR_ENCODER_PIN, ticks_per_rev=90)
    
# --- Create Motors ---
# NOTE: Depending on your physical wiring, you may need to set invert=True on one side
# so that both wheels spin 'forward' with the same sign of target RPM.
left_motor = Motor(
    speed_pin=LEFT_MOTOR_SPEED_PIN,
    direction_pin=LEFT_MOTOR_DIRECTION_PIN,
    brake_pin=LEFT_MOTOR_BRAKE_PIN,
    encoder=left_encoder,
    invert=True
)
right_motor = Motor(
    speed_pin=RIGHT_MOTOR_SPEED_PIN,
    direction_pin=RIGHT_MOTOR_DIRECTION_PIN,
    brake_pin=RIGHT_MOTOR_BRAKE_PIN,
    encoder=right_encoder,
    invert=False  # Often the right motor needs to be inverted, adjust as needed
)

# Initialize the DiffDriveController
controller = DiffDriveController(left_motor, right_motor)

def drive_run_for_seconds(controller: DiffDriveController, linear: float, angular: float, duration_s=3):
    t_start = time.ticks_ms()
    print("start running")
    while time.ticks_diff(time.ticks_ms(), t_start) < (duration_s * 1000):
        controller.update_cmd_vel(linear,angular)
        controller.compute_wheel_rpms()
        controller.update_motors()
        print(controller.motor_status)  # This will print the actual milliseconds value
        
        time.sleep_ms(12)  # 10 ms loop time (adjust as needed)
    print("end test")
    motor.brake()

def run_for_seconds(motor: Motor, rpm: int, duration_s=3):
    t_start = time.ticks_ms()
    print("start running")
    while time.ticks_diff(time.ticks_ms(), t_start) < (duration_s * 1000):
        # Update each motor with the computed RPM setpoint
        motor.set_target_rpm(rpm)
        # Run motor control loop
        motor.update()
        print(motor.current_rpm)  # This will print the actual milliseconds value
        
        time.sleep_ms(12)  # 10 ms loop time (adjust as needed)
    print("end test")
    motor.brake()

def main():
    try:
        #run_for_seconds(motor=right_motor, rpm=50,duration_s=10)
        drive_run_for_seconds(controller=controller, linear=3.0, angular=0, duration_s=10)
    except KeyboardInterrupt:
        print("Interrupted by user, stopping.")
        # Optionally brake motors:
        left_motor.brake()
        right_motor.brake()

if __name__ == "__main__":
    main()
