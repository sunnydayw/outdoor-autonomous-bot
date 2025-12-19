# backend/main.py
from __future__ import annotations

import logging
import threading
import time
from typing import Optional

import uvicorn

from .api import app, command_state
from .uart_bridge import control_loop as uart_control_loop


logger = logging.getLogger(__name__)


def start_uart_thread(loop_hz: float = 50.0) -> threading.Thread:
    """
    Start the Pi→Pico UART control loop in a background daemon thread.

    The loop:
      - Calls command_state.get_current_command() at a fixed rate.
      - Sends v_cmd / w_cmd to the Pico over UART (implemented in uart_bridge.py).
    """
    period_s = 1.0 / loop_hz

    def _run():
        logger.info("UART control loop started (%.1f Hz)", loop_hz)
        try:
            uart_control_loop(command_state, period_s=period_s)
        except Exception:
            logger.exception("UART control loop terminated due to an exception")

    t = threading.Thread(target=_run, name="uart-control-loop", daemon=True)
    t.start()
    return t


def main(
    host: str = "0.0.0.0",
    port: int = 8000,
    loop_hz: float = 50.0,
) -> None:
    """
    Entry point for the robot backend:

      - Starts UART loop thread.
      - Runs FastAPI app via uvicorn.

    The same command_state instance is shared between:
      - HTTP handlers (teleop /cmd_vel, /status, etc.)
      - UART loop (Pi→Pico control).
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    logger.info("Starting robot backend (host=%s, port=%d, loop_hz=%.1f)", host, port, loop_hz)

    # Start UART loop in the background
    start_uart_thread(loop_hz=loop_hz)

    # Run FastAPI app
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
        access_log=False,

    )


if __name__ == "__main__":
    main()
