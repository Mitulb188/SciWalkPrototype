# gps_test.py

import time
import board
import busio
import adafruit_gps
import serial
import datetime
# --- Global GPS setup ---
# This setup runs only once when the module is first imported.
uart = serial.Serial("/dev/serial0", baudrate=9600, timeout=10)
gps = adafruit_gps.GPS(uart, debug=False)

# Send configuration commands
gps.send_command(b"PMTK314,0,1,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0")
gps.send_command(b"PMTK220,1000")

print("GPS module initialized.")

def get_gps_data():
    """Waits for a GPS fix and returns the core data."""
    # Keep updating until we have a fix
    while False: #not gps.has_fix:
        gps.update()
        print("Waiting for GPS fix...")
        time.sleep(1)

    # We have a fix, update one more time to get the latest data
    gps.update()

    # Prepare the data to be returned
    timestamp = None
    if gps.timestamp_utc is not None:
        timestamp = "{}/{}/{} {:02}:{:02}:{:02}".format(
            gps.timestamp_utc.tm_mon,
            gps.timestamp_utc.tm_mday,
            gps.timestamp_utc.tm_year,
            gps.timestamp_utc.tm_hour,
            gps.timestamp_utc.tm_min,
            gps.timestamp_utc.tm_sec,
        )

    return {
        "latitude": 1,#gps.latitude ,
        "longitude": 1,#gps.longitude ,
        "altitude": 1,#gps.altitude_m,
        "timestamp": str(datetime.datetime.now().strftime("%m/%d/%Y %H:%M:%S")), #timestamp,
    }

# This part allows you to run the file directly for testing
if __name__ == "__main__":
    data = get_gps_data()
    print("\n--- GPS Data ---")
    if data:
        print(f"Timestamp: {data['timestamp']}")
        print(f"Latitude: {data['latitude']:.6f} degrees")
        print(f"Longitude: {data['longitude']:.6f} degrees")
        print(f"Altitude: {data['altitude']} meters")
