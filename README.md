# Outdoor Autonomous Bot

This project plan to build a differential drive robot platform designed for semi-autonomous outdoor use. It started as a lawn mowing idea but has expanded to include street cleaning, trash collection, and park maintenance, all with the goal of creating cleaner, greener spaces.

## Motivation

I’ve always loved robotics and the idea of using technology to free people from repetitive chores like mowing lawns. After moving back to NYC, I was disappointed by the amount of trash on the streets and in parks, especially during my runs. Seeing litter and debris overshadow the beauty of nature and public spaces made me realize how much a clean environment can affect our mental health.

While the ultimate solution is to encourage people not to litter in the first place, I wanted to start with something I could control. This robot is my way of making an impact—helping park rangers and others keep our shared spaces clean and enjoyable for everyone.

## Roadmap

1. **Build a Base Mobile Robot platform**

    Goal: Assemble a robust mobile base with motor control, power management, and essential sensors (camera, IMU GPS, etc.). Ensure the Raspberry Pi (main controller) communicates reliably with the Pico (motor controller) and intergrate a RC receiver for manual control.

2. **Perception Stack (Computer Vision)**

    Goal: Enable the robot to see and recognize trash and hazards. Develop a vision pipeline to detect small trash items (bottle caps, cigarette butts, plastic pieces) and dog poop with onboard cameras. Also, interpret camera data to identify traversable terrain (grass, roads, or sidewalk) and dangerous obstacles (e.g. stairs or drop-offs) in the park environment.

3. **Autonomy and Path Planning**

    Goal: Enable the robot to navigate the park along predefined routes, deviate to pick up detected trash, and avoid obstacles. This involves mapping, localization, path planning, and low-level motion control.

4. **User Interface (Mission Control Station)**

    Goal: Create a user-friendly interface (desktop and/or tablet compatible) for monitoring and controlling the robot. The interface should display the robot’s status and position on a map, live video feed, and allow manual teleoperation or mission scheduling (waypoint queue). It will run on a base station computer or tablet communicating with the robot over wireless network.

5. **Revisit Plan for Lawn Mowing and Robot Arm Function**

## Hardware

This section provides a detailed Bill of Materials (BOM) for the mechanical and electrical components used in the robot design.

---

### **Mechanical Components**
| ITEM NO. | PART NUMBER       | DESCRIPTION                                                  | QTY. | NOTES                |
|----------|-------------------|--------------------------------------------------------------|------|----------------------|
| 1        | BASE              | BASE                                                        | 1    | Main robot platform  |
| 2        | 19525T13          | Nonmarking High-Temperature Swivel Caster                   | 1    |                     |
| 3        | CASTER SPACER     | CASTER SPACER                                               | 1    |                     |
| 4        | HUBWHEEL          | HUBWHEEL                                                    | 2    |                     |
| 5        | TIRE 10IN         | TIRE 10IN                                                   | 2    |                     |
| 6        | HUBWHEEL SHAFT    | HUBWHEEL SHAFT                                              | 2    |                     |
| 7        | HUBWHEEL MOUNT    | HUBWHEEL MOUNT                                              | 2    |                     |
| 8        | HUBWHEEL MOUNT CLAMP | HUBWHEEL MOUNT CLAMP                                       | 2    |                     |
| 9        | 91502A135         | Blue-Dyed Zinc-Plated Alloy Steel Socket Head Screw (M4x50) | 8    | For frame assembly  |
| 10       | 94645A101         | High-Strength Steel Nylon-Insert Locknut (M4)               | 8    | For frame assembly  |
| 11       | 91502A132         | Blue-Dyed Zinc-Plated Alloy Steel Socket Head Screw (M4x35) | 4    |                     |
| 12       | 90591A255         | Zinc-Plated Steel Hex Nut (M4)                              | 8    |                     |
| 13       | 90128A215         | Zinc-Plated Alloy Steel Socket Head Screw (M4x16)           | 4    |                     |
| 14       | 90128A268         | Zinc-Plated Alloy Steel Socket Head Screw (M6x40)           | 4    |                     |
| 15       | 94645A205         | Zinc-Plated Steel Hex Nut (M6)                              | 4    |                     |

---

### **Electrical Components**

| ITEM NO. | COMPONENT                  | DESCRIPTION                                                                                 | PURCHASE LINK                                                                                                  | NOTES                                      |
|----------|----------------------------|---------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------|--------------------------------------------|
| 1        | Battery Adapter            | Multi-Functional USB Charger Adapter with 2 USB Ports, 1 Type-C Port, and DC XT60 Port      | [Amazon](https://www.amazon.com/)                                                                             | For Milwaukee M18 battery                  |
| 2        | Battery                    | Milwaukee M18 Lithium Battery                                                              | [Milwaukee](https://www.milwaukeetool.com/)                                                                   | Primary power source. Drill batteries are readily available and reliable. Could consider different power sources in the future. |
| 3        | Main Controller            | Raspberry Pi 5 (8GB)                                                                       | [Raspberry Pi](https://www.raspberrypi.org/)                                                                  | Handles navigation and computer vision processing tasks. |
| 4        | Microcontroller            | Raspberry Pi Pico 2 W                                                                      | [Raspberry Pi](https://www.raspberrypi.org/)                                                                  | For low-level motor and sensor control.     |
| 5        | Motor Controller           | JYQD_YL02D 12-36VDC Electric Scooter Controller                                            | [Controller Link](https://www.example.com/)                                                                   | Controls hub wheel motors. Budget option, potential upgrade in the future. |
| 6        | Motors                     | 10-inch 360W Hub Wheel Motors (2 units)                                                    | [Hub Motors](https://www.example.com/)                                                                        | Primary propulsion system for the robot. |

---

### **Notes**
- **Mechanical Components**: Designed for durability and modularity to handle outdoor environments.
- **Battery Considerations**: The Milwaukee M18 Lithium Battery offers a reliable and accessible solution. Future iterations may explore alternative power sources to improve efficiency or runtime.
- **Motor Controller**: The current motor controller is a budget-friendly choice. Future upgrades could enhance performance and enable additional features.
- **System Modularity**: The electrical system is designed to be modular, allowing for easy replacement and future upgrades of individual components.- Purchase links are placeholders and should be updated with specific vendor links for your components.

## Software

The software architecture is designed with a modular approach to separate low-level control and high-level control, ensuring efficient processing and scalability.

The software is divided into few different components:
1. [**Motor Control**](docs/hubmotor_low_level_control.md):

    Implements real-time motor control on the Raspberry Pi Pico 2 W. This module converts angular and linear velocity commands into precise PWM signals for the differential drive, integrates RC manual override

2. [**SLAM & Navigation**](docs/high_level_control.md):

    Deployed on the Raspberry Pi 5, this layer handles localization and path planning. It fuses data from GPS, wheel odometry, and (optionally) lidar to create a map of the operating environment, plan safe trajectories along predefined waypoints, and execute reactive obstacle avoidance.

3. **Computer Vision**:

    Processes camera feeds in real time to detect general trash (bottle caps, cigarette butts, plastics) and pet waste. Using a lightweight object detection model (e.g., YOLO-based), this module identifies trash pickup points and drivable terrain, providing cues to the navigation system.

4. **User Interface (Mission Control)**:

    A dashboard accessible via desktop and iPad that offers live telemetry, video streaming, and manual control. This interface includes an interactive map for mission planning, waypoint editing, and visual garbage mapping.

---
