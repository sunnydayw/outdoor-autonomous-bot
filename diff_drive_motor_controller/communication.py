import json
import machine
import time

class SerialComm:
    def __init__(self, tx_pin=0, rx_pin=1, baudrate=115200):
        """
        Initialize serial communication.
        :param tx_pin: UART TX pin number
        :param rx_pin: UART RX pin number
        :param baudrate: Serial baudrate
        """
        self._uart = machine.UART(0, baudrate=baudrate, tx=machine.Pin(tx_pin), rx=machine.Pin(rx_pin))
        self._msg_counter = 0
        self._last_send_time = time.ticks_ms()
        
    def publish(self, left_diagnostics, right_diagnostics):
        """
        Send motor data in ROS-like message format.
        """
        current_time = time.ticks_ms()
        
        message = {
            "header": {
                "stamp": time.ticks_ms(),  # Timestamp in milliseconds.
                "frame_id": "motor_controller"
            },
            "left_motor": {
                "target_rpm": left_diagnostics.get("target_rpm", 0),
                "current_rpm": left_diagnostics.get("current_rpm", 0),
                "p_term": left_diagnostics.get("p_term", 0),
                "i_term": left_diagnostics.get("i_term", 0),
                "d_term": left_diagnostics.get("d_term", 0),
                "output": left_diagnostics.get("output", 0)
            },
            "right_motor": {
                "target_rpm": right_diagnostics.get("target_rpm", 0),
                "current_rpm": right_diagnostics.get("current_rpm", 0),
                "p_term": right_diagnostics.get("p_term", 0),
                "i_term": right_diagnostics.get("i_term", 0),
                "d_term": right_diagnostics.get("d_term", 0),
                "output": right_diagnostics.get("output", 0)
            }
        }
        
        # Send JSON message followed by newline
        try:
            self._uart.write(json.dumps(message).encode() + b'\n')
            self._msg_counter += 1
            self._last_send_time = current_time
        except Exception as e:
            print(f"Failed to send message: {e}")
            
    def receive_command(self):
        """
        Receive and parse command from computer.
        Returns tuple of (command_type, data) or None if no command.
        """
        if self._uart.any():
            try:
                data = self._uart.readline().decode().strip()
                command = json.loads(data)
                return command.get('command'), command.get('data')
            except Exception as e:
                print(f"Failed to parse command: {e}")
        return None