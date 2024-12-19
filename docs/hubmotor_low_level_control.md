# Hub Motor Low-Level Control

This document provides detailed information on the low-level control implementation for the hub motors, including pin configuration, the JYQD_YL02D motor controller pinout, and integration with the Raspberry Pi Pico.

---

## Overview

The hub motor control system is responsible for managing motor speed, direction, and braking using the JYQD_YL02D motor controller. This setup allows precise control of motor rotations and distances by converting high-level commands into PWM signals and direction changes.

However, the JYQD_YL02D motor controller has its limitations as a budget option. For a detailed review, see this video: [JYQD V7. 3E Review cheap Chinese brushless motor controller](https://www.youtube.com/watch?v=gH4Vb8bXj34). Despite these constraints, the control code should be transferable to other motor controllers with minor adjustments in the future.

---

## JYQD_YL02D Motor Controller Pinout

### **Control Port Pin Description**
| Pin Name  | Description                                                                 |
|-----------|-----------------------------------------------------------------------------|
| 5V        | Internal 5V output, provides up to 300mA of current to external devices.    |
| EL        | Brake control port. Analog voltage braking (0-5V) with energy recovery.     |
| M         | Speed signal output. Pulse frequency is proportional to motor speed.        |
| Z/F       | Forward/reverse control port. 5V or floating for one direction, GND for reverse. |
| VR        | Speed control port. Analog voltage control (0V-5V) or external PWM control. |
| GND       | Ground.                                                                    |


### **Pico Pin Configuration**

The following table details the connections between the JYQD_YL02D motor controller and the Raspberry Pi Pico for both the left and right wheels:

| JYQD_YL02D Pin | Description          | Pico Pin (Right Wheel) | Pico Pin (Left Wheel)  |
|----------------|----------------------|-------------------------|------------------------|
| EL             | Braking control     | GPIO 10 (PWM)           | GPIO 21 (PWM)         |
| M              | Speed signal output | GPIO 11 (Input)         | GPIO 20 (Input)       |
| Z/F            | Direction control   | GPIO 12 (Output)        | GPIO 19 (Output)      |
| VR             | Speed control       | GPIO 13 (PWM)           | GPIO 18 (PWM)         |
| GND            | Ground              | GND                     | GND                   |


### Notes:
- **Direction Control (Z/F)**: Sets the motor direction; left and right motor should be set to oppsite for the same direction

---

## **Converting Linear and Angular Velocity to Motor Commands**

### **Differential Drive Kinematics**
A differential drive robot controls its movement by varying the speeds of its left and right wheels. This system allows the robot to move in straight lines, rotate in place, or follow curved paths.  

In this setup:
- **Linear velocity ( V )**: The robot's forward or backward speed.
- **Angular velocity ( ω )**: The robot's rotational speed about its center.

Given:
- **Wheel diameter**: 10 inches (radius = 5 inches).
- **Wheelbase (distance between two wheels,  D )**: 19 inches.
- **Pulses per wheel rotation**: 45.

---

### **Wheel Velocities to Rotations**
To calculate wheel rotations and distances, we use the wheel’s geometry:
- **Wheel circumference**: 31.41593 inches (≈ 80 cm).
- **Distance per pulse**: 0.698 inches (≈ 1.78 cm).

Given the pulses measured over time, the velocity can be calculated as:

![Velocity Formula](https://via.placeholder.com/500x100?text=Velocity+%3D+%28Pulses+*+1.78%29+%2F+Time)

To control motor speed precisely, we use PWM signals. The PID controller ensures the motor reaches the desired velocity quickly and accurately while compensating for external factors like friction or load.

---

### **Solving Left and Right Wheel Velocities**
For a differential drive robot, the left ( V_l ) and right ( V_r ) wheel velocities are calculated based on the linear ( V ) and angular ( ω ) velocities:

![Right Wheel Velocity](https://via.placeholder.com/500x100?text=V_r+%3D+V+%2B+%28%CE%A9+*+D%2F2%29)
![Left Wheel Velocity](https://via.placeholder.com/500x100?text=V_l+%3D+V+-+%28%CE%A9+*+D%2F2%29)

Where:
- \( V \) is the linear velocity in cm/s.
- \( \omega \) is the angular velocity in radians/s.
- \( D \) is the distance between the wheels (19 inches, converted to 48.26 cm).

These equations ensure that:
- When \( \omega = 0 \), both wheels move at the same speed for straight-line motion.
- When \( V = 0 \), the wheels move in opposite directions for in-place rotation.
- When both \( V \) and \( \omega \) are non-zero, the robot follows a curved path.

---

### **Testing Motor Control**

After implementing the motor control logic, the following tests should be conducted to evaluate the system's performance:

#### 1. **Drive a Specific Distance**
- Command the robot to travel a predefined distance (e.g., 100 cm).
- Measure the actual distance traveled and compare it with the expected distance using the pulse feedback.

#### 2. **360° Rotation in Place**
- Command the robot to rotate 360° in place.
- Verify the number of pulses and the time taken to complete the rotation.

#### 3. **Combined Movement**
- Command the robot to:
  - Drive forward a certain distance.
  - Rotate in place to a specified angle.
  - Drive back to the starting point.
- This test evaluates the system's ability to handle sequential commands accurately.

---
