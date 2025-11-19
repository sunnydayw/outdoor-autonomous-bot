
# 定义数据结构/总体接口设计思路 Low-Level API

This document defines the low-level API between:
- **Pi 5** – runs planner, localization, and high-level control.
- **Pi Pico** – runs motor control, low-level drivers, encoder and battery sampling.

The goal is to keep a **narrow and stable interface** between high-level and low-level code, so that:

- The planner and localization logic can evolve independently of motor driver details.
- The motor controller can be replaced or upgraded without breaking high-level code.

在 Pi 5 和 Pi Pico 之间，只保留一条很窄且清晰的 API：
- **上行（Pi 5 → Pi Pico）：
    - VelocityCommand（v, ω）
    - Stop
    - EmergencyStop
    - 配置/限幅类命令，可选

- **上下行（Pi Pico → Pi 5）：
    - DriveFeedback（当前 v/ω + encoder + 状态）
    - BatteryStatus
    - LowLevelStatus（fault、E-stop 状态等）
    - IMU 视连接方式而定

## 3. Common Header
All messages share a common header.
```c
struct Header {
    uint32  seq;        // sequence number recommended for debugging and detection of drops
    double  stamp;      // timestamp in seconds (since boot or UNIX time)
}
```

## 上行：Planner → Motor Controller
### Command Type Enum
```c
enum CommandType {
    CMD_SET_VELOCITY   = 0;  // normal velocity command
    CMD_STOP           = 1;  // smooth stop, decelerate to zero
    CMD_EMERGENCY_STOP = 2;  // hard stop, brake immediately and hold
}
```
可以后续再加 CMD_SET_LIMITS、CMD_CLEAR_ESTOP 之类

### VelocityCommand
```c
struct VelocityCommand {
    Header      header;

    CommandType type;          // usually CMD_SET_VELOCITY, or STOP / EMERGENCY_STOP

    // Velocity command in robot base frame
    float       v;             // linear velocity [m/s], forward +, backward -
    float       omega;         // angular velocity [rad/s], CCW +

    // Optional limits (can be ignored by Pico if not used)
    float       max_linear_accel;   // [m/s^2], 0 or negative = use default
    float       max_angular_accel;  // [rad/s^2]

    uint32      command_id;    // for matching acks / debugging
}
``` 
- 当 type == CMD_SET_VELOCITY： Pico 按 v, omega 做闭环控制。
- 当 type == CMD_STOP：忽略 v, ω；采用内部减速曲线平滑减速到 0。
- 当 type == CMD_EMERGENCY_STOP：立即切断/急停，电机输出进入安全状态，并记录 E-stop 状态；之后所有 CMD_SET_VELOCITY 可以直接忽略，直到收到单独的 ClearEstop 或 reset。

### E-stop 清除命令
紧急停机往往需要一个显式清除步骤，可以单独定义：
```c
struct ClearEstopCommand {
    Header header;
    uint32 request_id;
}
```

## 下行：Motor Controller → Planner
### DriveFeedback（运动相关反馈）
```c
struct DriveFeedback {
    Header header;

    // Estimated motion in base frame
    float  v_meas;          // measured linear velocity [m/s]
    float  omega_meas;      // measured angular velocity [rad/s]

    // Raw wheel encoder readings
    int32  left_ticks;      // cumulative ticks since boot or since last reset
    int32  right_ticks;     // same as above

    float  left_rpm;        // optional: wheel RPM for debugging / diag
    float  right_rpm;

    uint32 status_flags;    // bitmask: motor enabled, closed-loop active, etc.
}
```

status_flags 可包含：
- bit 0: motors_enabled
- bit 1: velocity_control_active
- bit 2: low_level_fault_present
- bit 3: overcurrent_warning
- bit 4: overtemp_warning
…（你可以后面扩展）

Planner / localization 使用：
left_ticks / right_ticks + IMU 做 odometry。
v_meas / omega_meas 可以做闭环监测 & debug。

