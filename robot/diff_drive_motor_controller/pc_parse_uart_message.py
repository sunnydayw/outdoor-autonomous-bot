import serial
import struct
import time

# Configure the serial port (adjust 'COM3' or '/dev/ttyUSB0' as needed)
port = '/dev/tty.usbserial-A505VA57'
ser = serial.Serial(port, baudrate=115200, timeout=1)

# Updated message format based on the new structure:
#   uint16: Start Delimiter
#   uint8:  Message Length
#   uint16: Message Counter
#   uint32: Timestamp (ms)
#   uint8:  Timeout Flag
#   7 x int16: Left Motor diagnostics
#   7 x int16: Right Motor diagnostics
#   uint16: Checksum
fmt_without_checksum = '<HBHIB' + '7h' + '7h'
fmt_checksum = '<H'
expected_size = struct.calcsize(fmt_without_checksum) + struct.calcsize(fmt_checksum)
print("Expected message size:", expected_size)

def compute_checksum(data):
    """Compute simple additive checksum over data."""
    return sum(data) & 0xFFFF

while True:
    # Read one full message from the serial port.
    data = ser.read(expected_size)
    if len(data) < expected_size:
        continue  # Wait until a full message is received.

    # Unpack the message; the final field is the checksum.
    unpacked = struct.unpack(fmt_without_checksum + 'H', data)
    
    header = unpacked[0]
    msg_length = unpacked[1]
    msg_counter = unpacked[2]
    timestamp = unpacked[3]
    timeout_flag = unpacked[4]

    # Left motor diagnostics: 7 values (indices 5 to 11).
    left_motor_values = unpacked[5:12]
    # Right motor diagnostics: 7 values (indices 12 to 18).
    right_motor_values = unpacked[12:19]
    received_checksum = unpacked[19]

    # Validate the header (should be 0xAA55).
    if header != 0xAA55:
        print("Invalid header:", header)
        continue

    # Recalculate checksum over all bytes except the checksum field itself.
    checksum_calc = compute_checksum(data[:-2])
    if checksum_calc != received_checksum:
        print("Checksum mismatch: calculated", checksum_calc, "received", received_checksum)
        continue

    # Print out the diagnostics.
    print("Msg Counter:", msg_counter, "Timestamp:", timestamp)
    print("Timeout Flag:", timeout_flag)
    print("Left Motor:")
    print("  Target RPM:", left_motor_values[0])
    print("  Current RPM:", left_motor_values[1])
    print("  P Term:", left_motor_values[2])
    print("  I Term:", left_motor_values[3])
    print("  D Term:", left_motor_values[4])
    print("  Output:", left_motor_values[5])
    print("  Loop Time:", left_motor_values[6])
    print("Right Motor:")
    print("  Target RPM:", right_motor_values[0])
    print("  Current RPM:", right_motor_values[1])
    print("  P Term:", right_motor_values[2])
    print("  I Term:", right_motor_values[3])
    print("  D Term:", right_motor_values[4])
    print("  Output:", right_motor_values[5])
    print("  Loop Time:", right_motor_values[6])
    print("-" * 40)
    
    # Optional delay for display clarity.
    time.sleep(0.02)
