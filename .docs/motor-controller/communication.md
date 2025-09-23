# Telemetry & UART Bridge

The Raspberry Pi Pico publishes compact telemetry frames while accepting velocity commands and PID tuning updates over UART. This document consolidates the workflow for piping that data into developer tools, ROS 2, and the mission dashboard.

## Frame Definitions

### Telemetry (`0xAA55`)
```
<start=0xAA55><len=34><seq><timestamp_ms><timeout_flag>
<left_rpm><right_rpm><battery_mv>
<ax_mg><ay_mg><az_mg>
<gx_ddeci><gy_ddeci><gz_ddeci>
<v_cmd_mmps><w_cmd_mrad><crc16>
```
- Multibyte fields are little-endian.
- Accel is reported in milli-g and gyro in deci-deg/s to keep integers.
- `timeout_flag` toggles when no fresh `cmd_vel` has been received.

### Command (`0xCC33`)
```
<start=0xCC33><len=11><seq><v_cmd_mmps><w_cmd_mrad><crc16>
```
The payload mirrors ROS `geometry_msgs/Twist` (linear.x, angular.z). Tooling that wants to push PID tuning values can extend the frame by appending additional int16 fields; the checksum still covers all bytes.

## Raspberry Pi 5 Bridge

`robot/Raspberry-Pi-5/ros-bridge/pico_bridge.py` wraps the UART link in ROS 2 publishers and subscribers:
- Subscribes to `/cmd_vel` and serializes Twist messages into the command frame shown above.
- Publishes `left_wheel_rpm`, `right_wheel_rpm`, `sensor_msgs/Imu`, and `BatteryState` from the telemetry stream.
- Exposes parameters for serial port selection, baud rate, watchdog warnings, and optional raw-byte logging.

Recommended workflow:
1. Launch the bridge alongside Nav2 so autonomy can drive the base with zero firmware changes.
2. Record telemetry with `ros2 bag record` for offline analysis; the numeric fields match the binary payload.
3. Enable the `rx_hex` parameter when reverse-engineering new firmware fields.

## PC Dashboard for PID Tuning

For microcontroller bring-up without ROS, the legacy PyQt dashboard (`robot/diff_drive_motor_controller/pc_uart_dashboard.py`) remains useful:
- Plots left/right RPM, PID terms, and loop times in real time using PyQtGraph.
- Allows streaming PID gains and target RPMs back to the Pico via the command frame.
- Handles framing, checksum validation, and base timestamping so you can focus on tuning.

## Dashboard WebSocket Adapter

The FastAPI backend (`dashboard/backend/app/server.py`) listens for WebSocket dashboard commands and forwards them to either the simulator or real robot. When pointed at real hardware, the recommended chain is:
```
Dashboard UI → WebSocket `/ws` → FastAPI → ROS 2 rosbridge (optional) → `/cmd_vel`
```
If you skip rosbridge and target the Pico directly, reuse the same command frame described above. Keep the interval at or below 10 Hz to satisfy the watchdog.

## Test Procedure
- **Loopback Test:** Short the Pico’s TX/RX pins and ensure the bridge rejects malformed frames (checksum fails).
- **Noise Rejection:** With motors powered, confirm the checksum discards partial frames and the ROS logs show warning counts instead of crashing.
- **Stop Condition:** Interrupt the dashboard command stream; verify `timeout_flag` rises and the ROS 2 bridge publishes zero velocities.

## Related Material
- Electrical pinouts and controller wiring: [`low-level-control.md`](low-level-control.md)
- Overall communication schema across subsystems: `../Communication_stack_schema.md`
