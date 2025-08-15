Pi IP address 192.168.0.50
Installed Ubuntu 24.04.1 LTS
To install ROS2 Jazzy https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html

Create ROS2 Publisher and Subscriber Nodes

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