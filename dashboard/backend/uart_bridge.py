# backend/uart_bridge.py
import time
from .command_state import CommandState, ControlMode

import logging
logger = logging.getLogger(__name__)


def control_loop(cmd_state: CommandState, period_s: float = 0.02) -> None:
    """
    Blocking loop that:
      - Reads current (v, w, mode) from cmd_state.
      - Applies Pi-side limits.
      - Sends commands to the Pico over UART.

    Runs forever; caller is expected to start it in a background thread.
    """
    last_log_ts = 0.0
    LOG_INTERVAL_S = 0.5   # log at most twice per second

    while True:
        v_cmd, w_cmd, mode = cmd_state.get_current_command()

        # TODO: clamp to Pi-side limits here
        # v_cmd, w_cmd = clamp(v_cmd, w_cmd)

        # TODO: send to Pico via your UART protocol
        # send_to_pico(v_cmd, w_cmd)

        # now = time.monotonic()
        # if now - last_log_ts > LOG_INTERVAL_S:
        #     logger.info("UART loop: mode=%s, v=%.3f, w=%.3f", mode.value, v_cmd, w_cmd)
        #     last_log_ts = now

        time.sleep(period_s)
