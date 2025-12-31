# Pico to Raspberry Pi Communication Specification

## Frame Format
All messages use the same frame structure:
- START1: 0xAA
- START2: 0x55
- MSG_ID: 1 byte message identifier
- LEN_H: High byte of payload length (big-endian)
- LEN_L: Low byte of payload length (big-endian)
- PAYLOAD: Variable length data
- CHECKSUM: 1 byte checksum (sum of MSG_ID, LEN_H, LEN_L, PAYLOAD bytes & 0xFF)

## Messages

### Velocity Command (Pi to Pico)
- MSG_ID: 0x01
- Payload: 2 floats (big-endian)
  - linear_mps: Linear velocity in m/s
  - angular_rps: Angular velocity in rad/s

### Telemetry (Pico to Pi)
- MSG_ID: 0x02
- Payload: 11 floats (big-endian)
  - left_target_rpm: Target RPM for left wheel
  - right_target_rpm: Target RPM for right wheel
  - left_actual_rpm: Actual RPM for left wheel
  - right_actual_rpm: Actual RPM for right wheel
  - battery_voltage: Battery voltage in volts
  - accel_x: Accelerometer X in g's
  - accel_y: Accelerometer Y in g's
  - accel_z: Accelerometer Z in g's
  - gyro_x: Gyroscope X in deg/s
  - gyro_y: Gyroscope Y in deg/s
  - gyro_z: Gyroscope Z in deg/s

## Notes
- All floats are 32-bit IEEE 754 in big-endian byte order.
- Checksum is the lower 8 bits of the sum of MSG_ID, LEN_H, LEN_L, and all payload bytes.
- Pico listens for velocity commands and periodically sends telemetry.