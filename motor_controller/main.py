import time
# Import the encoder and motor modules
import encoder_driver
import motor_driver

def test_encoders_only():
    """
    Test routine for encoders:
      - Resets encoders
      - Prints out counts and speed over a short interval
    """
    print("\n--- Test: Encoders Only ---")
    encoder_driver.reset_encoders()
    
    print("\nStart in 3 seconds")
    time.sleep_ms(3000)

    # We'll read the encoders for a couple of seconds
    start_time = time.ticks_ms()
    while time.ticks_diff(time.ticks_ms(), start_time) < 2000:  # 2 seconds
        encoder_driver.poll_encoders()
        left_count = encoder_driver.left_encoder.get_count()
        right_count = encoder_driver.right_encoder.get_count()
        left_speed = encoder_driver.left_encoder.get_speed()
        right_speed = encoder_driver.right_encoder.get_speed()

        print("[ENCODER] L_count:", left_count, 
              "L_speed(m/s):", f"{left_speed:.3f}",
              " | R_count:", right_count,
              "R_speed(m/s):", f"{right_speed:.3f}")
        time.sleep_ms(200)

def test_motor_basic():
    """
    Test basic motor functions:
      - Spin motors forward, then reverse, then stop
    """
    print("\n--- Test: Basic Motor Movement ---")
    # Forward at 50% for 1s
    print("[MOTOR] Running forward at 20%...")
    motor_driver.set_motor_speeds_percent(20, 20, forward_left=True, forward_right=True)
    time.sleep_ms(1000)

    # Reverse at 50% for 1s
    print("[MOTOR] Running in reverse at 20%...")
    motor_driver.set_motor_speeds_percent(20, 20, forward_left=False, forward_right=False)
    time.sleep_ms(1000)

    # Stop
    print("[MOTOR] Stopping motors.")
    motor_driver.set_motor_speed(0, 0)

def test_motor_run_for_time():
    """
    Test the 'run_for_time' method in the Motor class.
    """
    print("\n--- Test: run_for_time ---")
    print("[MOTOR] Left motor run forward 20% for 2s, then brake.")
    motor_driver.motor_left.run_for_time(speed_percent=20, ms=2000, forward=True, brake_percent=100)
    time.sleep_ms(3000)
    print("[MOTOR] Right motor run reverse 30% for 1s, then brake.")
    motor_driver.motor_right.run_for_time(speed_percent=30, ms=1000, forward=False, brake_percent=100)

def test_motor_run_for_counts():
    """
    Test the 'run_for_counts' method with encoders.
      - Make sure to poll encoders in the loop.
    """
    print("\n--- Test: run_for_counts ---")
    encoder_driver.reset_encoders()
    time.sleep_ms(100)  # small delay to ensure reset complete

    # For demonstration, say we want the left motor to move 50 counts forward
    target_counts = 45
    print(f"[MOTOR] Left motor: run forward until +{target_counts} counts reached.")
    motor_driver.motor_left.run_for_counts(
        encoder=encoder_driver.left_encoder,
        speed_percent=50,
        target_counts=target_counts,
        forward=True,
        brake_percent=100
    )

    print("[ENCODER] Final left encoder count:", encoder_driver.left_encoder.get_count())

def integrated_test():
    """
    An integrated test that runs a motor while polling encoders continuously.
    """
    print("\n--- Integrated Test: Motor + Encoders ---")
    encoder_driver.reset_encoders()
    start_time = time.ticks_ms()

    # Start motor forward at 30%
    motor_driver.set_motor_speeds_percent(30, 30, True, True)

    while time.ticks_diff(time.ticks_ms(), start_time) < 3000:  # 3 seconds
        # Poll encoders
        encoder_driver.poll_encoders()
        left_speed = encoder_driver.left_encoder.get_speed()
        right_speed = encoder_driver.right_encoder.get_speed()

        print(f"[INTEGRATED] L_speed: {left_speed:.3f} m/s, R_speed: {right_speed:.3f} m/s")
        time.sleep_ms(300)

    # Stop motors
    motor_driver.set_motor_speed(0, 0)
    print("[INTEGRATED] Motors stopped.")

def main():
    # 1) Initialize everything
    print("[SYSTEM] Initializing encoders and motors...")
    encoder_driver.init_encoders()            # init left_encoder, right_encoder
    motor_driver.init_motor_driver()          # init motor_left, motor_right

    # 2) Test each subsystem or integrated scenario
    test_encoders_only()
    test_motor_basic()
    test_motor_run_for_time()
    test_motor_run_for_counts()
    integrated_test()

    print("[SYSTEM] All tests completed!")

# Entry point
if __name__ == "__main__":
    main()
