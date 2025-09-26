import os

# URL of the telemetry source (simulation or real robot)
SIM_URL = os.environ.get("SIM_URL", "ws://simulation:8001/ws")


def _to_int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _to_float(value, default):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


# Camera configuration defaults (can be overridden via environment)
CAMERA_DEVICE = os.environ.get("CAMERA_DEVICE", "/dev/video0")
CAMERA_WIDTH = _to_int(os.environ.get("CAMERA_WIDTH"), 1280)
CAMERA_HEIGHT = _to_int(os.environ.get("CAMERA_HEIGHT"), 720)
CAMERA_FPS = _to_float(os.environ.get("CAMERA_FPS"), 15.0)
CAMERA_FOURCC = os.environ.get("CAMERA_FOURCC", "MJPG")
_jpeg_quality = _to_int(os.environ.get("CAMERA_JPEG_QUALITY"), 80)
CAMERA_JPEG_QUALITY = min(100, max(1, _jpeg_quality))
