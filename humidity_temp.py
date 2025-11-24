# humidity_temp.py

import board
import adafruit_sht31d

# --- Global Sensor setup ---
i2c = board.I2C()  # uses board.SCL and board.SDA
sensor = adafruit_sht31d.SHT31D(i2c)

print("SHT31 sensor initialized.")

def get_sensor_data():
    """Reads and returns the temperature and humidity."""
    return {
        "temperature": sensor.temperature,
        "humidity": sensor.relative_humidity,
    }

# This part allows you to run the file directly for testing
if __name__ == "__main__":
    for i in range(0,100):
        data = get_sensor_data()
        print("\n--- Sensor Data ---")
        if data:
            print(f"Temperature: {data['temperature']:.2f} C")
            print(f"Humidity: {data['humidity']:.2f} %")
    
