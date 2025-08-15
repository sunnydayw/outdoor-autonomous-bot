# server.py

import json
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from simulator.engine    import RobotSimulator
from simulator.telemetry import build_telemetry_message, set_event_loop

sim = RobotSimulator()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1) Give telemetry the proper event loop
    loop = asyncio.get_running_loop()
    set_event_loop(loop)

    # 2) Start the PyBullet simulation thread
    sim.start()

    yield  # <-- here FastAPI will run until shutdown

    # 3) On shutdown, stop the sim and clean up
    sim.disconnect()

app = FastAPI(lifespan=lifespan)

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    """WebSocket for telemetry broadcasts and cmd_vel commands."""
    await ws.accept()
    sim.clients.add(ws)

    # # Send initial snapshot
    # await ws.send_text(json.dumps(build_telemetry_message(sim.latest_state)))

    try:
        while True:
            raw = await ws.receive_text()
            cmd = json.loads(raw).get("command", {})
            if cmd.get("type") == "twist":
                lin = cmd["target_linear"].get("x", 0.0)
                ang = cmd["target_angular"].get("z", 0.0)
                sim.command_queue.put({
                    "type":   "cmd_vel",
                    "linear": lin,
                    "angular": ang
                })
    except WebSocketDisconnect:
        sim.clients.discard(ws)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8001, log_level="info")
