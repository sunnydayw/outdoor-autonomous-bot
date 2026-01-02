---
date: 2026-01-02T14:34:54-0500
researcher: Qingtian Chen
git_commit: bbf65bb8a5cf12effd45a296e94883aed8f214a0
branch: main
repository: outdoor-autonomous-bot
topic: "Document the camera streaming setup in old_code before removal"
tags: [research, codebase, old_code, camera_stream, mjpeg, teleop]
status: complete
last_updated: 2026-01-02
last_updated_by: Qingtian Chen
---

# Research: Document the camera streaming setup in old_code before removal

**Date**: 2026-01-02T14:34:54-0500
**Researcher**: Qingtian Chen
**Git Commit**: bbf65bb8a5cf12effd45a296e94883aed8f214a0
**Branch**: main
**Repository**: outdoor-autonomous-bot

## Research Question
Document the camera streaming setup in the `old_code` folder before removing it, capturing details to reuse for a new dashboard.

## Summary
The camera streaming setup in `old_code` is implemented as an OpenCV-based MJPEG generator (`old_code/camera_stream.py`) that yields multipart JPEG frames with a fixed boundary and optional FOURCC fallback. Camera defaults are defined in `old_code/config.py` via environment variables. The client-side page `old_code/static/index.html` renders a Live Camera panel that sets an `<img>` source to `/video/stream` and includes start/stop controls and retry-on-error logic for reconnecting the stream.

## Detailed Findings

### Camera Stream Generator (`old_code/camera_stream.py`)
- Defines constants for the multipart boundary (`BOUNDARY = "frame"`) and a fallback FOURCC (`MJPG`) alongside a lock guarding camera access (`_CAMERA_LOCK`) (`old_code/camera_stream.py:19-22`).
- Converts FOURCC strings to an OpenCV code via `_fourcc_code`, padding/normalizing the input (`old_code/camera_stream.py:25-28`).
- Opens a `cv2.VideoCapture` using the configured device and applies width/height/fps/FOURCC settings if provided (`old_code/camera_stream.py:31-49`).
- Wraps `cap.read()` in `_read_frame`, translating OpenCV read errors to a `RuntimeError` (`old_code/camera_stream.py:52-56`).
- `mjpeg_stream()` acquires the lock, opens the capture with `CAMERA_FOURCC`, computes the frame interval from FPS, and encodes each frame as JPEG (`old_code/camera_stream.py:59-132`).
- If capture reads fail or return empty frames, it attempts a one-time fallback to `MJPG`, then counts failures and raises after 5 consecutive errors (`old_code/camera_stream.py:75-118`).
- Each encoded frame is yielded as a multipart segment with boundary `frame` and `Content-Type: image/jpeg` (`old_code/camera_stream.py:125-129`).
- The generator releases the capture and lock on exit, including when the client closes the connection (`old_code/camera_stream.py:133-139`).

### Camera Configuration Defaults (`old_code/config.py`)
- Camera device and encoding defaults come from environment variables with fallbacks: device `/dev/video0`, 640x480, 12.0 FPS, FOURCC `H264`, JPEG quality 75 (clamped 1-100) (`old_code/config.py:21-28`).

### Client-Side Stream Usage (`old_code/static/index.html`)
- The Live Camera section uses an `<img id="videoStream">` element for displaying the stream (`old_code/static/index.html:40-48`).
- `startStream()` sets `videoEl.src` to `/video/stream?cacheBust=...` and updates the UI status (`old_code/static/index.html:158-167`).
- Stream control toggles between start/stop, clearing the `src` attribute when stopped (`old_code/static/index.html:169-187`).
- On `error`, the client schedules a reconnect attempt after 2 seconds, and on `load` it marks the status as “Streaming” (`old_code/static/index.html:176-199`).

## Code References
- `old_code/camera_stream.py:19-139` - MJPEG stream generator with OpenCV capture, fallback handling, and multipart frame yielding.
- `old_code/config.py:21-28` - Camera configuration defaults and environment overrides.
- `old_code/static/index.html:40-199` - Live Camera UI and client-side stream start/stop/reconnect logic.

## Architecture Documentation
The camera stream is produced by `mjpeg_stream()` as a generator of multipart JPEG chunks labeled with a fixed boundary (`frame`) and `Content-Type: image/jpeg` headers, suitable for an HTTP response body (`old_code/camera_stream.py:125-129`). The client-side page expects a `/video/stream` endpoint that serves this stream and manages retry behavior when the stream errors (`old_code/static/index.html:158-199`). Camera configuration is centralized in `old_code/config.py` and consumed by the stream generator (`old_code/camera_stream.py:10-16`).

## Historical Context (from thoughts/)
- `.ai/thoughts/tickets/camera-research.md` - Notes the intent to document the `old_code` camera streaming setup before removal, to reuse for a new dashboard.

## Related Research
No prior research documents found in `.ai/thoughts/research/`.

## Open Questions
- Where is the HTTP handler that connects `/video/stream` to `old_code.camera_stream.mjpeg_stream()`? (No references found outside `old_code`.)
- Where is `old_code/static/index.html` served from in the current repo?
