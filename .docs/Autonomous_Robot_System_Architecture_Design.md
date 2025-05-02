This document outlines the architecture for an autonomous robot system designed to operate in outdoor environments. The system leverages a modular design where each node is responsible for a distinct function, ensuring scalability, ease of maintenance, and flexibility for future enhancements. The initial design is simplified to serve as a proof of concept, demonstrating proper robot operation and overall system integration.

Key Data Flow:

Sensor Data: UART Node → Sensor Processing → Localization Node.
Localization: Localization Node → Global Planner, Local Planner, and Control Node.
Path Planning: Global Planner → Local Planner.
Motion Execution: Local Planner → Control Node → UART Node → Motors.
Obstacle Avoidance: Obstacle Detection Node → Local Planner.

Below is the detailed node-by-node breakdown of the architecture, including the functions, inputs, and outputs of each component.
1. Map Server
Function: Hosts the predefined static map (e.g., occupancy grid, point cloud, or 3D voxel map).
Input:
    None (predefined map loaded at startup).
Output:
    Static map data (published to Global Path Planner and Localization Node).

2. Mission Manager Node
Function: Allows users to input the goal position and monitor system status.
Input:
    User-defined goal (3D coordinates).
Output:
    Goal position (published to Global Path Planner).

3. UART Communication Node
Function: Manages bidirectional communication with Pico 2 Controller hardware (motor controller, IMU, encoders).
Input: Velocity commands (cmd_vel from Control Node).
Output:
    Raw IMU data (accelerometer, gyroscope).
    Raw odometry data (RPM, encoder ticks).
    Motor diagnostics (e.g., temperature, voltage).
Publishes:
    /raw_imu
    /raw_odometry
    /motor_diagnostics

4. Sensor Processing Node
Function: Fuses raw sensor data into usable state estimates.
Input:
    Raw IMU data (from UART Node).
    Raw odometry data (from UART Node).
Output:
    Filtered odometry (position, orientation).
    Processed IMU data (orientation, acceleration).
Publishes:
    /filtered_odometry
    /processed_imu

5. Localization Node
Function: Estimates the robot’s pose in the map frame.
Input:
    Filtered odometry (from Sensor Node).
    Static map (from Map Server).
    Optional: Additional sensor data (e.g., Lidar for scan matching).
Output:
    Estimated pose (x, y, z, roll, pitch, yaw).
Publishes:
    /current_pose

6. Global Path Planner

Function: Computes an optimal path from start to goal.
Input:
    Static map (from Map Server).
    Start pose (from Localization Node).
    Goal pose (from User Interface).
Output:
    Global path (sequence of 3D waypoints).
Publishes:
    /global_path

7. Obstacle Detection Node
Function: Detects dynamic obstacles using sensors (e.g., Lidar, depth cameras).
Input:
    Real-time sensor data (e.g., /lidar_scan from UART/sensor interface).
Output:
    Dynamic obstacle data (local costmap or obstacle list).
Publishes:
    /obstacles

8. Local Planner (Trajectory Generator)
Function: Adjusts the global path to avoid obstacles and generates smooth trajectories.
Input:
    Global path (from Global Planner).
    Current pose (from Localization Node).
    Obstacle data (from Obstacle Detection Node).
Output:
    Safe, collision-free trajectory (short-term path).
Publishes:
    /local_trajectory

9. Control Node
Function: Generates velocity commands to follow the trajectory.
Input:
    Current pose (from Localization Node).
    Desired trajectory (from Local Planner).
    Odometry (from Sensor Processing Node).
Output:
    Linear velocity (vx, vy, vz).
    Angular velocity (roll_rate, pitch_rate, yaw_rate).
Publishes:
    /cmd_vel

10. Diagnostics Node
Function: Monitors system health and logs errors.
Input:
    Motor diagnostics (from UART Node).
    Node statuses (heartbeats from all nodes).
Output:
    Alerts for failures (e.g., motor overheating, sensor disconnects).
Publishes:
    /system_status


