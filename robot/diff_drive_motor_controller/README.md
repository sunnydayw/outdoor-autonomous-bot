# Diff Drive Controller Implementation

This section covers the implementation of the differential drive controller, including the motor control, encoder feedback, and ROS-style cmd_vel processing. The design uses asynchronous control (via uasyncio) to drive two motors concurrently while maintaining straight-line motion and providing a cmd_vel timeout for safety.

---

## Overview

- **Encoder Module:**  
  The `encoder.py` file defines the `Encoder` class, which captures encoder ticks via interrupts and calculates RPM from the tick counts.

- **Motor Module:**  
  The `motor.py` file provides the `Motor` class, featuring both blocking and asynchronous (non-blocking) PID-based control. The PID controller uses feed-forward and a slew-rate limiter to smooth transitions.

- **Diff Drive Controller:**  
  The `diff_drive_controller.py` module implements a ROS-style differential drive controller that accepts `cmd_vel` commands (linear and angular velocities). It converts these into left and right wheel RPMs based on your robot’s geometry and continuously commands the motors. A timeout feature stops the motors if no new command is received.

- **Configuration:**  
  All configurable parameters (PID gains, feed-forward settings, PWM limits, and robot geometry) are centralized in `config.py`.

- **Main Application:**  
  The `main.py` file ties everything together, running an asynchronous control loop. It currently includes a simulated cmd_vel publisher for testing, with the option to integrate wired or network communication in the final setup.

---

## File Structure

- **config.py**  
  Central configuration for PWM settings, PID gains, feed-forward parameters, robot geometry (wheel radius and separation), and timeout values.

- **encoder.py**  
  Implementation of the `Encoder` class for counting ticks and computing RPM.

- **motor.py**  
  Contains the `Motor` class with methods for both open-loop and closed-loop (PID) control. Includes a blocking `set_rpm()` and an asynchronous `set_rpm_async()` function.

- **diff_drive_controller.py**  
  Implements the `DiffDriveController` class which:
  - Processes cmd_vel commands.
  - Converts linear and angular velocities to individual wheel RPMs.
  - Commands the left and right motors asynchronously.
  - Implements a cmd_vel timeout to ensure safety.

- **main.py**  
  Example application that initializes the encoders, motors, and diff drive controller, and runs the control loop. It currently simulates cmd_vel messages for testing purposes.

---

## Usage

1. **Configuration:**  
   Adjust parameters in `config.py` to match your hardware (e.g., wheel radius of 10 inches and wheel separation of 19 inches, PID tuning values, and PWM limits).

2. **Integration:**  
   Replace the simulated cmd_vel publisher in `main.py` with your chosen communication method (e.g., serial or network) for receiving ROS-style cmd_vel commands.

3. **Running the Code:**  
   Deploy the code on your microcontroller (Pico) and run `main.py` using uasyncio. The diff drive controller will continuously update the motor commands based on the latest cmd_vel inputs, and stop the motors if commands time out.

---

## Highlights

- **Asynchronous Control:**  
  The asynchronous (non-blocking) design allows the controller to run concurrently with other tasks, keeping the system responsive.

- **PID with Feed-Forward and Slew-Rate Limiting:**  
  Each motor is controlled by a PID loop that includes a feed-forward term and a slew-rate limiter to ensure smooth transitions and accurate tracking of target RPMs.

- **ROS Compatibility:**  
  The diff drive controller accepts cmd_vel commands similar to the ROS `diff_drive_controller` package, making it easier to integrate with higher-level navigation systems.

- **Safety Features:**  
  The cmd_vel timeout stops the motors if no new command is received within the specified time, ensuring safe operation.

---

This implementation is still under development.
