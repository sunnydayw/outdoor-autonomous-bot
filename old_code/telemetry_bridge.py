import asyncio
import math
import json
import websockets
from .config import SIM_URL

# Connected dashboard clients and latest state
clients = set()
global_state = None

async def telemetry_bridge():
    """
    Connects to SIM_URL, reads raw JSON telemetry, processes it,
    and broadcasts to dashboard clients at ~10Hz.
    """
    global global_state
    last_broadcast = 0.0
    min_interval   = 1  # seconds (10 Hz)

    while True:
        try:
            async with websockets.connect(SIM_URL) as sim_ws:
                async for raw_msg in sim_ws:
                    now = asyncio.get_event_loop().time()
                    # always update global_state (for new clients)
                    global_state = raw_msg

                    # throttle actual broadcasts
                    if now - last_broadcast < min_interval:
                        continue

                    # process & broadcast
                    try:
                        raw = json.loads(raw_msg)
                        clean_msg = process_telemetry(raw)
                        data = json.dumps(clean_msg)
                    except Exception:
                        # if processing fails, skip this frame
                        continue

                    for ws in set(clients):
                        try:
                            await ws.send_text(data)
                        except:
                            clients.discard(ws)

                    last_broadcast = now

        except Exception:
            # retry on any connection error after a short pause
            await asyncio.sleep(1)


"""
Post-process raw telemetry:
 - Round numerical values for readability
 - Compute heading (yaw) from quaternion for arrow display
"""
def process_telemetry(raw: dict) -> dict:
    # Post-process raw telemetry for readability
    #  - Round to 2 decimal places
    #  - Zero out tiny noise (<0.01)
    out = { "timestamp": raw.get("timestamp") }

    def clean(vals: dict) -> dict:
        cleaned = {}
        for k, v in vals.items():
            num = round(float(v), 2)
            # zero out small noise
            cleaned[k] = 0.0 if abs(num) < 0.01 else num
        return cleaned

    # Pose
    pose = raw.get("pose", {})
    pos   = pose.get("position", {})
    orn   = pose.get("orientation", {})
    out["pose"] = {
        "position":    clean(pos),
        "orientation": clean(orn),
    }

    # Velocity
    vel = raw.get("velocity", {})
    out["velocity"] = {
        "linear":  clean(vel.get("linear", {})),
        "angular": clean(vel.get("angular", {})),
    }

    # IMU
    imu = raw.get("imu", {})
    out["imu"] = {
        "linear_acceleration": clean(imu.get("linear_acceleration", {})),
        "angular_velocity":    clean(imu.get("angular_velocity", {})),
    }

    # Status passthrough
    out["status"] = raw.get("status", {})

    # Compute heading (yaw) for 2D arrow
    q = orn
    w = float(q.get("w", 1.0))
    x = float(q.get("x", 0.0))
    y = float(q.get("y", 0.0))
    z = float(q.get("z", 0.0))
    yaw = math.atan2(2*(w*z + x*y), 1 - 2*(y*y + z*z))
    out["heading"] = round(yaw, 2)

    return out
