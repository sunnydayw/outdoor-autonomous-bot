import asyncio
import json
from pathlib import Path

import websockets
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles

from telemetry_bridge import telemetry_bridge, clients, global_state
from config import SIM_URL

app = FastAPI()

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

@app.on_event("startup")
async def startup_event():
    # Launch the telemetry bridge when the server starts
    asyncio.create_task(telemetry_bridge())

@app.websocket("/ws")
async def dashboard_ws(ws: WebSocket):
    """
    WebSocket endpoint for the dashboard UI.
    - Sends the latest processed telemetry on connect.
    - Forwards incoming command messages to the simulation or real robot.
    """
    await ws.accept()
    clients.add(ws)

    # Send initial telemetry snapshot if available
    if global_state is not None:
        await ws.send_text(json.dumps(global_state))

    try:
        while True:
            raw_cmd = await ws.receive_text()
            # Forward the raw command JSON to the telemetry source (sim or robot)
            try:
                async with websockets.connect(SIM_URL) as sim_ws:
                    await sim_ws.send(raw_cmd)
            except Exception:
                # If forwarding fails, you could buffer or log the error
                pass
    except WebSocketDisconnect:
        clients.discard(ws)


if STATIC_DIR.exists():
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="dashboard")
