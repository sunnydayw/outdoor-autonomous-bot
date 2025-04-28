# Mission Control Dashboard

## Overview  
This project plan to use a browser-based mission control dashboard for the robot. The dashboard consists of a Python-powered backend running on the robot itself and a lightweight web frontend that any modern browser—on Windows, macOS, or iPad—can render. By keeping all core logic on the robot,  simplify deployment and ensure that field operators only need to open a URL to begin monitoring, planning missions, and exercising manual control.

## Why a Browser-Based UI?  
A web interface naturally supports multiple platforms without extra installation or packaging efforts. Modern browsers provide sandboxed environments that isolate the UI from client resources, reducing security risks and making updates frictionless (simply refresh to load the latest version). At the same time, WebGL and HTML5 APIs deliver smooth maps, charts, and control widgets that rival native applications in responsiveness.

## Hosting on the Robot  
The dashboard server is hosted directly on the robot’s onboard computer (e.g. a Raspberry Pi 4 or x86 SBC). This approach:
- Grants immediate access to telemetry, sensor feeds, and mapping data.  
- Allows multiple operators to connect concurrently via WebSockets or HTTP streaming.  
- Leverages any available hardware video encoders to offload camera compression, keeping CPU usage minimal.

By advertising its presence via mDNS (`http://robot.local`), the robot becomes discoverable on the local network without manual IP configuration.

## Networking Strategy  
Initially, the dashboard operates entirely on the same Wi-Fi or Ethernet LAN as the robot, guaranteeing low-latency, reliable connectivity. Later, it can expose the on-robot server through a secure VPN or SSH tunnel. If future requirements call for cloud aggregation—e.g., relaying data through a remote server—that layer can be introduced without altering the browser frontend or backend API design.

## System Architecture  
- **Backend (on robot):**  
  A Python web service (built with Flask, FastAPI, or a ROS websocket bridge) exposes REST endpoints for discrete commands and WebSocket streams for continuous telemetry.  
- **Frontend (in browser):**  
  Subscribes to live data streams, renders interactive maps and status panels, and sends high-level commands back over HTTP or WebSocket.  
- **Control Loops:**  
  Remain entirely on the robot to preserve safety and minimize critical latency. The dashboard handles only visualization and mission-level instructions.

## Low-Latency Video Streaming  
For teleoperation, sub-500 ms video latency is essential. The plan is to use WebRTC, the industry standard for real-time peer-to-peer video:
- Runs natively in all modern browsers over UDP, avoiding TCP buffering delays.  
- Negotiates optimal streaming paths with ICE/STUN/TURN, adapting to network conditions.  
- Automatically adjusts bitrate to maintain smooth playback even under fluctuating bandwidth.  

A WebRTC pipeline typically delivers ~200 ms round-trip latency from the robot’s camera to the browser. While I can start with a simpler MJPEG or ROS `web_video_server` feed for initial tests, migrating to WebRTC will ensure robust, low-lag video suitable for safe remote control.

---

> **Next Steps:**  
> 1. Spin up the Python backend on the robot and verify telemetry streams.  
> 2. Prototype the browser frontend to connect via WebSocket and plot real-time data.  
> 3. Integrate a basic MJPEG or ROS video feed for initial UI tests.  
> 4. Replace the test video stream with a WebRTC server component once telemetry and controls are stable.  


The plan is Use Docker for Deployment: Containerizing both the FastAPI backend and the frontend to keep  consistency between development and production.  Each component (backend API and frontend UI) should run in its own container for modularity

## Backend Containerization:
```
FROM python:3.11-slim-bullseye  
WORKDIR /app  
COPY requirements.txt .  
RUN pip install -r requirements.txt  # Install FastAPI, uvicorn, etc.  
COPY ./app ./app  
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Frontend Containerization
```
# Stage 1: build the frontend
FROM node:20-alpine as build  
WORKDIR /frontend  
COPY package*.json ./  
RUN npm install  
COPY ./src ./src  
COPY ./public ./public  
RUN npm run build  # produces static files in /frontend/dist or /build

