# simulator/control.py

import pybullet as p
from config import LEFT_JID, RIGHT_JID, WHEEL_RADIUS, WHEEL_SEPARATION, MAX_FORCE, GRAVITY

def apply_drive(robot, linear: float, angular: float):
    """Convert (linear, angular) into left/right wheel velocities and apply."""
    L = WHEEL_SEPARATION
    v_l = (linear - (L/2)*angular) / WHEEL_RADIUS
    v_r = (linear + (L/2)*angular) / WHEEL_RADIUS

    p.setJointMotorControl2(robot, LEFT_JID,
                            controlMode=p.VELOCITY_CONTROL,
                            targetVelocity=v_l,
                            force=MAX_FORCE)
    p.setJointMotorControl2(robot, RIGHT_JID,
                            controlMode=p.VELOCITY_CONTROL,
                            targetVelocity=v_r,
                            force=MAX_FORCE)

def compute_imu(orn, lin_vel, prev_lin, ang_vel, dt):
    """Compute body-frame accel & gyro from world-frame velocities."""
    # 1) World-frame linear acceleration
    acc_world = [(lin_vel[i] - prev_lin[i]) / dt for i in range(3)]
    # Add gravity back so IMU measures gravity + inertia
    acc_world[2] += -GRAVITY

    # 2) Build world→body rotation matrix
    m = p.getMatrixFromQuaternion(orn)
    R = [m[0:3], m[3:6], m[6:9]]  # 3×3

    # 3) Transform acceleration & angular velocity into body frame
    acc_body  = [sum(R[r][c] * acc_world[c] for c in range(3)) for r in range(3)]
    gyro_body = [sum(R[r][c] * ang_vel[c]    for c in range(3)) for r in range(3)]

    return acc_body, gyro_body
