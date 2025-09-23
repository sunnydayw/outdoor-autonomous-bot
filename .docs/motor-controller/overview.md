# Differential Drive Motor Controller

This document captures the Raspberry Pi Pico 2 W firmware that closes the loop on the hub motors and exposes a ROS-style interface to the rest of the robot. It replaces the scattered notes that used to live inside `robot/diff_drive_motor_controller/`.

## Responsibilities
- Convert high-level `cmd_vel` requests into synchronized wheel RPM targets.
- Regulate each wheel with a PID+feed-forward controller and slew limiting so speed changes stay smooth.
- Enforce a command timeout watchdog that halts the motors if upstream nodes go silent.
- Stream wheel speeds, IMU samples, battery voltage, and diagnostic flags back to the Raspberry Pi 5.

## Firmware Modules
| File | Purpose |
| --- | --- |
| `config.py` | Central tuning hub (wheel geometry, PID gains, PWM bounds, safety timeouts). |
| `encoder.py` | Interrupt-driven tick counting and RPM estimation. |
| `motor.py` | Open- and closed-loop motor commands with acceleration limiting. |
| `diff_drive_controller.py` | Kinematic solver that maps `cmd_vel` → wheel set-points and monitors the watchdog. |
| `main.py` | Bootstraps peripherals, spins the asyncio scheduler, and glues command ingest with telemetry publishing. |
| `robot_telemetry.py` | Formatting helpers for periodic telemetry frames sent over UART. |

### Runtime Diagram
1. `cmd_vel` arrives over UART or simulated publisher.
2. `diff_drive_controller` solves for left/right RPM targets.
3. `motor` applies PID to reach the target while honoring slew limits.
4. `encoder` updates measured RPM each control tick.
5. `robot_telemetry` packages measurements + IMU into the binary frame described in _Telemetry & UART Bridge_.

## Safety & Fallbacks
- **Command Watchdog:** configurable timeout (default 0.5 s). If exceeded, targets go to zero and a timeout bit is set in telemetry.
- **Soft Limits:** Wheel RPM clamps and PWM ceilings protect the scooter controller from overcurrent spikes.
- **Manual Override:** RC or direct UART commands can inject velocity updates, bypassing higher-level control for bring-up.

## Extending the Controller
- Add current-sense feedback once the power stage supports it; extend `robot_telemetry` to opportunistically include current draw.
- Integrate closed-loop braking by mapping ROS stop commands to the JYQD brake pin (documented in `low-level-control.md`).
- When migrating to ROS 2, point the UART bridge (see below) at the Nav2 velocity topic so autonomy can take over without firmware changes.

## Development Checklist
- Tune PID gains against the simulator (`simulation/simulation_server.py`) before touching hardware.
- Validate watchdog behaviour by pausing command input and checking that the timeout flag appears in telemetry.
- Record encoder counts vs. ground truth distance to calibrate wheel radius in `config.py`.
- Run the `pc_uart_dashboard.py` utility for a quick look at raw telemetry when ROS is unavailable.

## Related Documents
- [_Telemetry & UART Bridge_](communication.md) for message formats and ROS integration.
- [_Hub Motor Low-Level Control_](low-level-control.md) for pinouts and electrical wiring.
- System-level architecture: `../Autonomous_Robot_System_Architecture_Design.md`.
