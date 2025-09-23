# Outdoor Autonomous Bot

An outdoor-ready differential drive platform for semi-autonomous cleaning and grounds maintenance. The project explores an end-to-end stack: rugged hardware, low-level motion control, onboard perception, and a mission control dashboard for human-in-the-loop supervision.

## Vision
- Reduce repetitive maintenance tasks such as litter pickup, light street sweeping, or lawn prep with a reliable robotic platform.
- Pair approachable hardware with an open software stack so new capabilities (mapping, perception, manipulation) can be layered in iteratively.
- Keep safety in focus—manual override, telemetry visibility, and controlled autonomy are first-class requirements.

## Current Focus
- Bring-up of the differential drive base, including motor PID control and RC override.
- ROS 2 experimentation on Raspberry Pi 5 for inter-process messaging and future navigation stack integration.
- Simulation pipeline that produces realistic telemetry for UI development and autonomy prototyping.
- Responsive HTML/roslib.js teleoperation dashboard for quick command and status checks.

## System Architecture
| Layer | Platform | Responsibilities | Status |
| --- | --- | --- | --- |
| **Actuation & Sensing** | Raspberry Pi Pico 2 W | Motor drivers, encoders, IMU sampling, `cmd_vel` watchdog | Firmware in `robot/Raspberry-Pi-Pico-2` (alpha)
| **Edge Compute** | Raspberry Pi 5 (8 GB) | ROS 2 nodes, perception workloads, mission execution | ROS workspace scaffolded in `robot/Raspberry-Pi-5/ros-workspace`
| **Mission Control** | Base station (laptop/tablet) | Telemetry monitoring, teleop commands, mission authoring | FastAPI + static dashboard in `dashboard`
| **Simulation** | Local container | Publishes synthetic telemetry, accepts commands for rapid iteration | `simulation` service consumable via Docker Compose

**Data Flow**
- Low-level sensors and motor feedback stream into the Pico controller, which enforces failsafes and reports odometry.
- High-level behaviors on the Pi 5 fuse local sensors with ROS 2 topics, then publish motion commands back to the Pico (`/cmd_vel`).
- Telemetry (pose, velocity, system status) is exposed over WebSockets; the FastAPI bridge feeds both the mission dashboard and the simulation loop.
- Operators interact through the dashboard to send manual twists, review health metrics, and in the future, manage waypoint queues and autonomy state.

## Hardware Snapshot
| Subsystem | Components | Notes |
| --- | --- | --- |
| Mobility | 10" hub motors, custom mounts, swivel caster | Tuned for outdoor traction and payload headroom |
| Power | Milwaukee M18 battery + XT60 breakout | Swap-friendly packs, common tooling ecosystem |
| Compute | Raspberry Pi 5 (8 GB), Raspberry Pi Pico 2 W | Separation of real-time motor control vs. high-level planning |
| Control Electronics | Scooter motor controller, RC receiver | Budget-friendly start; planned upgrades for bi-directional feedback |
| Sensors (planned) | GPS, IMU, cameras, optional lidar | Selected with mapping and trash detection use cases in mind |

_Detailed BOM tracking lives in the mechanical CAD notes and will migrate into dedicated docs as components are finalized._

## Software Stack Overview
- **Motor & Safety Control** – `robot/Raspberry-Pi-Pico-2` hosts MicroPython firmware: PID-tuned motor drivers, encoder feedback, IMU sampling, and a ROS-style `cmd_vel` interface with timeout protection. Documentation: `.docs/motor-controller/overview.md`.
- **Edge Compute (ROS 2)** – `robot/Raspberry-Pi-5/ros-workspace` contains ROS 2 packages for telemetry publishing, command subscribers, and future navigation nodes. Helper scripts (`deploy-to-pi.sh`, `sync-from-pi.sh`) streamline Pi deployment. The `ros-bridge/pico_bridge.py` utility forwards `/cmd_vel` to the Pico over UART and republishes telemetry into ROS 2.
- **Simulation** – `simulation` provides a lightweight telemetry server so the dashboard and autonomy stack can iterate before hardware is ready. Start via Docker Compose and connect through the FastAPI bridge.
- **Mission Dashboard** – `dashboard` contains the FastAPI backend (`backend/app`) plus the static HTML dashboard (`backend/app/static`) built with roslib.js. The UI supports low-latency teleoperation, adjustable speed limits, and keyboard/mouse control. Additional widgets (maps, video) can be added without rebuilding Streamlit containers.

## Development Workflow
1. **Spin up simulation + dashboard**: `docker compose up --build` starts the telemetry simulator, FastAPI bridge, and serves the dashboard on `http://localhost:8000`.
2. **Deploy firmware**: Flash the Pico code from `robot/Raspberry-Pi-Pico-2` and confirm `cmd_vel` adherence using the dashboard.
3. **Iterate on ROS 2 nodes**: Use the `ros-workspace` packages as a baseline for publishers/subscribers before introducing mapping and navigation tasks. Utility scripts (e.g., `ros-bridge/pico_bridge.py`) help bridge ROS 2 topics to the Pico over UART.

## Repository Layout
- `dashboard/` – FastAPI backend (`backend`) and static mission dashboard assets (`backend/app/static`).
- `docker-compose.yml` – Orchestrates simulation + dashboard stack for local testing.
- `robot/` – Firmware, ROS 2 workspace, and teleop utilities for Raspberry Pi 5 & Pico.
- `simulation/` – Synthetic telemetry generator, rover dynamics, and helper scripts.
- `.docs/` – Documentation index (`.docs/README.md`) and subsystem references.

## Roadmap
1. Integrate ROS 2 navigation stack (Nav2) with wheel odometry + IMU to unlock autonomous waypoint driving.
2. Add mapping sensors (GPS, wheel encoders, stereo/RGB-D camera) and evaluate SLAM approaches for parks and sidewalk environments.
3. Extend telemetry schema to include battery health, fault states, and perception summaries.
4. Layer in perception models for trash/hazard detection and handoff targets to the navigation stack.
5. Explore manipulation attachments (collection bin, arm) once base navigation is stable.

## Reference Documentation
- Differential drive firmware notes: `.docs/motor-controller/overview.md`
- Communication design between Pico and Pi: `.docs/motor-controller/communication.md`
- Additional work-in-progress docs live under `.docs/` for hardware sketches and sensor research.
