# Tennis Ball Collecting Robot – Technical Roadmap

## 1. Overview

This document describes the technical roadmap for a **mid-size outdoor tennis ball collecting robot** and its supporting software stack.

The primary objective is to build a **flagship implementation** for one specific scenario:

> After a tennis session (training or match), the robot autonomously collects scattered balls on a court and returns them to a designated drop-off area.

This flagship scenario will be the foundation for future extensions (e.g., mowing, trash pickup) using the same mid-size platform and a shared software architecture.

---

## 2. Use Case and Constraints

### 2.1 Target Scenario

- Environment: Outdoor hard tennis court (single court to start).
- Typical usage:
  - After a session: user presses a button (on device or web UI) to start an automated "court cleanup" task.
  - The robot collects balls scattered within the court area and returns them to a predefined drop-off location.

### 2.2 Functional Goals (Initial Version)

- Detect and localize tennis balls within the court area.
- Navigate safely within the court without colliding with:
  - Net and posts
  - Ball carts / benches
  - Players or bystanders
- Collect balls into an onboard storage bin.
- Return to a designated drop-off/parking area at the end of the mission.

### 2.3 Typical Performance Targets (To Be Refined)

These are target ranges and can be adjusted as the design evolves:

- Ball capacity: approximately **60–100 balls** per run.
- Cleanup cycle: collect **~80 balls** in a single court within a reasonable time window.
- Continuous operation: **multi-hour** runtime on a single battery charge.
- Deployment: transportable by a single person (lift into car trunk, move around by hand).

---

## 3. System Architecture Overview

At a high level, the system is composed of:

1. **Robot Platform**
   - Mid-size outdoor mobile base (differential drive).
   - Ball collection and storage subsystem.
   - Onboard compute, sensors, and power system.

2. **Perception Stack**
   - Vision-based ball detection.
   - Obstacle detection around the robot.

3. **Localization Stack**
   - Fusion of RTK GNSS, visual odometry, wheel encoders, and IMU.
   - Provides a unified pose interface to higher-level modules.

4. **Motion and Task Layer**
   - Motion control (velocity commands to motors).
   - Local path planning and obstacle avoidance.
   - Global task logic for "full court cleanup".

5. **Communication Layer**
   - Communication between the robot and the operator/control UI.
   - Support for both local network and future remote/cloud options.

6. **Operator Console**
   - Web-based UI for:
     - Manual teleoperation
     - Monitoring robot status
     - Starting/stopping automated cleanup tasks

---

## 4. Functional Modules

### 4.1 Perception (Ball and Obstacle Detection)

**Inputs**

- Front-facing RGB camera(s).
- Optional depth or distance sensors (e.g., ultrasonic / ToF) for near-field obstacle detection.

**Responsibilities**

- Detect tennis balls in the camera view.
- Estimate ball positions in a unified coordinate frame on the court.
- Detect large obstacles such as:
  - Net and posts
  - Benches / ball carts
  - Human presence

**Key Outputs**

- A list of detected balls with estimated position and confidence scores.
- A representation of obstacles for local planning (e.g., costmap or obstacle list).

---

### 4.2 Localization and Mapping

**Inputs**

- RTK GNSS (for absolute outdoor positioning when available).
- Wheel encoders and IMU (odometry).
- Visual odometry / SLAM (optional in early stages, more important later).

**Responsibilities**

- Estimate the robot pose (position + orientation) in a consistent court-level frame.
- Fuse multiple sensor sources (GNSS, odometry, IMU, visual odometry) when available.
- Expose a **unified localization interface** to downstream modules (path planner, task executor, UI).

**Key Output**

- `RobotPose` structure (see Localization API in a separate document), including:
  - Frame ID
  - Timestamp
  - Position (x, y, z)
  - Orientation (roll, pitch, yaw)
  - Optional covariance and source tag

---

### 4.3 Motion Control

**Responsibilities**

