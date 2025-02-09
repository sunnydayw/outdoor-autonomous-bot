# RobotTelemetry Reporting and PC Dashboard

This repository provides the software for real-time telemetry reporting and PID tuning of a differential two-wheel robot. The system consists of a Raspberry Pi Pico running MicroPython for onboard data collection and a PC dashboard built with PyQt5 and PyQtGraph for visualization and live PID tuning.

## Purpose

The primary goal of this solution is to enable effective PID tuning and motor performance monitoring. The PC dashboard allows users to observe key motor parameters in real time and adjust control settings interactively, facilitating rapid tuning and diagnostic feedback.

## System Components

### RobotTelemetry (Pico Side)

- **Telemetry Data Collection:**  
  The Pico gathers diagnostic data such as target RPM, actual RPM, PID terms (P, I, D), computed output, and motor loop times.  
- **Binary Message Format:**  
  Data is packed into a fixed-length binary message with a start delimiter (`0xAA55`), message counter, a 32-bit timestamp, a timeout flag, two sets of motor diagnostics (7 int16 values per motor), and a simple additive checksum.
- **Control Message Reception:**  
  In addition to sending telemetry, the Pico listens for control messages from the PC dashboard. These messages (with a start delimiter `0xCC33`) carry new PID gains and target RPM values, enabling live tuning.

### PC Dashboard (PC Side)

- **Real-Time Visualization:**  
  The dashboard is implemented with PyQt5 and PyQtGraph. It features a three-column layout:
  - **Left Column:** Displays left motor data (RPM, P, I, D, and PWM) in vertically stacked plots.
  - **Center Column:** Displays right motor data in a similar fashion.
  - **Right Column:** Shows system-level stats (loop times, a scaled timeout flag, and message counter differences) along with control settings.
- **User Controls:**  
  - **X-Axis Window Slider:** Adjusts the time window (in seconds) for the plots.
  - **Clear Data Button:** Resets the telemetry buffers and the base timestamp, ensuring the x-axis starts at 0 for each new session.
  - **Reset Scale Button:** Recalculates the y-axis ranges for all plots based on data within the current x-axis window.
  - **Control Command Panel:** Provides input fields for target RPM and PID parameters; these values are packed into a control message and sent to the Pico for live tuning.

## Design Highlights

- **Efficient Data Transmission:**  
  A binary message format minimizes transmission overhead while providing robust error detection via a checksum.
- **Relative Time Stamping:**  
  The telemetry timestamps are converted to relative time (starting at 0) by storing the first received timestamp as a base. This yields a consistent x-axis display during each session.
- **Interactive Visualization:**  
  Dynamic plot scaling and user-adjustable time windows ensure that critical details (e.g., during a speed ramp or when PWM values span a wide range) are visible and informative.

## Usage

1. **Pico Setup:**  
   Load the RobotTelemetry code onto your Raspberry Pi Pico. Ensure the UART connections are properly configured. Create test code and ensure RobotTelemetry is reporting in the main loop.

2. **PC Dashboard:**  
   Run the `dashboard.py` script on your PC. Adjust the serial port settings if necessary.

3. **Operation:**  
   - Monitor real-time motor performance via the dashboard plots.
   - Use the control panel to send new target RPM and PID settings, enabling live PID tuning.
   - Adjust the x-axis window with the slider and use the reset scale and clear data buttons as needed.

## Conclusion

This solution provides an efficient and user-friendly platform for PID tuning and motor performance monitoring in differential drive robots. Its design combines low-overhead telemetry with interactive real-time visualization, supporting rapid control adjustments and detailed diagnostics.

