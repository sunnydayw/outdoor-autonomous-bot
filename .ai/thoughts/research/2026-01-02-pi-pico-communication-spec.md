---
date: 2026-01-02T20:28:41-0500
researcher: Qingtian Chen
git_commit: 7ca0a6236a903799e13c76f2747bdb9d2d6fbf13
branch: main
repository: outdoor-autonomous-bot
topic: "Pi <-> Pico UART communication spec and current architecture"
tags: [research, codebase, pi3-rover-1, raspberry-pi-pico-2, uart, telemetry, communication]
status: complete
last_updated: 2026-01-02
last_updated_by: Qingtian Chen
---

# Research: Pi <-> Pico UART communication spec and current architecture

**Date**: 2026-01-02T20:28:41-0500
**Researcher**: Qingtian Chen
**Git Commit**: 7ca0a6236a903799e13c76f2747bdb9d2d6fbf13
**Branch**: main
**Repository**: outdoor-autonomous-bot

## Research Question
I want you to research about the communication spec between pi and pico. I want you to document the current code structure, high level architure to help me update and improve the code. I also want a detailed docucmentation use as the spec for communication. in the folder pi3-rover-1, we have code for sending drive command to the pico and receiving telemerty information from the pico the file robot/Raspberry-Pi-Pico-2/pico_uart_comm.py lays out for how pico sending and receiving data from pi over uart there is a draft document of robot/Raspberry-Pi-Pico-2/communication_spec.md, but the information accuarcy need to be verify.

## Summary
The current Pi <-> Pico UART link is implemented as a framed binary protocol with start bytes 0xAA 0x55, a 1-byte message ID, a 2-byte payload length, a payload of big-endian float32 values, and a 1-byte additive checksum. The Pi side (pi3-rover-1) sends velocity commands (msg_id 0x01, 2 floats) and receives telemetry (msg_id 0x02, 11 floats) through the FastAPI backend's UART bridge and updates the shared CommandState. The Pico side (robot/Raspberry-Pi-Pico-2) parses velocity commands in the main loop and sends telemetry at a 10 Hz cadence, sourcing wheel targets, measured RPM, battery voltage, and IMU values. The draft communication_spec.md describes the same frame structure and field order that the code implements.

## Detailed Findings

### Pi-side UART bridge and backend (pi3-rover-1)
- The UART bridge defines the frame layout (start bytes, msg_id, length, payload, checksum) and constants for msg IDs and payload formats (velocity and telemetry) in `pi3-rover-1/dashboard/backend/uart_bridge.py:18-37`.
- Velocity frames are built with two big-endian float32 values and sent on changes or a heartbeat interval; telemetry is parsed from the RX buffer and unpacked into CommandState in `pi3-rover-1/dashboard/backend/uart_bridge.py:61-199`.
- The backend starts a background UART control loop thread at a configurable rate (default 50 Hz) and shares a single CommandState instance between HTTP handlers and the UART loop in `pi3-rover-1/dashboard/backend/main.py:18-73`.
- Teleop commands arrive via `/cmd_vel` and update CommandState, while telemetry is exposed over `/telemetry` and `/ws/telemetry` in `pi3-rover-1/dashboard/backend/api.py:96-201`.
- CommandState stores the latest telemetry fields (left/right target RPM, actual RPM, battery voltage, accel, gyro) and exposes snapshot accessors in `pi3-rover-1/dashboard/backend/command_state.py:17-199`.
- The browser teleop UI posts `/cmd_vel` at a fixed interval (SEND_INTERVAL_MS) in `pi3-rover-1/dashboard/web/teleop.js:14-345`.
- A simple UART read script shows the same framing (start bytes, msg_id, length, payload, checksum) in `pi3-rover-1/dashboard/test/pi_recv_from_pico.py:4-28`.

