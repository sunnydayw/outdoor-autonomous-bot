FROM ros:jazzy-ros-base
RUN apt-get update && apt-get install -y \
    ros-jazzy-demo-nodes-cpp \
    ros-jazzy-foxglove-bridge \
    ros-jazzy-tf2-ros \
    xvfb fluxbox novnc websockify x11vnc \
    python3-colcon-common-extensions \
    git curl && \
    rm -rf /var/lib/apt/lists/*

# Install noVNC
RUN git clone https://github.com/novnc/noVNC.git /opt/noVNC

# Startup script to launch graphical environment
RUN echo '#!/bin/bash\n\
export DISPLAY=:0\n\
Xvfb :0 -screen 0 1280x800x24 &\n\
sleep 2\n\
fluxbox &\n\
x11vnc -display :0 -forever -nopw -shared -rfbport 5900 &\n\
/opt/noVNC/utils/novnc_proxy --vnc localhost:5900 --listen 6080 &\n\
sleep 3\n\
bash' > /usr/local/bin/start-vnc.sh \
&& chmod +x /usr/local/bin/start-vnc.sh

# Create workspace
WORKDIR /workspace
VOLUME ["/workspace"]

# Persistent environment setup
RUN echo "export DISPLAY=:0" >> ~/.bashrc
RUN echo "source /opt/ros/jazzy/setup.bash" >> ~/.bashrc

# run command to build container -> docker build -t ros_dev .
# to start container -> docker run -it --rm -v /Users/sunnyday/Developer/outdoor-autonomous-bot:/workspace ros_dev
