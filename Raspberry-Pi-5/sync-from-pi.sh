#!/bin/bash

REMOTE_USER="sunnyday"
REMOTE_HOST="192.168.0.50"            # Raspberry Pi IP
REMOTE_SRC="/home/sunnyday/workspace/src"        # Location on the Pi where packages reside
LOCAL_SRC="/Users/sunnyday/Developer/outdoor-autonomous-bot/Raspberry-Pi-5/src"  # Your local workspace src folder

echo "Syncing src folder from Raspberry Pi to local workspace..."
# Pull changes from the Pi to your local workspace
rsync -avz --delete ${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_SRC}/ ${LOCAL_SRC}
echo "Sync complete."