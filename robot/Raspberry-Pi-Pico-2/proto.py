# proto.py
#
# Shared protocol definitions for Pi 5 <-> Pico UART link.
# Designed to be compatible with both CPython and MicroPython.
#
# This file defines:
#   - CommandType enum-like class
#   - Header (seq + stamp)
#   - VelocityCommandPayload
#   - DriveFeedbackPayload  (left/right RPM only)
#   - BatteryStatusPayload  (battery voltage only)

import struct
import time


# ------------------- CommandType "enum" -------------------

class CommandType:
    """Enum-like definition for command types.

    Use plain ints so it works on MicroPython as well.
    """
    SET_VELOCITY = 0  # normal velocity command
    STOP         = 1  # smooth stop, decelerate to zero


# ------------------- Header struct -------------------

class Header:
    """
    Reusable header for all messages.

    Fields:
        seq   : uint32 sequence number
        stamp : double (float64) timestamp in seconds
    """
    FMT = "!Id"   # uint32, double (big-endian)
    SIZE = struct.calcsize(FMT)

    def __init__(self, seq=0, stamp=0.0):
        self.seq = seq
        self.stamp = stamp

    @classmethod
    def now(cls, seq):
        """Convenience: create header with current time and given seq."""
        # For MicroPython compatibility, prefer time.ticks_ms() if available
        try:
            stamp = time.ticks_ms() / 1000.0
        except AttributeError:
            stamp = time.time()
        return cls(seq=seq, stamp=stamp)

    @classmethod
    def from_bytes(cls, buf, offset=0):
        """Unpack Header from bytes starting at offset.

        Returns: (Header instance, next_offset)
        """
        (seq, stamp) = struct.unpack_from(cls.FMT, buf, offset)
        return cls(seq, stamp), offset + cls.SIZE

    def to_bytes(self):
        """Pack Header into bytes."""
        return struct.pack(self.FMT, self.seq, self.stamp)


# ------------------- VelocityCommand payload -------------------

class VelocityCommandPayload:
    """
    Payload for VelocityCommand (Pi 5 -> Pico).

    Layout (big-endian):

        Header (seq, stamp)
        uint8   cmd_type           (CommandType)
        float32 v                  (linear m/s)
        float32 omega              (angular rad/s)
        float32 max_linear_accel   (m/s^2)
        float32 max_angular_accel  (rad/s^2)
        uint32  command_id
    """

    BODY_FMT = "BffffI"          # no leading "!", we prepend in pack/unpack
    FMT = Header.FMT + BODY_FMT  # "!IdBffffI"
    SIZE = struct.calcsize("!" + BODY_FMT)

    def __init__(self, header, cmd_type,
                 v, omega,
                 max_linear_accel, max_angular_accel,
                 command_id):
        self.header = header          # Header instance
        self.cmd_type = cmd_type      # int (CommandType)
        self.v = v
        self.omega = omega
        self.max_linear_accel = max_linear_accel
        self.max_angular_accel = max_angular_accel
        self.command_id = command_id

    @classmethod
    def from_bytes(cls, buf, offset=0):
        """Parse payload from bytes (without UART framing).

        Returns: (VelocityCommandPayload instance, next_offset)
        """
        header, off = Header.from_bytes(buf, offset)
        (cmd_type,
         v, omega,
         max_lin_accel, max_ang_accel,
         command_id) = struct.unpack_from("!" + cls.BODY_FMT, buf, off)
        off += struct.calcsize("!" + cls.BODY_FMT)

        obj = cls(header, cmd_type,
                  v, omega,
                  max_lin_accel, max_ang_accel,
                  command_id)
        return obj, off

    def to_bytes(self):
        """Pack payload into bytes (without UART framing)."""
        return self.header.to_bytes() + struct.pack(
            "!" + self.BODY_FMT,
            self.cmd_type,
            self.v,
            self.omega,
            self.max_linear_accel,
            self.max_angular_accel,
            self.command_id,
        )


# ------------------- DriveFeedback payload -------------------

class DriveFeedbackPayload:
    """
    Payload for DriveFeedback (Pico -> Pi 5).

    Only sends motor RPMs; timestamp is provided by Header.

    Layout:

        Header (seq, stamp)
        float32 left_rpm
        float32 right_rpm
    """

    BODY_FMT = "ff"
    FMT = Header.FMT + BODY_FMT
    SIZE = struct.calcsize("!" + BODY_FMT)

    def __init__(self, header,
                 left_rpm, right_rpm):
        self.header = header
        self.left_rpm = left_rpm
        self.right_rpm = right_rpm

    @classmethod
    def from_bytes(cls, buf, offset=0):
        header, off = Header.from_bytes(buf, offset)
        (left_rpm, right_rpm) = struct.unpack_from("!" + cls.BODY_FMT, buf, off)
        off += struct.calcsize("!" + cls.BODY_FMT)

        obj = cls(header, left_rpm, right_rpm)
        return obj, off

    def to_bytes(self):
        return self.header.to_bytes() + struct.pack(
            "!" + self.BODY_FMT,
            self.left_rpm,
            self.right_rpm,
        )


# ------------------- BatteryStatus payload -------------------

class BatteryStatusPayload:
    """
    Payload for BatteryStatus (Pico -> Pi 5).

    Only sends battery voltage; timestamp is provided by Header.

    Layout:

        Header (seq, stamp)
        float32 voltage   [V]
    """

    BODY_FMT = "f"
    FMT = Header.FMT + BODY_FMT
    SIZE = struct.calcsize("!" + BODY_FMT)

    def __init__(self, header, voltage):
        self.header = header
        self.voltage = voltage

    @classmethod
    def from_bytes(cls, buf, offset=0):
        header, off = Header.from_bytes(buf, offset)
        (voltage,) = struct.unpack_from("!" + cls.BODY_FMT, buf, off)
        off += struct.calcsize("!" + cls.BODY_FMT)

        obj = cls(header, voltage)
        return obj, off

    def to_bytes(self):
        return self.header.to_bytes() + struct.pack(
            "!" + self.BODY_FMT,
            self.voltage,
        )
