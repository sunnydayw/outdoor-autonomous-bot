#!/usr/bin/env python
# source simulation/venv/bin/activate

import threading
import time
import json
import queue
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

import pybullet as p
import pybullet_data

# ——— Shared state & queues ———
latest_state = {}              # updated by sim thread, read by WebSocket 
command_queue = queue.Queue()  # commands from clients → sim thread
clients = set()                # active WebSocket connections

# ——— Robot & world parameters ———
URDF_PATH = "rover/rover.urdf"
LEFT_JID = 0
RIGHT_JID = 1
WHEEL_RADIUS = 5 * 0.0254        # 5 in → meters
WHEEL_SEPARATION = 19 * 0.0254   # 19 in → meters
MAX_FORCE = 5.0                  # N·m

# ——— Build nested telemetry message per schema ———
def build_telemetry_message():
    ts = int(time.time() * 1000)
    pos = latest_state.get("position", (0.0, 0.0, 0.0))
    orn = latest_state.get("orientation", (0.0, 0.0, 0.0, 1.0))
    lin = latest_state.get("linear_velocity", (0.0, 0.0, 0.0))
    ang = latest_state.get("angular_velocity", (0.0, 0.0, 0.0))
    acc = latest_state.get("imu_acc", (0.0, 0.0, 0.0))
    gyro = latest_state.get("imu_gyro", (0.0, 0.0, 0.0))
    status = latest_state.get("status", {})

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

# ——— Send telemetry to all connected WebSocket clients ———
def broadcast_telemetry():
    message = json.dumps(build_telemetry_message())
    # for ws in list(clients):
    #     try:
    #         asyncio.create_task(ws.send_text(message))
    #     except RuntimeError:
    #         clients.discard(ws)
    # schedule the send_text coroutines on the FastAPI event loop:
    for ws in list(clients):
        try:
            loop.call_soon_threadsafe(asyncio.create_task, ws.send_text(message))
        except Exception:
            clients.discard(ws)

# ——— Apply drive commands ———
def apply_drive(linear: float, angular: float):
    L = WHEEL_SEPARATION
    v_l = (linear - (L/2)*angular) / WHEEL_RADIUS
    v_r = (linear + (L/2)*angular) / WHEEL_RADIUS

    p.setJointMotorControl2(
        bodyIndex=robot,
        jointIndex=LEFT_JID,
        controlMode=p.VELOCITY_CONTROL,
        targetVelocity=v_l,
        force=MAX_FORCE,
    )
    p.setJointMotorControl2(
        bodyIndex=robot,
        jointIndex=RIGHT_JID,
        controlMode=p.VELOCITY_CONTROL,
        targetVelocity=v_r,
        force=MAX_FORCE,
    )

# ——— Simulation loop (runs in background thread) ———
def simulation_loop():
    # Initialize PyBullet (headless)
    physics_client = p.connect(p.DIRECT)  # <-- use p.GUI on Linux for visuals
    p.setAdditionalSearchPath(pybullet_data.getDataPath())
    p.setGravity(0, 0, -9.81)

    # Load environment and robot
    p.loadURDF("plane.urdf")
    global robot
    robot = p.loadURDF(URDF_PATH, basePosition=[0, 0, 0.155])

    # Simulate battery status (static for now)
    latest_state["status"] = {
        "battery_voltage":    12.5,
        "battery_percentage": 1.0,
        "mode":               "SIM",
        "error_code":         0
    }
    
    # For IMU acceleration
    prev_lin_vel = [0.0, 0.0, 0.0]
    dt = 1/50  # matching your simulation rate

    # Main loop at ~50 Hz
    while True:
        # 1. Handle incoming commands
        while not command_queue.empty():
            cmd = command_queue.get_nowait()
            # expect {'type':'cmd_vel','linear':..,'angular':..}
            if cmd.get("type") == "cmd_vel":
                apply_drive(cmd["linear"], cmd["angular"])

        # 2. Step simulation
        p.stepSimulation()

        # 3. Read raw state
        pos, orn = p.getBasePositionAndOrientation(robot)
        lin_vel, ang_vel = p.getBaseVelocity(robot)

        # Compute IMU (body-frame acc & gyro)
        # 1) Linear acceleration (world frame)
        acc_world = [ (lin_vel[i] - prev_lin_vel[i]) / dt for i in range(3) ]
        prev_lin_vel = lin_vel

        # 2) Get rotation matrix from world → body
        rot_mat = p.getMatrixFromQuaternion(orn)  # returns 9‐tuple row‐major
        R = [rot_mat[0:3], rot_mat[3:6], rot_mat[6:9]]  # 3×3

        # 3) Body-frame acceleration = R * (acc_world − g_world)
        #    where g_world = [0,0,−9.81]
        acc_world[2] += 9.81  # add gravity back (so IMU measures gravity + inertia)
        acc_body = [
            sum(R[row][col] * acc_world[col] for col in range(3))
            for row in range(3)
        ]

        # 4) Body-frame angular velocity (gyroscope) = R * ang_vel_world
        gyro_body = [
            sum(R[row][col] * ang_vel[col] for col in range(3))
            for row in range(3)
        ]

        # Update latest_state
        latest_state.update({
            "position":         pos,
            "orientation":      orn,
            "linear_velocity":  lin_vel,
            "angular_velocity": ang_vel,
            "imu_acc":          acc_body,
            "imu_gyro":         gyro_body,
        })

        # Broadcast telemetry
        broadcast_telemetry()

        # Throttle rate
        time.sleep(1/50)

# ——— FastAPI lifespan for starting/stopping sim thread ———
app = FastAPI()
loop = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global loop
    loop = asyncio.get_running_loop()
    # Startup: launch the simulation thread
    sim_thread = threading.Thread(target=simulation_loop, daemon=True)
    sim_thread.start()
    yield
    # Shutdown: disconnect PyBullet
    try:
        p.disconnect()
    except:
        pass

# ——— Create app with lifespan handler ———
app.router.lifespan_context = lifespan

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    """WebSocket endpoint for telemetry & commands."""
    await ws.accept()
    clients.add(ws)

    # Send initial state
    await ws.send_text(json.dumps(build_telemetry_message()))

    try:
        while True:
            raw = await ws.receive_text()
            payload = json.loads(raw)

            # Expect nested "command" object
            cmd = payload.get("command")
            if not cmd:
                continue

            if cmd.get("type") == "twist":
                lin = cmd["target_linear"].get("x", 0.0)
                ang = cmd["target_angular"].get("z", 0.0)
                # enqueue as cmd_vel
                command_queue.put({"type":"cmd_vel", "linear":lin, "angular":ang})

    except WebSocketDisconnect:
        clients.discard(ws)

# ——— Run via Uvicorn when invoked directly ———
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("simulation_server:app", host="0.0.0.0", port=8001, log_level="info")


