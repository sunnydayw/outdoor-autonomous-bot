#!/usr/bin/env python
# source simulation/venv/bin/activate

import argparse
import threading
import time
import json
import queue

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import pybullet as p
import pybullet_data

# ——— Shared state & queues ———
latest_state   = {}
command_queue  = queue.Queue()
clients        = set()

# ——— Robot & world parameters ———
URDF_PATH        = "rover/rover.urdf"
LEFT_JID         = 0
RIGHT_JID        = 1
WHEEL_RADIUS     = 5 * 0.0254
WHEEL_SEPARATION = 19 * 0.0254
MAX_FORCE        = 5.0

# ——— Drive logic ———
def apply_drive(cmd):
    v = cmd.get("linear", 0.0)
    w = cmd.get("angular", 0.0)
    L = WHEEL_SEPARATION
    v_l = (v - (L/2)*w) / WHEEL_RADIUS
    v_r = (v + (L/2)*w) / WHEEL_RADIUS

    p.setJointMotorControl2(robot, LEFT_JID,  p.VELOCITY_CONTROL,
                            targetVelocity=v_l, force=MAX_FORCE)
    p.setJointMotorControl2(robot, RIGHT_JID, p.VELOCITY_CONTROL,
                            targetVelocity=v_r, force=MAX_FORCE)

# ——— Telemetry broadcast ———
def broadcast_telemetry():
    packet = {"type": "telemetry", **latest_state}
    data = json.dumps(packet)
    print(f"📡 Broadcasting to {len(clients)} client(s):", latest_state)
    import asyncio
    for ws in list(clients):
        try:
            asyncio.create_task(ws.send_text(data))
        except RuntimeError:
            clients.discard(ws)

# ——— Simulation loop ———
def simulation_loop():
    print("🕹️  Simulation loop started")
    while True:
        # Handle commands
        while not command_queue.empty():
            cmd = command_queue.get_nowait()
            if cmd.get("type") == "cmd_vel":
                print("▶️ apply_drive:", cmd)
                apply_drive(cmd)

        # Step physics
        p.stepSimulation()

        # Update state
        pos, orn     = p.getBasePositionAndOrientation(robot)
        lin_vel, ang = p.getBaseVelocity(robot)
        latest_state.update({
            "position": pos,
            "orientation": orn,
            "linear_velocity": lin_vel,
            "angular_velocity": ang
        })

        # Broadcast
        broadcast_telemetry()

        time.sleep(1/50)  # ~50 Hz

# ——— WebSocket API ———
app = FastAPI()

@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    clients.add(ws)
    try:
        # Send initial state
        await ws.send_text(json.dumps({"type": "telemetry", **latest_state}))
        # Receive commands
        while True:
            msg = await ws.receive_text()
            command_queue.put(json.loads(msg))
    except WebSocketDisconnect:
        clients.discard(ws)

# ——— Main entrypoint ———
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--gui",  action="store_true",
                        help="Run PyBullet with GUI (else headless)")
    parser.add_argument("--port", type=int, default=8001,
                        help="WebSocket server port")
    args = parser.parse_args()

    # 1) Connect PyBullet on main thread
    mode = p.GUI if args.gui else p.DIRECT
    p.connect(mode)
    p.setAdditionalSearchPath(pybullet_data.getDataPath())
    p.setGravity(0, 0, -9.81)

    # 2) Load world & robot
    p.loadURDF("plane.urdf")
    robot = p.loadURDF(URDF_PATH, basePosition=[0, 0, 0.16])

    # 3) Launch simulation & server per mode
    if args.gui:
        # GUI: sim on main thread, server in background
        server_thread = threading.Thread(
            target=lambda: __import__("uvicorn").run(
                app, host="0.0.0.0", port=args.port, log_level="info"
            ),
            daemon=True
        )
        server_thread.start()
        simulation_loop()  # blocks on main thread
    else:
        # Headless: sim in background, server on main
        threading.Thread(target=simulation_loop, daemon=True).start()
        __import__("uvicorn").run(
            app, host="0.0.0.0", port=args.port, log_level="info"
        )

