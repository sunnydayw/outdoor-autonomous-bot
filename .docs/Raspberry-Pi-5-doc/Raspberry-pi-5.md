# Hardware
Raspberry Pi 5 8GB
256GB SSD M.2 NvM2 Pcie 3.0

Raspberry Pi M.2 HAT+
- support PCIe 2.0
- support 450MBps data transfer to and from NVMe SSD drives
Raspberry Pi Cooling Fan

# Software
## Current Setup
Pi IP address 192.168.0.51
Installed Ubuntu Server 24.04.3 LTS (64-Bits)
To install ROS2 Jazzy https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html

## To Install rosbridge (and rosapi) 
sudo apt update
sudo apt install -y curl gnupg2 lsb-release

- Install/refresh the ROS key (Maybe not needed)
sudo mkdir -p /usr/share/keyrings
curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key \
| sudo gpg --dearmor -o /usr/share/keyrings/ros-archive-keyring.gpg

- Clean stale indexes and refresh
sudo apt clean
sudo rm -rf /var/lib/apt/lists/*
sudo apt update
sudo apt full-upgrade -y

- Install rosbridge (and rosapi). Add web_video_server later for camera.
sudo apt install -y \
  ros-jazzy-rosbridge-server \
  ros-jazzy-rosapi






- (Optional, for camera MJPEG later—if available on your distro)
sudo apt install -y ros-jazzy-web-video-server

## how to use ROS
Create ROS2 Publisher and Subscriber Nodes

source /opt/ros/jazzy/setup.bash

# To run remote test setup

Serve the webpage
cd robot-ui
python3 -m http.server 8000

- run the ros bridge
ros2 launch rosbridge_server rosbridge_websocket_launch.xml address:=0.0.0.0 port:=9090
- run python pico bridge

# To build workspace - colcon build

to create package, in src run ros2 pkg create --build-type ament_python package-name
inside the package, find the folder with package name,  create python file.
exit one level, edit package.xml edit the description and maintainer, and add dependeny package

<exec_depend>rclpy</exec_depend>
<exec_depend>std_msgs</exec_depend>

Next, edit the setup.py file and define the entry point
# function name, package name.python source file : name of the function
'talker = publisher.publisher:main',
'listener = publisher.subscriber:main',

  <description>This is a publisher node</description>
  <maintainer email="chenqingtian@gmail.com">sunnyday</maintainer>
  <license>TODO: License declaration</license>


Doubel Check missing dependencies by running
rosdep install -i --from-path src --rosdistro jazzy -y

Build the package colcon build --package-select package_name

now lets source the new workspace, source ~/workspace/install/setup.bash

To run the package, ros2 run package_name talker (giving_name in the setup.py file)Create ROS2 Publisher and Subscriber Nodes

source /opt/ros/jazzy/setup.bash

to build workspace - colcon build

to create package, in src run ros2 pkg create --build-type ament_python package-name
inside the package, find the folder with package name,  create python file.
exit one level, edit package.xml edit the description and maintainer, and add dependeny package

<exec_depend>rclpy</exec_depend>
<exec_depend>std_msgs</exec_depend>

Next, edit the setup.py file and define the entry point
# function name, package name.python source file : name of the function
'talker = publisher.publisher:main',
'listener = publisher.subscriber:main',

  <description>This is a publisher node</description>
  <maintainer email="chenqingtian@gmail.com">sunnyday</maintainer>
  <license>TODO: License declaration</license>


Doubel Check missing dependencies by running
rosdep install -i --from-path src --rosdistro jazzy -y

Build the package colcon build --package-select package_name

now lets source the new workspace, source ~/workspace/install/setup.bash

To run the package, ros2 run package_name talker (giving_name in the setup.py file)