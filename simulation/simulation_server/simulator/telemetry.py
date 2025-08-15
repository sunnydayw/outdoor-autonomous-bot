# simulator/telemetry.py

import json
import time
import asyncio

# will hold the FastAPI event loop
_loop = None

def set_event_loop(loop: asyncio.AbstractEventLoop):
    """Call this once at startup to give us the right event loop."""
    global _loop
    _loop = loop

def build_telemetry_message(state: dict) -> dict:
    ts   = int(time.time() * 1000)
    pos  = state.get("position", (0.0, 0.0, 0.0))
    orn  = state.get("orientation", (0.0, 0.0, 0.0, 1.0))
    lin  = state.get("linear_velocity", (0.0, 0.0, 0.0))
    ang  = state.get("angular_velocity", (0.0, 0.0, 0.0))
    acc  = state.get("imu_acc", (0.0, 0.0, 0.0))
    gyro = state.get("imu_gyro", (0.0, 0.0, 0.0))
    status = state.get("status", {})

    return {
        "timestamp": ts,
        "pose": {
            "position":    {"x": pos[0], "y": pos[1], "z": pos[2]},
            "orientation": {"x": orn[0], "y": orn[1], "z": orn[2], "w": orn[3]},
        },
        "velocity": {
            "linear":  {"x": lin[0], "y": lin[1], "z": lin[2]},
            "angular": {"x": ang[0], "y": ang[1], "z": ang[2]},
        },
        "imu": {
            "orientation":         {"x": orn[0], "y": orn[1], "z": orn[2], "w": orn[3]},
            "angular_velocity":    {"x": gyro[0], "y": gyro[1], "z": gyro[2]},
            "linear_acceleration": {"x": acc[0],  "y": acc[1],  "z": acc[2]},
        },
        "status": {
            "battery_voltage":    status.get("battery_voltage"),
            "battery_percentage": status.get("battery_percentage"),
            "mode":               status.get("mode"),
            "error_code":         status.get("error_code"),
        }
    }

def broadcast_telemetry(clients: set, state: dict):
    """Send the latest telemetry JSON to every WebSocket in `clients`."""
    if _loop is None:
        # startup not completed yet
        return

    message = json.dumps(build_telemetry_message(state))
    for ws in list(clients):
        try:
            _loop.call_soon_threadsafe(asyncio.create_task, ws.send_text(message))
        except Exception:
            clients.discard(ws)
