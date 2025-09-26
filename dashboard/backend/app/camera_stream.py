"""Utilities for exposing the USB camera as an MJPEG stream."""

import time
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


def _fourcc_code(symbols: str) -> int:
    normalized = (symbols or "").upper()
    padded = (normalized + "    ")[:4]
    return cv2.VideoWriter_fourcc(*padded)


def mjpeg_stream() -> Iterator[bytes]:
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
    if CAMERA_FOURCC:
        cap.set(cv2.CAP_PROP_FOURCC, _fourcc_code(CAMERA_FOURCC))

    frame_interval = 0.0
    if CAMERA_FPS and CAMERA_FPS > 0:
        frame_interval = 1.0 / CAMERA_FPS

    encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), CAMERA_JPEG_QUALITY]

    try:
        while True:
            success, frame = cap.read()
            if not success:
                time.sleep(0.1)
                continue

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
    finally:
        cap.release()


__all__ = ["BOUNDARY", "mjpeg_stream"]
