import asyncio
import json
import os
import threading
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import websockets

# Environment variable for simulation server URL
SIM_URL = os.environ.get("SIM_URL", "ws://simulation:8001/ws")

# Shared state and connections
global_state = None
clients = set()

async def sim_bridge():
    global global_state
    while True:
        try:
            async with websockets.connect(SIM_URL) as sim_ws:
                async for msg in sim_ws:
                    global_state = msg
                    # broadcast to frontend clients
                    for ws in set(clients):
                        try:
                            await ws.send_text(msg)
                        except:
                            clients.discard(ws)
        except Exception:
            await asyncio.sleep(1)

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    # start the bridge to simulation server
    asyncio.create_task(sim_bridge())

@app.websocket("/ws")
async def dashboard_ws(ws: WebSocket):
    await ws.accept()
    clients.add(ws)
    # send initial snapshot
    if global_state:
        await ws.send_text(global_state)
    try:
        while True:
            raw = await ws.receive_text()
            # forward command payload to sim
            async with websockets.connect(SIM_URL) as sim_ws:
                await sim_ws.send(raw)
    except WebSocketDisconnect:
        clients.discard(ws)