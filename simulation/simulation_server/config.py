# config.py

# Robot URDF and joint indices
URDF_PATH        = "rover/rover.urdf"
LEFT_JID         = 0
RIGHT_JID        = 1

# Wheel geometry
WHEEL_RADIUS     = 5 * 0.0254        # 5 in → meters
WHEEL_SEPARATION = 19 * 0.0254       # 19 in → meters

# Simulation parameters
MAX_FORCE     = 5.0                  # N·m
SIM_FREQUENCY = 50                   # Hz
GRAVITY       = -9.81                # m/s² (downward)
