# backend/api.py
from __future__ import annotations

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from fastapi import WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState
from pydantic import BaseModel, Field
from pathlib import Path
import time
import json
import asyncio
import logging
from .command_state import CommandState, ControlMode

app = FastAPI(title="Robot Teleop Backend")

# Serve the web UI from / and /debug
BASE_DIR = Path(__file__).resolve().parent.parent
WEB_DIR = BASE_DIR / "web"
# Resolve static directory relative to this file so uvicorn works regardless of CWD.
app.mount("/static", StaticFiles(directory=WEB_DIR, html=True), name="static")

logger = logging.getLogger(__name__)

@app.get("/", include_in_schema=False)
async def root():
    # Redirect root to the main teleop page
    return RedirectResponse(url="/static/teleop.html")

@app.get("/debug", include_in_schema=False)
async def debug():
    # Shortcut for the debug page
    return RedirectResponse(url="/static/debug.html")


# Single global command state for this process
command_state = CommandState()

# ---------- Pydantic models ----------

class TeleopCmd(BaseModel):
    """
    Command payload from web teleop UI.
    """
    v_cmd: float = Field(..., description="Linear velocity command [m/s]")
    w_cmd: float = Field(..., description="Angular velocity command [rad/s]")
    timestamp_ms: int = Field(..., description="Client-side timestamp in ms")
    source: str = Field("web_teleop", description="Command source identifier")


class AutoCmd(BaseModel):
    """
    Future: command payload from autonomy / ROS bridge.
    Not used yet, but defined for completeness.
    """
    v_cmd: float
    w_cmd: float
    timestamp_ms: int
    source: str = "auto_planner"


class StatusResponse(BaseModel):
    mode: ControlMode
    teleop: dict
    auto: dict
    server_time_ms: int


class CurrentCommandResponse(BaseModel):
    v_cmd: float
    w_cmd: float
    mode: ControlMode
    server_time_ms: int


class TelemetryResponse(BaseModel):
    left_target_rpm: float
    right_target_rpm: float
    left_actual_rpm: float
    right_actual_rpm: float
    battery_voltage: float
    accel_x: float
    accel_y: float
    accel_z: float
    gyro_x: float
    gyro_y: float
    gyro_z: float
    age_s: float
    valid: bool
    server_time_ms: int


# ---------- Endpoints ----------

@app.post("/cmd_vel", response_model=dict)
async def set_cmd_vel_teleop(cmd: TeleopCmd):
    """
    Main teleop endpoint.

    Called at a fixed rate (~20 Hz) by teleop.js.
    Updates the teleop source in CommandState.
    """
    # You can optionally log or validate the client timestamp here.
    command_state.update_teleop(cmd.v_cmd, cmd.w_cmd)
    return {"status": "ok"}


@app.post("/cmd_vel_auto", response_model=dict)
async def set_cmd_vel_auto(cmd: AutoCmd):
    """
    Reserved for future autonomy / ROS2 bridge.

    For now, this won't be called by your system but the signature is in place.
    """
    command_state.update_auto(cmd.v_cmd, cmd.w_cmd)
    return {"status": "ok"}


@app.get("/status", response_model=StatusResponse)
async def get_status():
    """
    Lightweight status snapshot for debugging and future UI.

    Returns:
    - current mode (idle/teleop/auto)
    - per-source v_cmd, w_cmd, active flag, age
    """
    snap = command_state.get_status_snapshot()
    return StatusResponse(
        mode=ControlMode(snap["mode"]),
        teleop=snap["teleop"],
        auto=snap["auto"],
        server_time_ms=int(time.time() * 1000),
    )


@app.get("/current_command", response_model=CurrentCommandResponse)
async def get_current_command():
    """
    Debug endpoint: what the UART loop *should* be sending right now.
    """
    v_cmd, w_cmd, mode = command_state.get_current_command()
    return CurrentCommandResponse(
        v_cmd=v_cmd,
        w_cmd=w_cmd,
        mode=mode,
        server_time_ms=int(time.time() * 1000),
    )


@app.get("/telemetry", response_model=TelemetryResponse)
async def get_telemetry():
    """
    Latest telemetry data from Pico.
    """
    snap = command_state.get_telemetry_snapshot()
    return TelemetryResponse(
        left_target_rpm=snap["left_target_rpm"],
        right_target_rpm=snap["right_target_rpm"],
        left_actual_rpm=snap["left_actual_rpm"],
        right_actual_rpm=snap["right_actual_rpm"],
        battery_voltage=snap["battery_voltage"],
        accel_x=snap["accel_x"],
        accel_y=snap["accel_y"],
        accel_z=snap["accel_z"],
        gyro_x=snap["gyro_x"],
        gyro_y=snap["gyro_y"],
        gyro_z=snap["gyro_z"],
        age_s=snap["age_s"],
        valid=snap["valid"],
        server_time_ms=int(time.time() * 1000),
    )


@app.websocket("/ws/telemetry")
async def websocket_telemetry(websocket: WebSocket):
    """
    WebSocket endpoint for real-time telemetry updates.
    """
    await websocket.accept()
    try:
        # Send initial telemetry
        snap = command_state.get_telemetry_snapshot()
        await websocket.send_json(snap)

        last_sent_ts = snap["last_update_ts"] if snap["valid"] else 0

        while True:
            # Check for new telemetry
            current_snap = command_state.get_telemetry_snapshot()
            if current_snap["valid"] and current_snap["last_update_ts"] > last_sent_ts:
                await websocket.send_json(current_snap)
                last_sent_ts = current_snap["last_update_ts"]

            # Small delay to avoid busy loop
            await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        logger.info("Telemetry WebSocket disconnected")
    except Exception as e:
        logger.error("WebSocket error: %s", e)
    finally:
        if websocket.application_state == WebSocketState.CONNECTED:
            await websocket.close()
