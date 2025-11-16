"""Utilities for exposing the USB camera as an MJPEG stream."""

import logging
import time
import threading
from typing import Iterator

import cv2

from .config import (
    CAMERA_DEVICE,
    CAMERA_WIDTH,
    CAMERA_HEIGHT,
    CAMERA_FPS,
    CAMERA_FOURCC,
    CAMERA_JPEG_QUALITY,
)

BOUNDARY = "frame"
FALLBACK_FOURCC = "MJPG"
_LOG = logging.getLogger(__name__)
_CAMERA_LOCK = threading.Lock()


def _fourcc_code(symbols: str) -> int:
    normalized = (symbols or "").upper()
    padded = (normalized + "    ")[:4]
    return cv2.VideoWriter_fourcc(*padded)


def _open_capture(fourcc: str) -> cv2.VideoCapture:
    cap = cv2.VideoCapture(CAMERA_DEVICE)
    if not cap.isOpened():
        cap.release()
        raise RuntimeError(f"Unable to open camera at {CAMERA_DEVICE}")

    if CAMERA_WIDTH:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
    if CAMERA_HEIGHT:
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
    if CAMERA_FPS:
        cap.set(cv2.CAP_PROP_FPS, CAMERA_FPS)
    if fourcc:
        cap.set(cv2.CAP_PROP_FOURCC, _fourcc_code(fourcc))

    if hasattr(cv2, "CAP_PROP_BUFFERSIZE"):
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    return cap


def _read_frame(cap: cv2.VideoCapture):
    try:
        return cap.read()
    except cv2.error as exc:
        raise RuntimeError("capture-read-error") from exc


def mjpeg_stream() -> Iterator[bytes]:
    _CAMERA_LOCK.acquire()

    cap = None
    try:
        fourcc = CAMERA_FOURCC
        cap = _open_capture(fourcc)
        fallback_used = False

        frame_interval = 0.0
        if CAMERA_FPS and CAMERA_FPS > 0:
            frame_interval = 1.0 / CAMERA_FPS

        encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), CAMERA_JPEG_QUALITY]
        failure_count = 0

        try:
            while True:
                try:
                    success, frame = _read_frame(cap)
                except RuntimeError:
                    if not fallback_used and fourcc.upper() != FALLBACK_FOURCC:
                        fallback_used = True
                        _LOG.warning(
                            "Camera read failed for FOURCC %s, retrying with %s",
                            fourcc,
                            FALLBACK_FOURCC,
                        )
                        cap.release()
                        cap = _open_capture(FALLBACK_FOURCC)
                        fourcc = FALLBACK_FOURCC
                        time.sleep(0.1)
                        continue

                    _LOG.error("Camera read failed: %s", CAMERA_DEVICE)
                    failure_count += 1
                    if failure_count >= 5:
                        raise RuntimeError("Camera read failed repeatedly")
                    time.sleep(0.1)
                    continue

                if not success or frame is None:
                    if not fallback_used and fourcc.upper() != FALLBACK_FOURCC:
                        fallback_used = True
                        _LOG.warning(
                            "Camera read returned empty frame for FOURCC %s, switching to %s",
                            fourcc,
                            FALLBACK_FOURCC,
                        )
                        cap.release()
                        cap = _open_capture(FALLBACK_FOURCC)
                        fourcc = FALLBACK_FOURCC
                        time.sleep(0.1)
                        continue

                    failure_count += 1
                    if failure_count >= 5:
                        raise RuntimeError("Camera returned empty frames repeatedly")
                    time.sleep(0.1)
                    continue

                failure_count = 0
                encoded, buffer = cv2.imencode(".jpg", frame, encode_params)
                if not encoded:
                    continue

                frame_bytes = buffer.tobytes()
                yield (
                    b"--" + BOUNDARY.encode("ascii") + b"\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n"
                )

                if frame_interval:
                    time.sleep(frame_interval)
        except GeneratorExit:
            # client closed connection; ensure capture is released
            pass
    finally:
        if cap is not None:
            cap.release()
        _CAMERA_LOCK.release()


__all__ = ["BOUNDARY", "mjpeg_stream"]
