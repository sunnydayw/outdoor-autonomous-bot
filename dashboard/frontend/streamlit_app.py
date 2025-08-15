# streamlit_app.py
import streamlit as st
import websocket
import json
import threading
import time
import plotly.graph_objects as go
import numpy as np
from collections import deque
import plotly.express as px
from datetime import datetime
import queue

global_telemetry_queue = queue.Queue()  # Use a global queue for cross-thread communication

# Initialize session state
if 'telemetry_history' not in st.session_state:
    st.session_state.telemetry_history = {
        'timestamps': deque(maxlen=100),
        'velocity': deque(maxlen=100),
        'acceleration': deque(maxlen=100),
        'angular_velocity': deque(maxlen=100),
        'position': deque(maxlen=100),
    }

if 'websocket_connected' not in st.session_state:
    st.session_state.websocket_connected = False

# WebSocket connection
class TelemetryWebSocket:
    def __init__(self):
        self.ws = None
        self.latest_data = None
        self.connected = False
        self.should_reconnect = True
        
    def connect(self):
        def on_open(ws):
            self.connected = True
            st.session_state.websocket_connected = True
            print("WebSocket connected")
            
        def on_message(ws, message):
            self.latest_data = json.loads(message)
            global_telemetry_queue.put(self.latest_data)  # Use global queue
            
        def on_error(ws, error):
            print(f"WebSocket error: {error}")
            
        def on_close(ws, close_status_code, close_msg):
            self.connected = False
            st.session_state.websocket_connected = False
            print("WebSocket connection closed")
            if self.should_reconnect:
                time.sleep(1)
                self.connect()
        
        websocket.enableTrace(True)
        self.ws = websocket.WebSocketApp(
            "ws://backend:8000/ws",  # Changed from localhost to backend service name
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close
        )
        
        wst = threading.Thread(target=self.ws.run_forever)
        wst.daemon = True
        wst.start()

    def update_history(self, data):
        # This method will be called from the main thread with Streamlit context
        if not data:
            return
            
        timestamp = datetime.now().strftime('%H:%M:%S')
        st.session_state.telemetry_history['timestamps'].append(timestamp)
        
        vel = data.get('velocity', {}).get('linear', {})
        st.session_state.telemetry_history['velocity'].append(
            (vel.get('x', 0), vel.get('y', 0), vel.get('z', 0))
        )
        
        imu = data.get('imu', {})
        acc = imu.get('linear_acceleration', {})
        st.session_state.telemetry_history['acceleration'].append(
            (acc.get('x', 0), acc.get('y', 0), acc.get('z', 0))
        )
        
        ang_vel = imu.get('angular_velocity', {})
        st.session_state.telemetry_history['angular_velocity'].append(
            (ang_vel.get('x', 0), ang_vel.get('y', 0), ang_vel.get('z', 0))
        )
        
        pos = data.get('pose', {}).get('position', {})
        st.session_state.telemetry_history['position'].append(
            (pos.get('x', 0), pos.get('y', 0))
        )

    def send_command(self, linear_x, angular_z):
        if not self.ws or not self.connected:
            print("WebSocket not connected, attempting to reconnect...")
            self.connect()
            time.sleep(0.5)  # Wait for connection
            
        if self.connected:
            try:
                twist_command = {
                    "command": {
                        "type": "twist",
                        "target_linear": {"x": linear_x, "y": 0.0, "z": 0.0},
                        "target_angular": {"x": 0.0, "y": 0.0, "z": angular_z}
                    }
                }
                self.ws.send(json.dumps(twist_command))
            except Exception as e:
                print(f"Error sending command: {e}")
                self.connected = False

# Initialize WebSocket connection
ws_client = TelemetryWebSocket()

# Only connect the first time the script runs
if not st.session_state.websocket_connected:
    ws_client.connect()

# Process any telemetry data in the queue
while not global_telemetry_queue.empty():
    try:
        data = global_telemetry_queue.get_nowait()
        ws_client.update_history(data)
    except queue.Empty:
        break

# Streamlit UI
st.title("Ground Robot Telemetry Dashboard")

# Create two columns for the layout
col1, col2 = st.columns(2)

