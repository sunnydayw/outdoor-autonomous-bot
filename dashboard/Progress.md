
## 1. High-Level Architecture

### 1.1 Control Path Overview

We finalized the control path using following:

- **Web UI (teleop.html + teleop.js)** hosted on the **Pi 5** (inside a Docker container).
- The operator connects over **VPN** from a client machine (laptop/desktop).
- The **physical controller (Taranis Q X7 + XSR-SIM)** is plugged into the client.
- The browser uses the **Gamepad API** to read stick inputs.
- **teleop.js**:
  - Identifies **FWD** and **STR** axes based on the XSR-SIM mapping.
  - Maps raw axes → `v_cmd` (linear velocity, m/s) and `w_cmd` (angular velocity, rad/s).
  - Applies:
    - Deadzone on STR.
    - One-way mapping for FWD: raw axis ≤ 0 ⇒ `v_cmd = 0`, raw axis > 0 ramps to `V_MAX`.
  - Sends `v_cmd`, `w_cmd` to the backend at a **fixed 20 Hz** using `fetch("/cmd_vel", ...)`.

On the Pi 5:

- A **FastAPI backend**:
  - Hosts the teleop UI and debug page as static files.
  - Exposes `/cmd_vel` endpoint for teleop commands.
  - Maintains central **command state** and **mode** (`idle`, `teleop`, `auto`).
- A **UART control loop**:
  - Runs in a background thread.
  - Polls the command state at a fixed rate (e.g. 50 Hz).
  - Will forward commands to the Pico over UART (integration still to be finalized with existing Pico UART code).

No software E-stop is implemented yet; only timeouts and mode logic are in place at the Pi level. Pico-level watchdog behavior is planned but not implemented here.

# 2. Repository Structure

We defined and started using the following layout for dashbaord( root: `dashboard/`):

```text
dashboard/
├── backend/
│   ├── __init__.py
│   ├── api.py              # FastAPI app, mounts static UI, exposes /cmd_vel, /status, /current_command
│   ├── command_state.py    # Command/mode manager (teleop & auto sources, timeouts, arbitration)
│   ├── uart_bridge.py      # Pi→Pico control loop (skeleton), reads CommandState and will send UART
│   └── main.py             # Entry point: starts UART loop thread + runs uvicorn app
│
├── web/
│   ├── teleop.html         # Main teleop UI (gamepad visualization + v_cmd/w_cmd)
│   ├── teleop.js           # Gamepad polling, mapping, and /cmd_vel POST loop
│   ├── debug.html          # Raw gamepad diagnostic page (separate)
│   └── debug.js            # Shows raw axes/buttons for XSR-SIM mapping
│
├── docker/
│   └── Dockerfile          # Container for backend + static hosting
│
├── requirements.txt        
└── README.md               # High-level instructions (to be expanded later)
```

## 3. Backend Review (Mar 2025)

- Implement the UART bridge: serialize and send `v_cmd`/`w_cmd` over Pi→Pico UART, including reconnect/backoff and basic telemetry logging.
- Add Pi-side safety and limits: clamp v/w to robot-safe bounds, add rate limiting if needed, and integrate a software E-stop/heartbeat path that works with the Pico watchdog.
- Harden the API inputs: validate `v_cmd`/`w_cmd` ranges, optionally reject stale client timestamps, and return informative error responses on bad payloads.
- Cover arbitration logic with tests: unit-test `CommandState` timeouts, mode switching (teleop vs auto), and idle fallback to guard against regressions.
- Clean up unused code: either wire `mode_manager.py` into the flow or remove it to avoid confusion.



#source .venv/bin/activate
# python -m backend.main
        port: str = "/dev/ttyAMA10",
