# proto.py
#
# Shared protocol definitions for Pi 5 <-> Pico UART link.
# Designed to be compatible with both CPython and MicroPython.
#
# This file defines:
#   - CommandType enum-like class
#   - Header (seq + stamp)
#   - VelocityCommandPayload
#   - DriveFeedbackPayload
#   - BatteryStatusPayload
#   - LowLevelStatusPayload

import struct
import time


# ------------------- CommandType "enum" -------------------

class CommandType:
    """Enum-like definition for command types.

    Use plain ints so it works on MicroPython as well.
    """
    SET_VELOCITY   = 0  # normal velocity command
    STOP           = 1  # smooth stop, decelerate to zero
    EMERGENCY_STOP = 2  # hard stop, brake immediately and hold


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
        uint8   cmd_type
        float32 v
        float32 omega
        float32 max_linear_accel
        float32 max_angular_accel
        uint32  command_id
    """

    BODY_FMT = "BffffI"          # no leading "!", we prepend Header.FMT
    FMT = Header.FMT + BODY_FMT  # "!IdBffffI"
    SIZE = struct.calcsize(FMT)

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

    Layout:

        Header (seq, stamp)
        float32 v_meas
        float32 omega_meas
        int32  left_ticks
        int32  right_ticks
        float32 left_rpm
        float32 right_rpm
        uint32 status_flags
    """

    BODY_FMT = "ffii ffI".replace(" ", "")  # "ffii ffI" -> "ffiiffI"
    FMT = Header.FMT + BODY_FMT
    SIZE = struct.calcsize("!" + BODY_FMT)

    def __init__(self, header,
                 v_meas, omega_meas,
                 left_ticks, right_ticks,
                 left_rpm, right_rpm,
                 status_flags):
        self.header = header
        self.v_meas = v_meas
        self.omega_meas = omega_meas
        self.left_ticks = left_ticks
        self.right_ticks = right_ticks
        self.left_rpm = left_rpm
        self.right_rpm = right_rpm
        self.status_flags = status_flags

    @classmethod
    def from_bytes(cls, buf, offset=0):
        header, off = Header.from_bytes(buf, offset)
        (v_meas, omega_meas,
         left_ticks, right_ticks,
         left_rpm, right_rpm,
         status_flags) = struct.unpack_from("!" + cls.BODY_FMT, buf, off)
        off += struct.calcsize("!" + cls.BODY_FMT)

        obj = cls(header,
                  v_meas, omega_meas,
                  left_ticks, right_ticks,
                  left_rpm, right_rpm,
                  status_flags)
        return obj, off

    def to_bytes(self):
        return self.header.to_bytes() + struct.pack(
            "!" + self.BODY_FMT,
            self.v_meas,
            self.omega_meas,
            self.left_ticks,
            self.right_ticks,
            self.left_rpm,
            self.right_rpm,
            self.status_flags,
        )


class DriveFeedbackStatusFlags:
    """Bitmask for DriveFeedbackPayload.status_flags."""

    COMMAND_TIMEOUT     = 1 << 0
    LEFT_ENCODER_FAULT  = 1 << 1
    RIGHT_ENCODER_FAULT = 1 << 2
    LEFT_DRIVER_SAT     = 1 << 3
    RIGHT_DRIVER_SAT    = 1 << 4


# ------------------- BatteryStatus payload -------------------

class BatteryStatusFlags:
    """Bitmask flags for BatteryStatusPayload.status_flags."""
    LOW_BATTERY_WARNING   = 1 << 0
    CRITICALLY_LOW        = 1 << 1
    TEMP_HIGH             = 1 << 2
    TEMP_LOW              = 1 << 3
    # bits 4+ reserved