# Stage 2: serve the frontend
FROM nginx:1.23-alpine  
COPY --from=build /frontend/dist /usr/share/nginx/html  
```

# Frontend Technology Stack
I plan to use  JavaScript framework like React for the frontend. React is widely used and has a huge ecosystem and community, plenty of tutorials and help if I get stuck​. Its component-based architecture promotes clean separation of concerns, and it can scale from a simple dashboard to a complex app without needing a rewrite.

### UI Component Libarary:
- Chakra UI is a great choice for dashboards – it comes with pre-built responsive components (buttons, forms, layout grids, even charts via extensions) and enforces consistent styling. Chakra is used in some FastAPI full-stack examples​: https://fastapi.tiangolo.com/project-generation#:~:text=,Secure%20password%20hashing%20by%20default

- Material-UI (MUI) is another popular React component framework that implements Google’s Material Design

### State Management
- For a simple dashboard, React’s built-in state and context may be sufficient. Maybe later introduce a state management library like Redux 

# Project Structure and Workspace

/backend/ – Backend (FastAPI) service code and config.
app/ – Your FastAPI application code. This may further contain submodules:
main.py – Initializes FastAPI app, includes route includes (and possibly startup events to init hardware connections, etc).
routers/ – (Optional) if you have many API endpoints, you can organize them into router modules (e.g. telemetry.py, video.py for different API groups).
models/ – (Optional) data models or schemas (could be Pydantic models for request/response).
static/ – (Optional) if serving the frontend or any static images directly from FastAPI, place them here.
requirements.txt or pyproject.toml – Python dependencies (FastAPI, uvicorn, etc).
Dockerfile – Docker instructions to build the backend container (as discussed in Section 1).
(Optional) tests/ – any unit or integration tests for the backend logic.
README.md – instructions specific to setting up/running the backend (if not covered in root README).
/frontend/ – Frontend (React or chosen framework) source code.
src/ – Frontend source files (React components, CSS or styling, utility modules, etc). You might structure this further by feature:
For example, components/ for reusable UI components, pages/ for page-level components or views, etc. Keep related files grouped logically.
public/ – Static assets (if React: the public directory with index.html, possibly placeholder images, etc that are needed at runtime).
package.json – Node.js dependencies and scripts (e.g. React, build scripts).
vite.config.js or similar – If using Vite, the config file for it (or if Create React App, you’ll have configuration hidden or in package.json scripts).
Dockerfile – Docker instructions to build and serve the frontend (as discussed, possibly multi-stage with Node and Nginx).
README.md – instructions specific to setting up the frontend (could include how to run the dev server, how to build for production, etc.).
docker-compose.yml (at project root) – Compose file to define both the backend and frontend services. For example, it will have a service for FastAPI (using backend/Dockerfile) and one for the frontend (using frontend/Dockerfile), with appropriate port mappings. This allows you to run docker-compose up to launch the whole system in one go in development or on the Pi. It also documents how the two pieces connect (you might define a network for them to communicate, or simply use browser->Pi host networking for API calls).
.env (and possibly .env.dev, .env.prod) – Define environment variables for configuration. For instance, you might set SIMULATION_MODE=true in a dev env file (see simulation section), or define API URLs, etc. Docker Compose can load these to configure containers. Secure or device-specific values (like API keys or hardware device paths) can be placed here rather than hardcoding.
README.md (at project root) – The main documentation for the project, describing how to set up the dev environment, how to run the app locally, how to deploy to Pi, etc. Essentially, instructions for yourself or anyone else who might work on it later. Since this plan is meant for internal use, it could evolve into that README.


# Development Workflow: With this setup, typical dev workflow would be:

- Run the FastAPI app locally (e.g. uvicorn app.main:app --reload) or via Docker if you prefer. Ensure it’s accessible (by default on http://localhost:8000). Enable CORS in FastAPI so that your frontend (which will run on a different port during dev, e.g. 5173 for Vite) can talk to it. This involves adding from fastapi.middleware.cors import CORSMiddleware and allowing http://localhost:5173 in the app startup if needed.

- Run the React dev server: e.g. npm run dev (if using Vite). This will serve the frontend on its own local dev server with hot-reload. It will proxy or call the FastAPI endpoints for data. During development, you can configure the proxy or just have the React code call http://localhost:8000/api/... for APIs.