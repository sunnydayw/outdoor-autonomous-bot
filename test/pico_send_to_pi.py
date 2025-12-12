from machine import UART, Pin
import time

START1, START2 = 0xAA, 0x55
MSG_ID = 0x43  # test id for Pico->Pi
uart = UART(0, baudrate=115200, tx=Pin(0), rx=Pin(1))

def build_packet(msg_id, payload: bytes) -> bytes:
    length = len(payload)
    header = bytes([START1, START2, msg_id, (length >> 8) & 0xFF, length & 0xFF])
    chk = sum(header[2:] + payload) & 0xFF
    return header + payload + bytes([chk])

i = 0
print("Sending to Pi...")
while True:
    payload = ("HELLO_FROM_PICO #%d" % i).encode()
    frame = build_packet(MSG_ID, payload)
    uart.write(frame)
    i += 1
    time.sleep(1)