class BatteryStatusPayload:
    """
    Payload for BatteryStatus (Pico -> Pi 5).

    Layout:

        Header (seq, stamp)
        float32 voltage       [V]
        float32 current       [A], + = discharging, - = charging
        float32 soc           [%] 0–100
        float32 temperature   [°C]
        uint32 status_flags
    """

    BODY_FMT = "ffffI"
    FMT = Header.FMT + BODY_FMT
    SIZE = struct.calcsize("!" + BODY_FMT)

    def __init__(self, header,
                 voltage, current, soc, temperature,
                 status_flags):
        self.header = header
        self.voltage = voltage
        self.current = current
        self.soc = soc
        self.temperature = temperature
        self.status_flags = status_flags

    @classmethod
    def from_bytes(cls, buf, offset=0):
        header, off = Header.from_bytes(buf, offset)
        (voltage, current,
         soc, temperature,
         status_flags) = struct.unpack_from("!" + cls.BODY_FMT, buf, off)
        off += struct.calcsize("!" + cls.BODY_FMT)

        obj = cls(header,
                  voltage, current, soc, temperature,
                  status_flags)
        return obj, off

    def to_bytes(self):
        return self.header.to_bytes() + struct.pack(
            "!" + self.BODY_FMT,
            self.voltage,
            self.current,
            self.soc,
            self.temperature,
            self.status_flags,
        )


# ------------------- LowLevelStatus payload -------------------

class LowLevelFaultFlags:
    """Bitmask for LowLevelStatusPayload.fault_flags."""
    DRIVER_OVERCURRENT = 1 << 0
    DRIVER_OVERTEMP    = 1 << 1
    ENCODER_FAULT      = 1 << 2
    IMU_COMM_FAULT     = 1 << 3
    # bits 4+ reserved


class LowLevelWarningFlags:
    """Bitmask for LowLevelStatusPayload.warning_flags."""
    COMM_TIMEOUT     = 1 << 0
    VOLTAGE_DIP      = 1 << 1
    TEMP_NEAR_LIMIT  = 1 << 2
    # bits 3+ reserved


class LowLevelStatusPayload:
    """
    Payload for LowLevelStatus (Pico -> Pi 5).

    Layout:

        Header (seq, stamp)
        uint32 fault_flags
        uint32 warning_flags
        uint8  estop_active   (0 or 1)
        uint8  estop_source   (0=none, 1=HW button, 2=SW cmd, 3=driver_fault, ...)
        uint32 uptime_ms      (milliseconds since Pico boot)
    """

    BODY_FMT = "IIBBI"   # fault_flags, warning_flags, estop_active, estop_source, uptime_ms
    FMT = Header.FMT + BODY_FMT
    SIZE = struct.calcsize("!" + BODY_FMT)

    def __init__(self, header,
                 fault_flags, warning_flags,
                 estop_active, estop_source,
                 uptime_ms):
        self.header = header
        self.fault_flags = fault_flags
        self.warning_flags = warning_flags
        self.estop_active = estop_active
        self.estop_source = estop_source
        self.uptime_ms = uptime_ms

    @classmethod
    def from_bytes(cls, buf, offset=0):
        header, off = Header.from_bytes(buf, offset)
        (fault_flags,
         warning_flags,
         estop_active,
         estop_source,
         uptime_ms) = struct.unpack_from("!" + cls.BODY_FMT, buf, off)
        off += struct.calcsize("!" + cls.BODY_FMT)

        obj = cls(header,
                  fault_flags, warning_flags,
                  estop_active, estop_source,
                  uptime_ms)
        return obj, off

    def to_bytes(self):
        return self.header.to_bytes() + struct.pack(
            "!" + self.BODY_FMT,
            self.fault_flags,
            self.warning_flags,
            self.estop_active,
            self.estop_source,
            self.uptime_ms,
        )

# ------------------- ClearEstop payload -------------------

class ClearEstopPayload:
    """
    Payload for ClearEstopCommand (Pi 5 -> Pico).

    Layout:

        Header (seq, stamp)
        uint32 request_id   (opaque ID from sender, for logging/correlation)
    """

    BODY_FMT = "I"
    FMT = Header.FMT + BODY_FMT
    SIZE = struct.calcsize("!" + BODY_FMT)

    def __init__(self, header, request_id):
        self.header = header
        self.request_id = request_id

    @classmethod
    def from_bytes(cls, buf, offset=0):
        header, off = Header.from_bytes(buf, offset)
        (request_id,) = struct.unpack_from("!" + cls.BODY_FMT, buf, off)
        off += struct.calcsize("!" + cls.BODY_FMT)
        obj = cls(header, request_id)
        return obj, off

    def to_bytes(self):
        return self.header.to_bytes() + struct.pack(
            "!" + self.BODY_FMT,
            self.request_id,
        )