### Pico-side UART handling and telemetry (robot/Raspberry-Pi-Pico-2)
- The Pico UART helper defines the same frame layout and uses big-endian float32 payloads for velocity and telemetry in `robot/Raspberry-Pi-Pico-2/pico_uart_comm.py:1-134`.
- `PicoUARTComm.poll()` reads bytes, parses a velocity frame, and calls `controller.set_cmd_vel(linear, angular)` on successful decode in `robot/Raspberry-Pi-Pico-2/pico_uart_comm.py:36-54`.
- `PicoUARTComm.send_telemetry()` packs 11 float32 values (targets, actuals, battery, accel, gyro) and sends a framed telemetry message in `robot/Raspberry-Pi-Pico-2/pico_uart_comm.py:55-68`.
- The main loop sends telemetry every 100 ms and polls UART for commands in `robot/Raspberry-Pi-Pico-2/main.py:28-246`.
- Telemetry values are sourced from diff-drive diagnostics, encoder RPMs, battery ADC, and IMU readings in `robot/Raspberry-Pi-Pico-2/main.py:192-214`.
- UART pins and baud rate are defined in `robot/Raspberry-Pi-Pico-2/config.py:50-54`, and battery divider parameters are defined in `robot/Raspberry-Pi-Pico-2/config.py:76-81`.
- The DriveSystem exposes `set_cmd_vel()` and forwards to the diff-drive controller in `robot/Raspberry-Pi-Pico-2/drive_system.py:95-103`.
- The UART-only test harness references a `PicoVelocityReceiver` in `robot/Raspberry-Pi-Pico-2/test_main.py:10-49`.

### Current UART Communication Spec (derived from code)

#### Frame Format (Pi <-> Pico)
- Start bytes: `0xAA 0x55` (`pi3-rover-1/dashboard/backend/uart_bridge.py:22-27`, `robot/Raspberry-Pi-Pico-2/pico_uart_comm.py:3-10`).
- Message ID: 1 byte.
- Length: 2 bytes, big-endian (LEN_H, LEN_L).
- Payload: variable length.
- Checksum: 1 byte, `(msg_id + len_h + len_l + sum(payload_bytes)) & 0xFF` (`pi3-rover-1/dashboard/backend/uart_bridge.py:117-128`, `robot/Raspberry-Pi-Pico-2/pico_uart_comm.py:59-66`).

#### Message: Velocity Command (Pi -> Pico)
- `MSG_ID = 0x01` (`pi3-rover-1/dashboard/backend/uart_bridge.py:32-34`, `robot/Raspberry-Pi-Pico-2/pico_uart_comm.py:21-26`).
- Payload length: 8 bytes (2 x float32).
- Payload (big-endian float32, in order):
  1. `linear_mps`
  2. `angular_rps`
- Packed with `!ff` (`pi3-rover-1/dashboard/backend/uart_bridge.py:33-34`, `robot/Raspberry-Pi-Pico-2/pico_uart_comm.py:24-26`).

#### Message: Telemetry (Pico -> Pi)
- `MSG_ID = 0x02` (`pi3-rover-1/dashboard/backend/uart_bridge.py:35-37`, `robot/Raspberry-Pi-Pico-2/pico_uart_comm.py:22-28`).
- Payload length: 44 bytes (11 x float32).
- Payload (big-endian float32, in order):
  1. `left_target_rpm`
  2. `right_target_rpm`
  3. `left_actual_rpm`
  4. `right_actual_rpm`
  5. `battery_voltage`
  6. `accel_x`
  7. `accel_y`
  8. `accel_z`
  9. `gyro_x`
  10. `gyro_y`
  11. `gyro_z`
- Packed with `!fffffffffff` (`pi3-rover-1/dashboard/backend/uart_bridge.py:35-37`, `robot/Raspberry-Pi-Pico-2/pico_uart_comm.py:27-28`).

#### Frame Lengths
- Total frame length = 2 (start) + 1 (msg_id) + 2 (length) + payload_len + 1 (checksum).
- Velocity frame length = 2 + 1 + 2 + 8 + 1 = 14 bytes.
- Telemetry frame length = 2 + 1 + 2 + 44 + 1 = 50 bytes.

### Draft spec alignment (communication_spec.md)
- The draft spec describes the same frame format, msg IDs, and payload fields used by the code (`robot/Raspberry-Pi-Pico-2/communication_spec.md:3-39`).

