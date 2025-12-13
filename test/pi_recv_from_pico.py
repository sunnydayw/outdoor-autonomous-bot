#!/usr/bin/env python3
import serial, time

PORT = "/dev/ttyAMA10"  # adjust to your Pi debug UART path
BAUD = 115200
START1, START2 = 0xAA, 0x55

def read_packet(ser):
    while True:
        b = ser.read(1)
        if not b:
            return None
        if b[0] == START1:
            b2 = ser.read(1)
            if b2 and b2[0] == START2:
                rest = ser.read(3)
                if len(rest) < 3:
                    return None
                msg_id = rest[0]
                length = (rest[1] << 8) | rest[2]
                payload = ser.read(length)
                chk = ser.read(1)
                if len(payload) < length or len(chk) < 1:
                    return None
                if (sum(bytes([msg_id, rest[1], rest[2]]) + payload) & 0xFF) != chk[0]:
                    print("checksum mismatch, skipping")
                    continue
                return msg_id, payload

def main():
    ser = serial.Serial(PORT, BAUD, timeout=1)
    print("Waiting for Pico frames...")
    try:
        while True:
            pkt = read_packet(ser)
            if pkt:
                msg_id, payload = pkt
                print(f"got packet id {msg_id} payload: {payload!r}")
            time.sleep(0.01)
    finally:
        ser.close()

if __name__ == "__main__":
    main()
