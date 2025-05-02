## Robot-to-Dashboard Communication (WebSocket JSON)

The robot streams telemetry to a browser-based dashboard over a WebSocket using JSON. This non-ROS interface prioritizes:

- **Human readability**: easy inspection in browser dev tools or logs  
- **Cross-platform support**: any modern browser can parse JSON  
- **Loose coupling**: UI can evolve without changing robot code

### Message Structure

Use a shallow **nested JSON** schema to group related fields:

- Top-level keys for major categories (`pose`, `velocity`, `imu`, `command`, `status`)  
- A `timestamp` (Unix sec or ms) for synchronization and latency tracking  
- Arrays or objects for vectors/quaternions  

```json
{
  "timestamp": 1682979440000,
  "pose": {
    "position":    { "x": 1.23, "y": 4.56, "z": 0.00 },
    "orientation": { "x": 0.0,  "y": 0.0,  "z": 0.707, "w": 0.707 }
  },
  "velocity": {
    "linear":  { "x": 0.5, "y": 0.0, "z": 0.0 },
    "angular": { "x": 0.0, "y": 0.0, "z": 0.1 }
  },
  "imu": {
    "orientation":        { "x": 0.0, "y": 0.0, "z": 0.707, "w": 0.707 },
    "angular_velocity":   { "x": 0.01, "y": -0.00, "z": 0.0001 },
    "linear_acceleration":{ "x": -0.003, "y": 0.0,  "z": -9.81 }
  },
  "command": {
    "type":          "twist",
    "target_linear":  { "x": 0.5, "y": 0.0, "z": 0.0 },
    "target_angular": { "z": 0.1 }
  },
  "status": {
    "battery_voltage":    12.5,
    "battery_percentage": 0.82,
    "mode":               "AUTO",
    "error_code":         0
  }
}
```

## Internal Controller–Planner Communication (Python Messaging)

Within the robot’s Python code, the low-level controller and high-level planner exchange rich data without serialization overhead. Use typed dataclasses (or nested dicts) that mirror your WebSocket schema and ROS conventions.

``` python

from dataclasses import dataclass
from typing import Tuple

@dataclass
class Pose:
    x: float; y: float; z: float
    qx: float; qy: float; qz: float; qw: float

@dataclass
class Twist:
    vx: float; vy: float; vz: float
    wx: float; wy: float; wz: float

@dataclass
class ImuData:
    orientation: Pose
    angular_velocity: Tuple[float, float, float]
    linear_acceleration: Tuple[float, float, float]

@dataclass
class RobotStatus:
    battery_voltage: float
    mode: str
    error_code: int

@dataclass
class ControlCommand:
    type: str                # e.g. "twist", "set_target"
    target_twist: Twist      # desired linear & angular velocities

@dataclass
class RobotState:
    pose: Pose
    velocity: Twist
    imu: ImuData
    status: RobotStatus

```

## ROS-to-ROS Communication (ROS Messages between Nodes)
When operating within a ROS ecosystem, leverage standard ROS messages on dedicated topics instead of ad-hoc payloads:

### Guidelines:

- Separate topics for each data stream (modular and subscribable)
- Include headers (std_msgs/Header) for timestamps and frame IDs
- Avoid packing JSON into strings—use typed fields so rviz, rosbag, and rqt_plot work out-of-the-box
- For custom data, define a .msg file with specific fields rather than a generic catch-all

| Data                | Recommended ROS Type               | Topic Example      |
|---------------------|------------------------------------|--------------------|
| Pose + Twist        | `nav_msgs/Odometry`                | `/odom`            |
|                     | _or_ `geometry_msgs/PoseStamped` + `TwistStamped` | `/pose`, `/vel`   |
| IMU                 | `sensor_msgs/Imu`                  | `/imu/data`        |
| Velocity Command    | `geometry_msgs/Twist`              | `/cmd_vel`         |
| Battery State       | `sensor_msgs/BatteryState`         | `/battery_state`   |
| System Status       | `diagnostic_msgs/DiagnosticStatus` | `/diagnostics`     |


## Unit for parameter
Linear velocities | meters per second (m/s).
Angular velocities | radians per second (rad/s)