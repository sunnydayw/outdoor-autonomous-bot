# Mid-Size Robot Platform v1 – Specification (Draft)

> This document defines a **draft** specification for the mid-size outdoor mobile platform to be used as the base for the tennis ball collecting robot.  
> All values are initial targets and may be refined through prototyping and testing.

---

## 1. Intended Use

- Primary use case:  
  - Autonomous tennis ball collection on outdoor hard courts.
- Secondary future use cases (not in v1 scope, but influencing design):
  - Light outdoor tasks such as patrol, light cleaning, or other attachments on the same base.

The platform is designed as a **general mid-size outdoor base** with sufficient payload capacity and extensibility for multiple task modules.

---

## 2. Physical Specifications (Target Ranges)

> All dimensions and weights below are target ranges, not final constraints.

- **Overall Dimensions (L × W × H)**
  - Target range: **45–70 cm × 40–60 cm × 35–60 cm**
  - Tennibot 官方规格示例：尺寸约 17.7" x 22.6" x 21.5"，重量约 33 磅，约可存 80–90 球，续航 4–5 小时。
  - Goals:
    - Small enough to maneuver easily on a standard tennis court.
    - Large enough to provide stability, sufficient battery capacity, and ball storage volume.

- **Weight**
  - Target range: **12–20 kg**
  - Design goal:
    - Transportable by a single adult (lift into a car trunk, carry short distances).
    - Heavy enough to be stable at operational speeds.

- **Ground Clearance**
  - Sufficient to:
    - Traverse tennis court lines and small surface irregularities.
    - Avoid getting stuck on minor debris.
  - Final value to be determined via prototyping.

---

## 3. Locomotion and Drive System

- **Drive Type**
  - Differential drive:
    - Two powered drive wheels.
    - One or more caster/omni wheels for stability.

- **Top Speed**
  - Target: **0.6–1.0 m/s** (approx. 1.3–2.2 mph).
  - Notes:
    - Speed will be limited in software for safety and comfort.
    - Higher mechanical capability may be allowed but restricted by firmware.

- **Turning**
  - Support for:
    - In-place rotation (or very small turning radius).
    - Smooth controlled turns during navigation.

- **Traction**
  - Wheel and tire selection must:
    - Provide sufficient grip on outdoor hard court surfaces.
    - Avoid damaging the court surface.

- **Braking / Emergency Stop**
  - Software-level emergency stop command.
  - Hardware-level interrupt (e.g., physical E-stop button) can be part of a later safety-focused revision.

---

## 4. Ball Collection Subsystem (Task Module)

- **Intake Width**
  - Target: large portion of the robot front width (e.g., 40–50 cm), to reduce missed balls.

- **Mechanism**
  - Front-mounted intake unit that:
    - Guides balls into the robot’s storage area using rolling or sweeping elements.
  - Exact design (roller, brush, belt, etc.) to be determined through mechanical design and testing.

- **Storage Capacity**
  - Target range: **30 tennis balls** per run.
  - Storage must:
    - Securely retain balls during motion.
    - Allow easy unloading (manual or assisted) at a drop-off location, 
    - or feed into the ball shooter system

- **Collection Efficiency**
  - Design goal (to be validated experimentally):
    - Able to collect a realistic number of scattered balls on a court in a reasonable time window, without excessive back-and-forth passes, maybe within 5 min as target.

---

## 5. Power System

- **Battery Type**
  - Rechargeable lithium-based battery pack from existing powered tool

- **Nominal Voltage**
  - Target range: **18–24 V** system voltage.

- **Energy Capacity**
  - Target: sufficient for **multi-hour operation** in tennis ball collection duty cycles.
  - The exact Wh capacity will be determined based on:
    - Drive power consumption.
    - Compute and sensor power consumption.
    - Ball collection mechanism power draw.
 - Estimated battery size to be simialr to 10.5Ah Makita Battery
- **Runtime Target**
  - Design goal: **four hours of typical operation** on a single charge.

- **Charging**
  - Use charger from existing power tool

---

## 6. Compute and Sensing

### 6.1 Compute

- **Main Compute Unit**
  - Single-board computer (e.g., equivalent class to a Raspberry Pi-level device) for:
    - High-level control
    - Perception
    - Communication

- **Optional AI Accelerator**
  - Provision for an AI accelerator (NPU/TPU/GPU/Jetson or similar) for:
    - Real-time vision-based ball detection
    - Future perception tasks
  - 目标整体算力在 5–10 TOPS 的量级（Tennibot 提到 on-device NN 推理和约 8 TOPS 等级，可做参考）

- **Real-Time Control**
  - Either:
    - A dedicated real-time microcontroller for low-level motor control, or
    - A real-time-capable subsystem integrated with the main compute.
    - raspberry pi pico as inital prototype

### 6.2 Sensors

- **Vision**
  - One or more front-facing RGB cameras for:
    - Ball detection
    - Obstacle detection
    - Scene awareness for the operator

- **Odometry**
  - Wheel encoders on drive wheels for:
    - Estimating distance traveled
    - Supporting localization and control loops

- **IMU**
  - 6–9 DoF IMU for:
    - Attitude estimation
    - Short-term motion tracking and stabilization

- **GNSS / RTK or UWB**
  - High-accuracy outdoor positioning when signal quality allows

- **Proximity / Obstacle Sensors**
  - Short-range sensors (ultrasonic / ToF / similar) for:
    - Near-field obstacle detection
    - Additional safety layer during navigation

---

## 7. Connectivity

- **Wireless**
  - Wi-Fi (2.4 / 5 GHz) as the initial primary communication mode.
  - radio controller for test drive

- **Wired Interfaces**
  - USB for setup and debugging.
  - Optional Ethernet for:
    - Development
    - Bench testing
    - Potential integration with a fixed network in a court facility

- **Protocols**
  - Internal communication:
    - Can be implemented via ROS 2, custom middleware, or equivalent.
  - External API:
    - To be exposed via HTTP/gRPC/WebSocket/MQTT or a similar protocol with a clear, documented interface.

---

## 8. Environmental and Reliability Considerations

- **Operating Environment**
  - Outdoor tennis courts.
  - Avoid operation in heavy rain or extreme weather in the initial version.
  - should be operational in the winter time wihtout snow

- **Ingress Protection**
  - Early versions:
    - Basic splash resistance and dust protection.
    - Formal IP rating can be a target for later iterations (e.g., IPX3–X4).

- **Temperature Range**
  - Target working range:
    - Compatible with typical outdoor tennis conditions.
    - Exact numeric range to be defined later.

- **Serviceability**
  - made from 3d printing / laser or CNC
  - The platform should be designed so that:
    - Major components (battery, compute, sensors, wheels) are accessible.
    - Maintenance, repair, and upgrades are feasible without complete disassembly.

---

## 9. Software Interface Considerations

- The platform is expected to provide:

  - **Velocity Control Interface**
    - Commands: linear and angular velocities.
  - **Localization Interface**
    - Unified pose output (position + orientation in a known frame).
  - **Telemetry Interface**
    - Battery status
    - System health
    - Task-related status

- Interfaces must be generic enough so that:
  - Different task modules (tennis ball collection, mowing, etc.) can share the same base APIs.
  - The same mid-size platform can be reused with different task-specific attachments and software components.

This specification is a **living document** and will be updated as prototypes are built and tested.
