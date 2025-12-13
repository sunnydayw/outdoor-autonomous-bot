#!/usr/bin/env python3
import serial, time

PORT = "/dev/ttyAMA10"  # adjust to your Pi debug UART path
BAUD = 115200
START1, START2 = 0xAA, 0x55
MSG_ID = 0x42  # test message id

def build_packet(msg_id: int, payload: bytes) -> bytes:
    length = len(payload)
    header = bytes([START1, START2, msg_id, (length >> 8) & 0xFF, length & 0xFF])
    chk = sum(header[2:] + payload) & 0xFF
    return header + payload + bytes([chk])

def main():
    ser = serial.Serial(PORT, BAUD, timeout=1)
    for i in range(5):
        payload = f"HELLO_FROM_PI #{i}".encode()
        frame = build_packet(MSG_ID, payload)
        ser.write(frame)
        print(f"sent: {payload!r}")
        time.sleep(1)
    ser.close()

if __name__ == "__main__":
    main()
