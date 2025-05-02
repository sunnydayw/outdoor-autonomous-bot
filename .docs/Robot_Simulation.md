# Selecting a Physics Simulation Engine

PyBullet is the primary chooices, An open-source physics engine known for its ease of use in Python and real-time robotics simulation. It supports URDF robot models out-of-the-box and has a Python API for control. 

MuJoCo is also an option to consider, However, MuJoCo uses an MJCF (XML) model format (though it can import URDFs with some effort) and a C/Python API that may require more upfront learning.

Currently the plan is start with PyBullet, in the rover urdf, we have two continuous joins for left and the right wheel. there are three control options:

VELOCITY_CONTROL - directly set a target angular velocity (rad/s) and a maximum force (i.e. torque) the motor can apply
TORQUE_CONTROL - command a raw torque (N·m), letting the physics engine resolve the resulting velocity
POSITION_CONTROL - drive the joint toward a target angle, rarely used on continuous wheels—more for steering or pan/tilt axes.

I will use the simple VELOCITY_CONTROL for the wheel, which mimicking the rover taking velocity command from the raspbeery pi.

The PyBullet simulation 

Plan is to use FastAPI + WebSocket to Broadcast the robot telemetry information in the simulation, micking the robot in real world Broadcast telemetry information to the dashbaord. the Telemetry Broadcast will happen after each physics step 
The Main process runs FastAPI / Uvicorn, it exposes a /ws WebSocket endpoint for bi-directional communication. currently any client that can reach the server at ws://…/ws could connect and issue commands. To prevent unauthorized access, I will implemnt the follwoing in the future to improve security.
Transport Security (TLS)
Token-Based Authentication
Command Validation and Rate-Limiting

The telemetry information will include

Simulated on board Robot IMU reading for orentation, heading, and accessration.
- Gyroscope: reading the body’s angular velocity (getBaseVelocity() gives you world‐frame angular rates; and rotate them into the robot’s local frame).
- Accelerometer: differentiating the linear velocity to get acceleration, then subtracting the gravity vector (and rotating into the body frame).
Robot left and Right wheel RPM
Robot Linear and angular Speed

 