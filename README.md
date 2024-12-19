# Outdoor Autonomous Bot

This project is a differential drive robot platform designed for autonomous outdoor navigation. It started as a lawn mowing idea but has expanded to include street cleaning, trash collection, and park maintenance, all with the goal of creating cleaner, greener spaces.

## Motivation

I’ve always loved robotics and the idea of using technology to free people from repetitive chores like mowing lawns. After moving back to NYC, I was disappointed by the amount of trash on the streets and in parks, especially during my runs. Seeing litter and debris overshadow the beauty of nature and public spaces made me realize how much a clean environment can affect our mental health.

While the ultimate solution is to encourage people not to litter in the first place, I wanted to start with something I could control. This robot is my way of making an impact—helping park rangers and others keep our shared spaces clean and enjoyable for everyone.

## Roadmap

1. **Build a Mobile Robot Base**
    - Select key components such as the compute unit, motors, battery, and controller.
    - Design and assemble a differential drive platform for basic mobility.
    - Test basic movement and control to ensure the robot can move reliably.
    - Optimize PID control loops for precise movement and turning.

2. **Solve Navigation Challenges**
    - Design and implement path planning and localization (e.g., LIDAR, GPS, or camera-based SLAM).
    - Test autonomous navigation in outdoor environments, addressing challenges like terrain variability and GPS signal loss.

3. **Integrate Lawn Mowing Design**
    - Design and build a robust lawn mowing mechanism.
    - Fine-tune path planning for lawn mowing-specific patterns.
    - Test the lawn mowing functionality in controlled environments and evaluate its performance on different types of grass.

4. **Develop Computer Vision for Trash Identification**
    - Train object detection models to identify various litter types (e.g., bottle caps, cans, wrappers).
    - Optimize for outdoor conditions, including lighting changes, cluttered environments, and seasonal variations.
    - Validate the vision system with field data and iteratively improve detection accuracy.

5. **Design and Integrate a Robot Arm**
    - Develop a robotic arm capable of picking up and sorting litter.
    - Implement gripping mechanisms for handling different trash shapes and materials.
    - Add sorting capabilities for separating recyclable and non-recyclable waste.

6. **Combine All Systems**
    - Integrate navigation, vision, mowing (if applicable), and litter handling into a cohesive system.
    - Test the robot's full functionality in real-world environments like parks or urban streets.
    - Iterate on the design to improve reliability and efficiency.
    - 
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

### **Overview**
The software is divided into two primary layers:
1. **Low-Level Control**:
   - Responsible for precise motor control (e.g., rotations, speed, and direction).
   - Runs on a microcontroller (e.g., Raspberry Pi Pico 2 W) to offload tasks from the main controller.

2. **High-Level Control**:
   - Handles navigation, path planning, and integration with task-specific modules like computer vision and robotic arm control.
   - Runs on the Raspberry Pi 5 using ROS 2.

---

### **Details**
1. [Low-Level Control](docs/hubmotor_low_level_control.md)
   - Focuses on motor control algorithms and GPIO handling.
   - Includes methods for converting angular and linear velocity commands into motor outputs.

2. [High-Level Control](docs/high_level_control.md)
   - Outlines the use of ROS 2 for navigation and task coordination.
   - Discusses communication between the main controller and the low-level controller.

---

### **Current Progress**
- **Low-Level Control**:
    - Developing scripts to control motor rotation and drive the robot specific distances.
    - Testing and fine-tuning foundational low-level control algorithms to ensure precise and repeatable movement.

- **High-Level Control**:
  - TBD

---