- Accept high-level velocity commands:
  - Linear velocity `v`
  - Angular velocity `ω`
- Convert these into left/right wheel commands for a differential drive base.
- Provide:
  - Smooth, stable motion
  - Emergency stop behavior on command or when a critical fault is detected

**Key Interfaces**

- `set_velocity(v, omega)`
- `stop()`
- `emergency_stop()`

These interfaces are used by both manual control and autonomous planners.

---

### 4.4 Path Planning and Task Logic

#### Local Path Planning

**Inputs**

- Current `RobotPose`
- Target point (e.g., ball location, drop-off point)
- Obstacle information around the robot

**Responsibilities**

- Compute a feasible path from current pose to target pose.
- Perform collision-free motion using local obstacle information.
- Provide near-term waypoints or direct velocity commands to Motion Control.

#### Global Task Logic – “Full Court Cleanup”

**Inputs**

- List of ball detections (with positions and confidence)
- Court boundaries and restricted zones
- Robot state (pose, battery status, storage capacity)

**Responsibilities**

- Maintain a list of balls to collect.
- Schedule an efficient visiting order (e.g., nearest-ball-first, or zoned scanning).
- Manage state transitions:
  - Idle → Navigate to ball → Collect → Repeat
  - Storage full / low battery → Return to drop-off/home position.
- Detect task completion conditions:
  - No more balls detected
  - Maximum time exceeded
  - Manual stop

---

### 4.5 Communication Layer

**Responsibilities**

- Provide a communication channel between robot and operator UI.
- Support:
  - Telemetry streaming (pose, battery, task status).
  - Video streaming from onboard cameras.
  - Command reception (manual control and high-level tasks).

**Connectivity Modes**

- Local network (Wi-Fi) as the primary mode for early versions.
- Architecture keeps the protocol clear enough for future:
  - Cloud-based or remote control via VPN / custom gateway.

---

### 4.6 Operator Console (Web UI)

**Core Functions**

- Display robot status:
  - Online/offline
  - Battery level
  - Current mode (idle, manual, auto cleanup)
  - Current pose (visualized on a simple 2D court map)
- Provide control options:
  - Manual teleoperation (forward/backward/turn).
  - Start/stop the automatic "court cleanup" task.
  - Send a "return to drop-off/home" command.
- Present video feed from the robot camera for situational awareness.

The UI is designed with **multi-robot support in mind**, even if initially only one robot is connected. APIs should include a `robot_id` or equivalent identifier.

---

## 5. Development Phases and Milestones (High Level)

### Phase 1 – Basic Mobile Platform

- Build or adapt a mid-size differential drive base.
- Implement low-level motor control and teleoperation.
- Integrate basic sensors: camera, encoders, IMU.
- Achieve stable manual driving on a court with live video streaming.

### Phase 2 – Ball Detection and Point-to-Point Navigation

- Implement tennis ball detection in camera images.
- Calibrate camera to estimate approximate ball positions on the ground.
- Implement localization and simple point-to-point navigation:
  - Drive from current position to a selected ball.
- Demonstrate:
  - “Drive to one ball and stop in front of it” reliably.

### Phase 3 – Basic Autonomous Collection Loop

- Maintain a list of detected balls and their estimated positions.
- Implement a simple task loop:
  - Select next ball → navigate → collect → repeat.
- Implement a basic storage subsystem for collected balls.
- Demonstrate:
  - Collecting multiple balls in a row on a single court without manual intervention.

### Phase 4 – Full Court Cleanup Scenario

- Include court boundary and no-go zones.
- Improve path planning to cover the whole court efficiently.
- Add logic for:
  - Handling low battery or full storage (returning to drop-off).
  - Handling perception failures and edge cases.
- Demonstrate:
  - A full “court cleanup” run on a realistic number of balls.

Further phases can extend this roadmap (multi-court operation, multi-robot coordination, mapping improvements, etc.), but the primary near-term focus is to achieve a robust single-robot tennis ball collection scenario.
