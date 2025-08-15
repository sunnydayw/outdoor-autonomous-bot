# simulator/engine.py

import threading
import time
import queue
import pybullet as p
import pybullet_data

from .control   import apply_drive, compute_imu
from .telemetry import broadcast_telemetry
import config

class RobotSimulator:
    def __init__(self):
        self.latest_state  = {}
        self.command_queue = queue.Queue()
        self.clients       = set()
        self._should_run   = True
        self._thread       = threading.Thread(target=self._run, daemon=True)

    def start(self):
        """Launch the simulation thread."""
        self._thread.start()

    def disconnect(self):
        """Signal the loop to stop and disconnect PyBullet."""
        self._should_run = False
        p.disconnect()

    def _run(self):
        # Initialize physics
        physics_client = p.connect(p.DIRECT)
        p.setAdditionalSearchPath(pybullet_data.getDataPath())
        p.setGravity(0, 0, config.GRAVITY)
        p.loadURDF("plane.urdf")

        # Load robot
        self.robot = p.loadURDF(config.URDF_PATH, basePosition=[0, 0, 0.155])

        # Static battery status
        self.latest_state["status"] = {
            "battery_voltage":    12.5,
            "battery_percentage": 1.0,
            "mode":               "SIM",
            "error_code":         0
        }

        prev_lin = [0.0, 0.0, 0.0]
        dt       = 1 / config.SIM_FREQUENCY

        while self._should_run:
            # Handle all pending drive commands
            while not self.command_queue.empty():
                cmd = self.command_queue.get_nowait()
                if cmd.get("type") == "cmd_vel":
                    apply_drive(self.robot, cmd["linear"], cmd["angular"])

            # Step the physics
            p.stepSimulation()

            # Read pose & velocities
            pos, orn       = p.getBasePositionAndOrientation(self.robot)
            lin_vel, ang_vel = p.getBaseVelocity(self.robot)

            # Compute IMU
            acc_body, gyro_body = compute_imu(orn, lin_vel, prev_lin, ang_vel, dt)
            prev_lin = lin_vel

            # Update shared state
            self.latest_state.update({
                "position":         pos,
                "orientation":      orn,
                "linear_velocity":  lin_vel,
                "angular_velocity": ang_vel,
                "imu_acc":          acc_body,
                "imu_gyro":         gyro_body,
            })

            # Broadcast to WebSocket clients
            broadcast_telemetry(self.clients, self.latest_state)

            # Throttle to target rate
            time.sleep(dt)