with col1:
    st.subheader("Robot Controls")
    
    # Speed control
    speed = st.slider("Speed (m/s)", -1.0, 1.0, 0.0, 0.1)
    turn_rate = st.slider("Turn Rate (rad/s)", -1.0, 1.0, 0.0, 0.1)
    
    # Control buttons
    if st.button("Forward"):
        ws_client.send_command(0.5, 0.0)
    
    col1_1, col1_2, col1_3 = st.columns(3)
    with col1_1:
        if st.button("Left"):
            ws_client.send_command(0.0, 0.5)
    with col1_2:
        if st.button("Stop"):
            ws_client.send_command(0.0, 0.0)
    with col1_3:
        if st.button("Right"):
            ws_client.send_command(0.0, -0.5)
            
    if st.button("Backward"):
        ws_client.send_command(-0.5, 0.0)

    # Custom velocity control
    if st.button("Send Custom Velocity"):
        ws_client.send_command(speed, turn_rate)

with col2:
    st.subheader("Position Plot")
    if len(st.session_state.telemetry_history['position']) > 0:
        positions = list(st.session_state.telemetry_history['position'])
        fig = px.scatter(
            x=[p[0] for p in positions],
            y=[p[1] for p in positions],
            title="Robot Position"
        )
        fig.update_layout(
            xaxis_title="X Position (m)",
            yaxis_title="Y Position (m)"
        )
        st.plotly_chart(fig)

# Telemetry plots
st.subheader("Telemetry Data")
tab1, tab2, tab3 = st.tabs(["Velocity", "Acceleration", "Angular Velocity"])

with tab1:
    if len(st.session_state.telemetry_history['velocity']) > 0:
        velocities = list(st.session_state.telemetry_history['velocity'])
        fig = go.Figure()
        fig.add_trace(go.Scatter(y=[v[0] for v in velocities], name="X", mode="lines"))
        fig.add_trace(go.Scatter(y=[v[1] for v in velocities], name="Y", mode="lines"))
        fig.add_trace(go.Scatter(y=[v[2] for v in velocities], name="Z", mode="lines"))
        fig.update_layout(title="Velocity", xaxis_title="Time", yaxis_title="m/s")
        st.plotly_chart(fig)

with tab2:
    if len(st.session_state.telemetry_history['acceleration']) > 0:
        accels = list(st.session_state.telemetry_history['acceleration'])
        fig = go.Figure()
        fig.add_trace(go.Scatter(y=[a[0] for a in accels], name="X", mode="lines"))
        fig.add_trace(go.Scatter(y=[a[1] for a in accels], name="Y", mode="lines"))
        fig.add_trace(go.Scatter(y=[a[2] for a in accels], name="Z", mode="lines"))
        fig.update_layout(title="Acceleration", xaxis_title="Time", yaxis_title="m/s²")
        st.plotly_chart(fig)

with tab3:
    if len(st.session_state.telemetry_history['angular_velocity']) > 0:
        ang_vels = list(st.session_state.telemetry_history['angular_velocity'])
        fig = go.Figure()
        fig.add_trace(go.Scatter(y=[v[0] for v in ang_vels], name="Roll", mode="lines"))
        fig.add_trace(go.Scatter(y=[v[1] for v in ang_vels], name="Pitch", mode="lines"))
        fig.add_trace(go.Scatter(y=[v[2] for v in ang_vels], name="Yaw", mode="lines"))
        fig.update_layout(title="Angular Velocity", xaxis_title="Time", yaxis_title="rad/s")
        st.plotly_chart(fig)

# Status information
if ws_client.latest_data and 'status' in ws_client.latest_data:
    st.subheader("Robot Status")
    st.json(ws_client.latest_data['status'])

# Show latest telemetry indicator
if len(st.session_state.telemetry_history['timestamps']) > 0:
    st.success(f"Latest telemetry received at: {st.session_state.telemetry_history['timestamps'][-1]}")
else:
    st.warning("No telemetry data received yet. Waiting for data from backend...")

# Auto-refresh the dashboard every 1 second to get new telemetry data
import time
st.empty()
time.sleep(1)
st.rerun()