### Other UART protocol definitions in the repo (separate from pi3-rover-1 / Raspberry-Pi-Pico-2)
- `robot/Raspberry-Pi-Pico-2/proto.py` defines a different header+payload format with sequence numbers and timestamps for velocity and feedback messages (`robot/Raspberry-Pi-Pico-2/proto.py:19-211`).
- `robot/diff_drive_motor_controller/communication.py` defines a 64-byte little-endian telemetry packet (start 0xAA55) and a 23-byte control packet (start 0xCC33) with a 16-bit checksum (`robot/diff_drive_motor_controller/communication.py:5-129`).
- `robot/Raspberry-Pi-5/ros-bridge/pico_bridge.py` defines a different little-endian framing for telemetry and commands (0xAA55 telemetry start, 0xCC33 command start) with fixed lengths (`robot/Raspberry-Pi-5/ros-bridge/pico_bridge.py:9-115`).

## Code References
- `pi3-rover-1/dashboard/backend/uart_bridge.py:18` - UART frame layout, msg IDs, and payload formats.
- `pi3-rover-1/dashboard/backend/uart_bridge.py:61` - Velocity send cadence and telemetry parsing loop.
- `pi3-rover-1/dashboard/backend/api.py:96` - `/cmd_vel`, `/telemetry`, and `/ws/telemetry` endpoints.
- `pi3-rover-1/dashboard/backend/command_state.py:17` - Telemetry and command state storage.
- `pi3-rover-1/dashboard/backend/main.py:18` - UART control loop thread and FastAPI server entry.
- `pi3-rover-1/dashboard/web/teleop.js:14` - Teleop send interval and `/cmd_vel` client logic.
- `pi3-rover-1/dashboard/test/pi_recv_from_pico.py:4` - UART frame parser used for debugging.
- `robot/Raspberry-Pi-Pico-2/pico_uart_comm.py:1` - Pico UART framing, parsing, and telemetry send.
- `robot/Raspberry-Pi-Pico-2/main.py:192` - Telemetry field sourcing and send cadence.
- `robot/Raspberry-Pi-Pico-2/config.py:50` - UART pin/baud configuration and battery divider.
- `robot/Raspberry-Pi-Pico-2/communication_spec.md:3` - Draft spec description.

## Architecture Documentation
The Pi3 backend (`pi3-rover-1/dashboard/backend/main.py`) runs a FastAPI server and a background UART loop. The web UI posts velocity commands to `/cmd_vel` (`pi3-rover-1/dashboard/web/teleop.js:132-345`), which updates CommandState (`pi3-rover-1/dashboard/backend/api.py:96-106`). The UART loop pulls the latest command and sends it to the Pico via `PiUartBridge` (`pi3-rover-1/dashboard/backend/uart_bridge.py:61-137`). On the Pico, `PicoUARTComm.poll()` decodes the velocity payload and forwards it to `DriveSystem.set_cmd_vel()` (`robot/Raspberry-Pi-Pico-2/pico_uart_comm.py:36-54`, `robot/Raspberry-Pi-Pico-2/drive_system.py:95-103`). The Pico main loop sends telemetry frames at 10 Hz (`robot/Raspberry-Pi-Pico-2/main.py:193-219`), which the Pi UART bridge parses and stores in CommandState (`pi3-rover-1/dashboard/backend/uart_bridge.py:158-199`). The backend exposes telemetry via REST and a WebSocket (`pi3-rover-1/dashboard/backend/api.py:152-201`) for the web UI.

## Historical Context (from thoughts/)
- `.ai/thoughts/tickets/eng-0001.md` - Notes UI changes for telemetry display and battery percentage mapping.
- `.ai/thoughts/tickets/eng-0002.md` - Notes telemetry display behavior and UART warnings with payload length 8 on reconnect.
- `.ai/thoughts/plans/2026-01-01-ENG-0001-teleop-telemetry-ui.md` - Plan for grouping telemetry UI and battery percentage mapping (9.0V to 12.5V).

## Related Research
- `.ai/thoughts/research/2026-01-02-old-code-camera-streaming.md` - Camera streaming research (different subsystem).

## Open Questions
- Which component is intended to use the header/sequence-based payloads defined in `robot/Raspberry-Pi-Pico-2/proto.py`?
- What producer emits the payload length 8 frames noted in `.ai/thoughts/tickets/eng-0002.md`?
- Where is `PicoVelocityReceiver` defined for `robot/Raspberry-Pi-Pico-2/test_main.py`?
