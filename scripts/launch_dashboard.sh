#!/usr/bin/env bash
set -euo pipefail

# Bootstrap a venv (if needed) and launch the dashboard backend.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
APP_DIR="$ROOT_DIR/dashboard/backend"
VENV_DIR="${VENV_DIR:-$APP_DIR/.venv}"

PYTHON_BIN="${PYTHON_BIN:-python3}"

if [ ! -d "$VENV_DIR" ]; then
  echo "[launch] Creating virtual environment at $VENV_DIR"
  "$PYTHON_BIN" -m venv "$VENV_DIR"
  "$VENV_DIR/bin/pip" install --upgrade pip
  "$VENV_DIR/bin/pip" install -r "$APP_DIR/requirements.txt"
elif [ "${SYNC_DEPS:-0}" = "1" ]; then
  echo "[launch] Syncing Python dependencies"
  "$VENV_DIR/bin/pip" install -r "$APP_DIR/requirements.txt"
fi

source "$VENV_DIR/bin/activate"

export SIM_URL="${SIM_URL:-ws://localhost:8001/ws}"
export CAMERA_DEVICE="${CAMERA_DEVICE:-/dev/video0}"
export CAMERA_WIDTH="${CAMERA_WIDTH:-640}"
export CAMERA_HEIGHT="${CAMERA_HEIGHT:-480}"
export CAMERA_FPS="${CAMERA_FPS:-12}"
export CAMERA_FOURCC="${CAMERA_FOURCC:-H264}"
export CAMERA_JPEG_QUALITY="${CAMERA_JPEG_QUALITY:-75}"
export PORT="${PORT:-8000}"

cd "$APP_DIR"

echo "[launch] Starting dashboard on port $PORT"
exec uvicorn app.server:app --host 0.0.0.0 --port "$PORT"
