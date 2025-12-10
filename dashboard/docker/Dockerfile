# docker/Dockerfile

# 1. Base image – Python 3.11 slim is fine on Pi 5 (ARM64 images exist)
FROM python:3.11-slim

# 2. Create work directory inside the container
WORKDIR /app

# 3. System dependencies (if you need any; keep minimal for now)
#    Uncomment / extend if you later need build tools or extra libs.
# RUN apt-get update && apt-get install -y --no-install-recommends \
#     build-essential \
#     && rm -rf /var/lib/apt/lists/*

# 4. Copy and install Python dependencies first (better cache utilization)
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# 5. Copy application code
#    Copy backend and web folders into the container image.
COPY backend /app/backend
COPY web /app/web

# 6. Environment settings
ENV PYTHONUNBUFFERED=1 \
    UVICORN_HOST=0.0.0.0 \
    UVICORN_PORT=8000

# 7. Expose the port FastAPI will listen on
EXPOSE 8000

# 8. Default command: run the FastAPI app with uvicorn
#
#    backend.api:app  -> module:object path
#    If later you add startup events that launch the UART loop,
#    they'll be triggered automatically when uvicorn starts.
# CMD ["uvicorn", "backend.api:app", "--host", "0.0.0.0", "--port", "8000"]
CMD ["python", "-m", "backend.main"]

# # Note: Example build and run commands
# # Build
# docker build -f docker/Dockerfile -t robot-teleop .
# # Run (example) – mapping UART device into the container
# docker run --rm \
#   --name robot-teleop \
#   -p 8000:8000 \
#   --device=/dev/ttyACM0:/dev/ttyACM0 \
#   robot-teleop

## Adjust /dev/ttyACM0 to whatever device your Pico appears as.