### BatteryStatus（电池反馈）
```c
struct BatteryStatus {
    Header  header;

    float   voltage;        // [V]
    float   current;        // [A], positive = discharging, negative = charging
    float   soc;            // state of charge [%], 0-100 (optional if no fuel gauge)
    float   temperature;    // [°C], if available

    uint32  status_flags;   // e.g., low_battery_warning, critically_low, etc.
}
```

status_flags 示例：
bit 0: low_battery_warning
bit 1: critically_low_battery
bit 2: battery_temp_high
bit 3: battery_temp_low

### LowLevelStatus / FaultStatus（低层状态）
```c
struct LowLevelStatus {
    Header  header;

    uint32  fault_flags;    // bitmask of latched faults
    uint32  warning_flags;  // bitmask of non-latched warnings

    bool    estop_active;   // whether E-stop is currently active
    uint8   estop_source;   // 0 = none, 1 = HW button, 2 = SW command, 3 = driver_fault, ...

    uint32  uptime_ms;      // time since Pico boot, for debug
}
```

fault_flags 例子：
bit 0: driver_overcurrent_fault
bit 1: driver_overtemp_fault
bit 2: encoder_fault
bit 3: imu_comm_fault (若 IMU 走 Pico 才有意义)
这些 flag 真正的具体编码可以后面再定义，重要的是预留一个 bitmask，避免以后没位置扩展。


# Timing and Frequency Guidelines
The following are recommended target rates and can be adjusted as needed:
- VelocityCommand (Pi 5 → Pico):
    - 20–50 Hz (e.g., every 20–50 ms).
- DriveFeedback (Pico → Pi 5):
    - 50–100 Hz, aligned with control loop / encoder readout.
- BatteryStatus (Pico → Pi 5):
    - 1–5 Hz, depending on how quickly battery values change.
- LowLevelStatus (Pico → Pi 5):
    - 1–10 Hz under normal operation.
    - Immediately on fault / E-stop transitions.
- ImuMeasurement:
    - 100–200 Hz.

## IMU 数据结构
```c
struct ImuMeasurement {
    Header header;

    // Linear acceleration in m/s^2
    float accel_x;
    float accel_y;
    float accel_z;

    // Angular velocity in rad/s
    float gyro_x;
    float gyro_y;
    float gyro_z;

    // Optional: magnetic field or orientation, if available
    float mag_x;
    float mag_y;
    float mag_z;

    // Optional orientation estimate (e.g., from onboard fusion)
    float qx;
    float qy;
    float qz;
    float qw;

    uint32 status_flags; // sensor ok, saturation, etc.
}
```


# RobotPose
struct RobotPose {
    string frame_id;      // 例如 "court_map"
    double timestamp;     // 秒或毫秒

    double x;
    double y;
    double z;             // 球场可以固定 0，预留给未来坡度/高度

    double roll;
    double pitch;
    double yaw;

    double[36] covariance; // 可选，用于标记不确定性
    string source;         // "RTK", "VISION", "FUSED"（仅供调试）
}


服务接口可以长这样：

interface LocalizationProvider {
    RobotPose get_current_pose(string frame_id);
    RobotPose get_pose_at_time(string frame_id, double timestamp); // 可选
    FrameTransform get_transform(string from_frame, string to_frame); // 可选
}

在实现时，可以有多个 provider：
- RTKLocalizationProvider
- VisualOdometryProvider
- FusionLocalizationProvider

然后在系统启动时，指定当前使用哪个 provider 或者用 Fusion 作为默认。

所有传感器先喂给定位/融合模块（LF）,LF 对外只暴露一个统一的「Localization API」，输出 RobotPose；路径规划、任务执行、UI 都只依赖这个 API，不直接访问传感器。

对于球的位置，也可以抽象成类似的结构：

struct BallDetection {
    int    id;
    double timestamp;

    // 在与 RobotPose 相同的 frame_id 下的坐标
    double x;
    double y;

    double confidence;
}

上层的路径规划只需要知道：
当前机器人 RobotPose
当前待处理的 BallDetection[] 列表
