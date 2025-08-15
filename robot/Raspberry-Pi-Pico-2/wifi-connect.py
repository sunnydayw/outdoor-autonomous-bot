import network
import time

def connect_to_wifi(ssid, password):
    # Initialize the WLAN station interface
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)  # Activate Wi-Fi

    # Check if already connected
    if wlan.isconnected():
        print("Already connected to Wi-Fi")
        return wlan

    # Connect to Wi-Fi
    print(f"Connecting to {ssid}...")
    wlan.connect(ssid, password)

    # Wait for connection
    timeout = 10  # seconds
    start_time = time.time()
    while not wlan.isconnected():
        if time.time() - start_time > timeout:
            print("Failed to connect to Wi-Fi within timeout period.")
            return None
        time.sleep(1)

    print("Connected to Wi-Fi")
    print("Network Config:", wlan.ifconfig())
    return wlan


# Replace these with your Wi-Fi credentials
WIFI_SSID = "Sunny Day"
WIFI_PASSWORD = "Qzhang1993$"

wlan = connect_to_wifi(WIFI_SSID, WIFI_PASSWORD)

