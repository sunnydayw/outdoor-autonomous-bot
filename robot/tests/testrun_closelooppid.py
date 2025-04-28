# test_motor_pid.py
import time
from test_motor import Motor
from test_encoder import Encoder
from test_config import (LEFT_MOTOR_DIRECTION_PIN, LEFT_MOTOR_SPEED_PIN,
                         LEFT_MOTOR_BRAKE_PIN, LEFT_MOTOR_ENCODER_PIN,
                         FULL_DUTY, MIN_DUTY, MAX_DUTY, Kff, offset, MAX_RUN_TIME_MS)

# Create an Encoder instance (adjust ticks_per_rev as needed).
encoder = Encoder(LEFT_MOTOR_ENCODER_PIN, ticks_per_rev=90)

# Create a Motor instance.
motor = Motor(LEFT_MOTOR_DIRECTION_PIN, LEFT_MOTOR_SPEED_PIN, LEFT_MOTOR_BRAKE_PIN, encoder, reverse_dir=False)

def test_set_rpm(target_rpm, run_time=10):
    """
    Run closed-loop PID control at a specified target RPM (using set_rpm() logic)
    for run_time seconds, logging:
      - Time (s)
      - Measured RPM
      - Error (target - measured)
      - PID Correction (Kp*error + Ki*integral + Kd*derivative)
      - Feed-Forward contribution (Kff * target_rpm + offset)
      - PWM Output (applied duty cycle)
      
    The function then prints the logged data as a table and computes the average RPM over the last 3 seconds.
    """
    print("--------------------------------------------------")
    print("Testing closed-loop PID for target RPM: {} RPM".format(target_rpm))
    motor.encoder.reset()
    
    # Set the desired direction.
    if target_rpm < 0:
        desired_direction = 0 if not motor.reverse_dir else 1
        target_rpm = -target_rpm
    else:
        desired_direction = 1 if not motor.reverse_dir else 0
    motor.direction.value(desired_direction)
    
    # Initialize PID state.
    integral = 0.0
    last_error = 0.0
    start_time = time.ticks_ms()
    last_time = start_time
    last_output = 0
    max_delta = 10000  # Slew-rate limiter
    
    # Log data: each entry is a tuple
    # (Time(s), Measured RPM, Error, PID Correction, Feed-Forward, PWM Output)
    log_data = []

    while time.ticks_diff(time.ticks_ms(), start_time) < run_time * 1000:
        current_time = time.ticks_ms()
        dt = time.ticks_diff(current_time, last_time) / 1000.0
        if dt < 0.02:
            continue
        last_time = current_time

        measured_rpm = motor.encoder.get_rpm()
        error = target_rpm - measured_rpm

        integral += error * dt
        derivative = (error - last_error) / dt
        last_error = error

        pid_correction = motor.Kp * error + motor.Ki * integral + motor.Kd * derivative
        feed_forward = Kff * target_rpm + offset
        output = feed_forward + pid_correction

        if output < 0:
            output = 0
        if output > FULL_DUTY:
            output = FULL_DUTY
        elif 0 < output < MIN_DUTY:
            output = MIN_DUTY

        # Slew-rate limiting:
        delta = output - last_output
        if delta > max_delta:
            output = last_output + max_delta
        elif delta < -max_delta:
            output = last_output - max_delta
        last_output = output

        motor.speed_pwm.duty_u16(int(output))

        t_sec = time.ticks_diff(current_time, start_time) / 1000.0
        log_data.append((t_sec, measured_rpm, motor.Kp * error, motor.Ki * integral, motor.Kd * derivative, pid_correction))
        time.sleep(0.1)

    # Stop motor.
    motor.speed_pwm.duty_u16(0)
    motor.brake_pwm.duty_u16(FULL_DUTY)
    time.sleep(0.5)
    motor.brake_pwm.duty_u16(0)

    # Print logged data table.
    header = "Time(s)\t RPM\t Error\t integral\t derivative\t pid_correction"
    print(header)
    for entry in log_data:
        print("{:.2f}\t{:.2f}\t{:.2f}\t{:.2f}\t\t{:.2f}\t\t{}".format(
            entry[0], entry[1], entry[2], entry[3], entry[4], entry[5]))
    
    # Compute and print the average RPM over the last 3 seconds.
    last_entries = [e for e in log_data if e[0] > (run_time - 3)]
    if last_entries:
        avg_rpm = sum(e[1] for e in last_entries) / len(last_entries)
        print("Average RPM (last 3 s): {:.2f}".format(avg_rpm))
    else:
        print("Not enough data for average RPM.")
    print("--------------------------------------------------\n")
    time.sleep(2)

# List of target RPM values for testing.
target_rpm_values = [40, 60, 80, 100, 120]

print("Starting closed-loop PID performance test.")
for rpm in target_rpm_values:
    test_set_rpm(rpm, run_time=5)
print("Closed-loop PID performance test complete.")

