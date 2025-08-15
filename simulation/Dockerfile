# simulation/Dockerfile
FROM python:3.9-slim

# install build dependencies for PyBullet
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        python3-dev \
        libgl1-mesa-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY rover/ rover/
COPY simulation_server/ simulation_server/
CMD ["python", "simulation_server/server.py"]
