import sys
import json
from time import sleep
from sps30 import SPS30

if __name__ == "__main__":
    # 1. Connect to SPS30 on I2C Bus 1
    # (The library requires the bus number '1')
    pm_sensor = SPS30(1)

    print("Starting measurement...")
    pm_sensor.start_measurement()

    # 2. CRITICAL: Wait for fan to spin up and airflow to stabilize
    # Without this, the first few readings might be 0 or inaccurate.
    sleep(3)

    print("Reading data (Press Ctrl+C to stop)...")

    while True:
        try:
            # 3. Get the full measurement dictionary
            data = pm_sensor.get_measurement()

            # 4. Print it nicely formatted using JSON
            print(json.dumps(data, indent=2))
            
            sleep(2)

        except KeyboardInterrupt:
            print("\nStopping measurement...")
            pm_sensor.stop_measurement()
            sys.exit()
