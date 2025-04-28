#!/bin/bash

# --- Configuration ---
# Raspberry Pi settings
REMOTE_USER="sunnyday"
REMOTE_HOST="192.168.0.50"            # Raspberry Pi IP
REMOTE_SRC="/home/sunnyday/workspace/src"        # Location on the Pi where packages reside
LOCAL_SRC="/Users/sunnyday/Developer/outdoor-autonomous-bot/Raspberry-Pi-5/src"  # Your local workspace src folder

# --- Step 1: Push local src to Raspberry Pi ---
echo "Pushing local src folder to Raspberry Pi..."
rsync -avz --delete "${LOCAL_SRC}/" "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_SRC}/"

# --- Step 2: Trigger remote build ---
echo "Triggering remote build on Raspberry Pi..."
ssh "${REMOTE_USER}@${REMOTE_HOST}" "source /opt/ros/jazzy/setup.bash && cd ${REMOTE_WS} && colcon build"

echo "Deployment complete."
