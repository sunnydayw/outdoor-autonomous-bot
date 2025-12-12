from machine import UART, Pin
import time

START1, START2 = 0xAA, 0x55
uart = UART(0, baudrate=115200, tx=Pin(0), rx=Pin(1))
buf = bytearray()

def read_packet():
    global buf
    data = uart.read()
    if data:
        buf.extend(data)

    # Hunt for start bytes without deleting in place (MicroPython bytearray
    # doesn't support slice deletion).
    while len(buf) >= 2 and not (buf[0] == START1 and buf[1] == START2):
        buf = buf[1:]

    if len(buf) < 5:
        return None

    msg_id = buf[2]
    length = (buf[3] << 8) | buf[4]
    total = 2 + 1 + 2 + length + 1
    if len(buf) < total:
        return None

    frame = buf[:total]
    buf = buf[total:]  # drop the consumed bytes by re-slicing

    payload = frame[5:-1]
    chk = frame[-1]
    if chk != (sum(frame[2:-1]) & 0xFF):
        print("checksum mismatch, dropping")
        return None
    return msg_id, payload

print("Waiting for Pi frames...")
while True:
    pkt = read_packet()
    if pkt:
        msg_id, payload = pkt
        try:
            text = payload.decode()
        except Exception:
            text = str(payload)
        print("got packet id", msg_id, "payload:", text)
    time.sleep(0.01)
