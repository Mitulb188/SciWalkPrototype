# TemperatureSensor.py

import board
import digitalio
import adafruit_max31865

# --- Global Sensor setup ---
# This runs once when the module is imported.
spi = board.SPI()
cs = digitalio.DigitalInOut(board.D5)
sensor = adafruit_max31865.MAX31865(spi, cs)

print("MAX31865 (Globe Temperature) sensor initialized.")

def get_globe_temperature():
    """Reads and returns the temperature from the MAX31865 thermocouple."""
    return {
        "globe_temp": sensor.temperature
    }

# This part allows you to run the file directly for testing
if __name__ == "__main__":
    data = get_globe_temperature()
    print("\n--- Globe Temperature Data ---")
    if data:
        print(f"Globe Temperature: {data['globe_temp']:.2f} C")
