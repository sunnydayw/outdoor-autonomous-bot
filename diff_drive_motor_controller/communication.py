import time
import struct
from machine import UART, Pin

class RobotTelemetry:
    def __init__(self, left_motor, right_motor, controller):
        # Initialize UART on UART1 with the given TX/RX pins.
        self.uart = UART(1, baudrate=115200, tx=Pin(8), rx=Pin(9))
        self.left_motor = left_motor
        self.right_motor = right_motor
        self.controller = controller
        self.msg_counter = 0
        self.start_delimiter = 0xAA55
        self.msg_length = 64  # Updated total message length in bytes

    def compute_checksum(self, data):
        """Simple additive checksum: sum all bytes modulo 0x10000."""
        return sum(data) & 0xFFFF

    def send_message(self):
        """
        Assemble and send the telemetry message over UART.
        Message Format:
          uint16: Start Delimiter
          uint8:  Message Length (64)
          uint16: Message Counter
          uint32: Timestamp (ms)
          uint8:  Timeout Flag
          5 x float: Left motor diagnostics (target_rpm, current_rpm, p_term, i_term, d_term)
          3 x int16: Left motor diagnostics (output, motor_loop_time, encoder_loop_time)
          5 x float: Right motor diagnostics (target_rpm, current_rpm, p_term, i_term, d_term)
          3 x int16: Right motor diagnostics (output, motor_loop_time, encoder_loop_time)
          uint16: Checksum
        """
        timestamp = time.ticks_ms()
        self.msg_counter = (self.msg_counter + 1) & 0xFFFF

        # Get controller diagnostics (for timeout flag)
        ctrl_diag = self.controller.get_diagnostics()
        timeout_flag = 1 if ctrl_diag.get("timeout", False) else 0

        # Get motor diagnostics (now with float precision for RPM and PID values)
        left_diag = self.left_motor.get_diagnostics()
        right_diag = self.right_motor.get_diagnostics()

        left_vals = (
            float(left_diag["target_rpm"]),
            float(left_diag["current_rpm"]),
            float(left_diag["p_term"]),
            float(left_diag["i_term"]),
            float(left_diag["d_term"]),
            int(left_diag["output"]),
            int(left_diag["motor_loop_time"]),
            int(left_diag["encoder_loop_time"])

        )
        right_vals = (
            float(right_diag["target_rpm"]),
            float(right_diag["current_rpm"]),
            float(right_diag["p_term"]),
            float(right_diag["i_term"]),
            float(right_diag["d_term"]),
            int(right_diag["output"]),
            int(right_diag["motor_loop_time"]),
            int(right_diag["encoder_loop_time"])
        )

        # Build the format string:
        # '<' for little-endian
        # H: start delimiter; B: message length; H: message counter; I: timestamp; B: timeout flag;
        # 5f2h: left motor diagnostics; 5f2h: right motor diagnostics.
        fmt_without_checksum = '<HBHIB' + '5f3h' + '5f3h'
        packed = struct.pack(fmt_without_checksum,
                             self.start_delimiter,
                             self.msg_length,
                             self.msg_counter,
                             timestamp,
                             timeout_flag,
                             *left_vals,
                             *right_vals)
        checksum = self.compute_checksum(packed)
        packed_checksum = struct.pack('<H', checksum)
        message = packed + packed_checksum

        self.uart.write(message)
        
    def receive_control_message(self):
        """
        Check the UART for an incoming control message, parse it, and print its contents.
        Control Message Format (23 bytes total):
        uint16: Start Delimiter (0xCC33)
        uint8:  Message Length (23)
        uint16: Message Counter
        int16: Left Target RPM
        int16: Right Target RPM
        int16: Left P, Left I, Left D
        int16: Right P, Right I, Right D
        uint16: Checksum
        """
        fmt = '<HBH8h'
        ctrl_msg_size = struct.calcsize(fmt) + 2  # 2 bytes for checksum.
        if self.uart.any():
            data = self.uart.read(ctrl_msg_size)
            if data and len(data) == ctrl_msg_size:
                try:
                    unpacked = struct.unpack(fmt + 'H', data)
                except Exception as e:
                    print("Control message unpack error:", e)
                    return
                if unpacked[0] != 0xCC33:
                    print("Invalid control message delimiter:", hex(unpacked[0]))
                    return
                calc_checksum = sum(data[:-2]) & 0xFFFF
                if calc_checksum != unpacked[-1]:
                    print("Control message checksum error: calc", calc_checksum, "recv", unpacked[-1])
                    return
                print("Received Control Message:")
                print("Message Counter:", unpacked[2])
                print("Left Target RPM:", unpacked[3])
                print("Right Target RPM:", unpacked[4])
                print("Left P:", unpacked[5])
                print("Left I:", unpacked[6])
                print("Left D:", unpacked[7])
                print("Right P:", unpacked[8])
                print("Right I:", unpacked[9])
                print("Right D:", unpacked[10])
            else:
                print("Incomplete control message")


'''
Below is one approach to designing an efficient binary message format for communicating from a Pico (running MicroPython) to a PC over UART. 

In this design the Pico sends a fixed‑length, binary‐packed message (40 bytes total) over UART
We use a: 
Start Delimiter: 2 bytes (uint16) A unique header (0xAA55) to mark the beginning of each frame.
Message Length: 1 byte (uint8) A field for the overall message length
Message Counter: 2 bytes (uint16) a message counter for tracking lost/dropped messages
Timestamp: 4 bytes (uint32)
Timeout Flag: 1 byte (uint8)
Left Motor Diagnostics: 7 × 2 bytes = 14 bytes (7 int16)
Right Motor Diagnostics: 7 × 2 bytes = 14 bytes (7 int16)
Checksum: 2 bytes (uint16) The checksum function simply sums the bytes modulo 0x10000. This method is both simple and fast enough for a Pico board.
Total: 2 + 1 + 2 + 4 + 1 + 14 + 14 + 2 = 40 bytes

fmt_without_checksum = '<HBHIB7h7h'
This string tells the struct packer:

<: Specifies little-endian byte order. This means that multi-byte numbers are stored with the least significant byte first.
H: Represents an unsigned short (2 bytes). This is used for the start delimiter (e.g., 0xAA55).
B: unsigned char (1 byte) for the message length
H: unsigned short (2 bytes) for the message counter
I: unsigned int (4 bytes) for the timestamp
B: unsigned char (1 byte) for the timeout flag
7h: seven signed shorts (each 2 bytes) for the left motor diagnostics
7h: seven signed shorts for the right motor diagnostics

Given the baud rate of 115200 bits per second and the 40-byte message:
Transmission Size: 40 bytes * 10 bits/byte = 400 bits per message (including start, stop, and parity bits).
Max Theoretical Rate: 115200 / 400 ≈ 288 messages per second (i.e. about 4 ms per message) if the channel were fully dedicated.

A typical update rate of 20–50 ms per message (20–50 Hz) strikes a good balance between timely updates and ensuring that the UART is not overloaded. 

Parsing (Python on PC Side)
Synchronization: Look for the fixed start delimiter in the incoming byte stream to find the beginning of a message.
Unpacking: Once we have received 4 bytes, use Python’s struct.unpack() with the corresponding format string (e.g., using little-endian format: '<HBHIB7h7h<H' where the ellipsis covers both motor data blocks and the checksum).
Validation: Check the checksum to ensure data integrity before processing the fields.

'''