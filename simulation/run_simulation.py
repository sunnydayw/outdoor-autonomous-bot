#!/usr/bin/env python
import os
import time
import signal
import sys
import math

import pybullet as p
import pybullet_data

# ——— Robot & world parameters ———
URDF_PATH = "rover/rover.urdf"

# joint indices
LEFT_JID  = 0
RIGHT_JID = 1

# real-world dimensions (inches → meters)
WHEEL_RADIUS_INCH    = 5
WHEEL_SEPARATION_INCH = 19
WHEEL_RADIUS    = WHEEL_RADIUS_INCH * 0.0254        # ≈0.127 m
WHEEL_SEPARATION = WHEEL_SEPARATION_INCH * 0.0254   # ≈0.4826 m

# maximum torque simulated “motors” can apply (N·m)
MAX_FORCE = 5.0

def cleanup(signum, frame):
    """Ensure the GUI window closes on Ctrl+C."""
    print("\nCaught interrupt — disconnecting PyBullet")
    p.disconnect()
    sys.exit(0)

def drive(robot, linear_vel, angular_vel):
    """
    Convert (v, ω) → (left, right) wheel speeds (rad/s), then apply
    VELOCITY_CONTROL on each wheel joint.
    """
    L = WHEEL_SEPARATION
    # ω = rad/s, v = m/s → wheel angular velocity = v / r
    v_l = (linear_vel - (L/2)*angular_vel) / WHEEL_RADIUS
    v_r = (linear_vel + (L/2)*angular_vel) / WHEEL_RADIUS

    p.setJointMotorControl2(
        bodyIndex=robot,
        jointIndex=LEFT_JID,
        controlMode=p.VELOCITY_CONTROL,
        targetVelocity=v_l,
        force=MAX_FORCE
    )
    p.setJointMotorControl2(
        bodyIndex=robot,
        jointIndex=RIGHT_JID,
        controlMode=p.VELOCITY_CONTROL,
        targetVelocity=v_r,
        force=MAX_FORCE
    )


    
def main():
    # catch Ctrl+C
    signal.signal(signal.SIGINT, cleanup)

    # start the GUI
    client = p.connect(p.GUI)

    # allow loading of both built-in URDFs and our rover’s meshes
    p.setAdditionalSearchPath(pybullet_data.getDataPath())

    # basic physics
    p.setGravity(0, 0, -9.81)

    # load ground plane &  rover
    p.loadURDF("plane.urdf")
    robot = p.loadURDF(
        URDF_PATH,
        basePosition=[0, 0, 0.16],
        useFixedBase=False
    )

    # create GUI sliders
    lin_slider = p.addUserDebugParameter("Linear Velocity (m/s)",
                                         -1.0, 1.0, 0.0)
    ang_slider = p.addUserDebugParameter("Angular Velocity (rad/s)",
                                         -math.pi, math.pi, 0.0)


    # simulation loop
    while True:
        # read slider positions
        v = -p.readUserDebugParameter(lin_slider)
        w = p.readUserDebugParameter(ang_slider)

        # drive your rover
        drive(robot, v, w)

        p.stepSimulation()
        time.sleep(0.001)
        

if __name__ == "__main__":
    main()