# backend/command_state.py
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from threading import RLock
import time
from typing import Tuple


class ControlMode(str, Enum):
    IDLE = "idle"
    TELEOP = "teleop"
    AUTO = "auto"  # reserved for ROS2 / planner


@dataclass
class TelemetryData:
    """
    Incoming telemetry from Pico.
    """
    left_target_rpm: float = 0.0
    right_target_rpm: float = 0.0
    left_actual_rpm: float = 0.0
    right_actual_rpm: float = 0.0
    battery_voltage: float = 0.0
    accel_x: float = 0.0
    accel_y: float = 0.0
    accel_z: float = 0.0
    gyro_x: float = 0.0
    gyro_y: float = 0.0
    gyro_z: float = 0.0
    last_update_ts: float = 0.0
    valid: bool = False  # True if we have received valid telemetry


@dataclass
class SourceState:
    """
    Per-source command state (teleop, auto, etc.).
    All times are in time.monotonic() seconds.
    """
    v_cmd: float = 0.0          # m/s
    w_cmd: float = 0.0          # rad/s
    last_update_ts: float = 0.0
    active: bool = False


@dataclass
class CommandState:
    """
    Central command/mode manager.

    - Receives commands from different sources (teleop now, auto later).
    - Applies per-source timeouts.
    - Selects the active mode (manual override by teleop).
    - Provides the current command to the motor/UART loop.
    """
    teleop: SourceState = field(default_factory=SourceState)
    auto: SourceState   = field(default_factory=SourceState)

    mode: ControlMode = ControlMode.IDLE

    # Timeouts (seconds)
    teleop_timeout: float = 0.5   # if no teleop cmd in 0.5s → teleop inactive
    auto_timeout: float   = 1.0   # auto planner can be slightly slower

    # Incoming telemetry from Pico
    telemetry: TelemetryData = field(default_factory=TelemetryData)

    # Internal lock for thread/async safety
    _lock: RLock = field(default_factory=RLock, init=False, repr=False)

    # ---------- Update APIs (called by FastAPI / ROS2 bridges) ----------

    def update_teleop(self, v_cmd: float, w_cmd: float) -> None:
        """
        Update teleop source with a new command from the web UI.
        """
        now = time.monotonic()
        with self._lock:
            self.teleop.v_cmd = v_cmd
            self.teleop.w_cmd = w_cmd
            self.teleop.last_update_ts = now
            self.teleop.active = True
            self._recompute_mode_locked(now)

    def update_auto(self, v_cmd: float, w_cmd: float) -> None:
        """
        Update auto source (future ROS2/planner). Not used yet, but ready.
        """
        now = time.monotonic()
        with self._lock:
            self.auto.v_cmd = v_cmd
            self.auto.w_cmd = w_cmd
            self.auto.last_update_ts = now
            self.auto.active = True
            self._recompute_mode_locked(now)

    def update_telemetry(
        self,
        left_target_rpm: float,
        right_target_rpm: float,
        left_actual_rpm: float,
        right_actual_rpm: float,
        battery_voltage: float,
        accel_x: float,
        accel_y: float,
        accel_z: float,
        gyro_x: float,
        gyro_y: float,
        gyro_z: float,
    ) -> None:
        """
        Update telemetry data from Pico.
        """
        now = time.monotonic()
        with self._lock:
            self.telemetry.left_target_rpm = left_target_rpm
            self.telemetry.right_target_rpm = right_target_rpm
            self.telemetry.left_actual_rpm = left_actual_rpm
            self.telemetry.right_actual_rpm = right_actual_rpm
            self.telemetry.battery_voltage = battery_voltage
            self.telemetry.accel_x = accel_x
            self.telemetry.accel_y = accel_y
            self.telemetry.accel_z = accel_z
            self.telemetry.gyro_x = gyro_x
            self.telemetry.gyro_y = gyro_y
            self.telemetry.gyro_z = gyro_z
            self.telemetry.last_update_ts = now
            self.telemetry.valid = True

    # ---------- Query APIs (called by UART loop / status endpoints) ----------

    def get_current_command(self) -> Tuple[float, float, ControlMode]:
        """
        Return the currently active (v_cmd, w_cmd, mode), after applying timeouts.

        This is what your Pi→Pico UART loop should call at a fixed rate
        (e.g. 50 Hz). If no source is active, returns (0, 0, IDLE).
        """
        now = time.monotonic()
        with self._lock:
            self._recompute_mode_locked(now)

            if self.mode == ControlMode.TELEOP:
                src = self.teleop
            elif self.mode == ControlMode.AUTO:
                src = self.auto
            else:
                return 0.0, 0.0, ControlMode.IDLE

            return src.v_cmd, src.w_cmd, self.mode

    def get_status_snapshot(self) -> dict:
        """
        Lightweight snapshot for /status API or debug UI.
        """
        now = time.monotonic()
        with self._lock:
            self._recompute_mode_locked(now)
            return {
                "mode": self.mode.value,
                "teleop": {
                    "v_cmd": self.teleop.v_cmd,
                    "w_cmd": self.teleop.w_cmd,
                    "active": self.teleop.active,
                    "age_s": now - self.teleop.last_update_ts,
                },
                "auto": {
                    "v_cmd": self.auto.v_cmd,
                    "w_cmd": self.auto.w_cmd,
                    "active": self.auto.active,
                    "age_s": now - self.auto.last_update_ts,
                },
            }

    def get_telemetry_snapshot(self) -> dict:
        """
        Snapshot of latest telemetry data.
        """
        now = time.monotonic()
        with self._lock:
            return {
                "left_target_rpm": self.telemetry.left_target_rpm,
                "right_target_rpm": self.telemetry.right_target_rpm,
                "left_actual_rpm": self.telemetry.left_actual_rpm,
                "right_actual_rpm": self.telemetry.right_actual_rpm,
                "battery_voltage": self.telemetry.battery_voltage,
                "accel_x": self.telemetry.accel_x,
                "accel_y": self.telemetry.accel_y,
                "accel_z": self.telemetry.accel_z,
                "gyro_x": self.telemetry.gyro_x,
                "gyro_y": self.telemetry.gyro_y,
                "gyro_z": self.telemetry.gyro_z,
                "last_update_ts": self.telemetry.last_update_ts,
                "age_s": now - self.telemetry.last_update_ts,
                "valid": self.telemetry.valid,
            }

    # ---------- Internal helpers ----------

    def _recompute_mode_locked(self, now: float) -> None:
        """
        Apply timeouts and select the active mode.

        Priority rule (for now):
        - If teleop is active → TELEOP
        - Else if auto is active → AUTO
        - Else → IDLE
        """

        # Apply timeouts
        teleop_age = now - self.teleop.last_update_ts
        auto_age   = now - self.auto.last_update_ts

        teleop_active = teleop_age < self.teleop_timeout
        auto_active   = auto_age   < self.auto_timeout

        self.teleop.active = teleop_active
        self.auto.active   = auto_active

        # Mode arbitration
        if teleop_active:
            self.mode = ControlMode.TELEOP
        elif auto_active:
            self.mode = ControlMode.AUTO
        else:
            self.mode = ControlMode.IDLE
