FROM ros:jazzy-ros-base
RUN apt-get update && apt-get install -y \
    ros-jazzy-demo-nodes-cpp \
    ros-jazzy-foxglove-bridge \
    ros-jazzy-tf2-ros

WORKDIR /workspace
VOLUME ["/workspace"]

# run command to build container -> docker build -t ros_dev .
# to start container -> docker run -it --rm -v /Users/sunnyday/Developer/outdoor-autonomous-bot:/workspace ros_dev
