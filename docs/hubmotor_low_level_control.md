# Hub Motor Low-Level Control

This document provides detailed information on the low-level control implementation for the hub motors, including pin configuration, the JYQD_YL02D motor controller pinout, and integration with the Raspberry Pi Pico.

---

## Overview

The hub motor control system is responsible for handling motor speed, direction, and braking using the JYQD_YL02D motor controller. This system enables precise control of motor rotations and distances by converting high-level commands into PWM signals and direction changes.

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

---

## Integration with Raspberry Pi Pico

The JYQD_YL02D motor controller is connected to the Raspberry Pi Pico as follows:

### **Pico Pin Configuration**

The following table details the connections between the JYQD_YL02D motor controller and the Raspberry Pi Pico for both the left and right wheels:

| JYQD_YL02D Pin | Description          | Pico Pin (Right Wheel) | Pico Pin (Left Wheel)  |
|----------------|----------------------|-------------------------|------------------------|
| EL             | Braking control     | GPIO 10 (PWM)           | GPIO 21 (PWM)         |
| M              | Speed signal output | GPIO 11 (Input)         | GPIO 20 (Input)       |
| Z/F            | Direction control   | GPIO 12 (Output)        | GPIO 19 (Output)      |
| VR             | Speed control       | GPIO 13 (PWM)           | GPIO 18 (PWM)         |
| GND            | Ground              | GND                     | GND                   |

---

### Notes:
- **Direction Control (Z/F)**: Sets the motor direction; left and right motor should be set to oppsite for the same direction

