# wind_sensor.py
#
# Python script to read a Modern Device Rev C Wind Sensor
# using a Raspberry Pi and an ADS1115 ADC.
#
# This script ports the logic from the official Arduino sketch,
# which is calibrated for a 5V sensor supply.
#
# Refactored to be importable by other scripts.
import time
import board
import busio
#from Adafruit_ADS1x15 import ADS1x15
#import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.ads1115 import ADS1115
from adafruit_ads1x15.analog_in import AnalogIn
import math

# --- User Configuration ---
# To calibrate your sensor, put a glass over it to create a no-wind environment.
# Adjust 'zero_wind_adjustment' until the sensor reads about 0.0 MPH.
# Negative numbers yield smaller wind speeds and vice versa.
ZERO_WIND_ADJUSTMENT = 0.2

# --- Setup (runs once on import) ---
try:
    # Create the I2C bus
    i2c = busio.I2C(board.SCL, board.SDA)

    # Create the ADC object using the I2C bus
    ads = ADS1115(i2c)

    # This gain setting is crucial. The sensor outputs up to 5V.
    # A gain of 2/3 allows the ADS1115 to measure up to 6.144V.
    ads.gain = 2/3

    # Define the analog input channels
    # TMP is connected to A0, RV is connected to A1
    tmp_channel = AnalogIn(ads, 0)
    rv_channel = AnalogIn(ads, 1)
except ValueError:
    print("Error: Could not initialize I2C or ADS1115.")
    print("Please check your wiring and I2C configuration.")
    # We can still define the functions, but they will fail if called
    # without the hardware present.
    tmp_channel = None
    rv_channel = None


def get_wind_data():
    """
    Reads the sensor and performs all calculations for temperature and wind speed.
    
    Returns:
        tuple: (temperature_c, rv_volts, zero_wind_volts, wind_speed_mps)
        Returns (None, None, None, None) if hardware was not initialized.
    """
    if tmp_channel is None or rv_channel is None:
        print("Hardware not initialized. Cannot get data.")
        return None, None, None, None

    # Read the voltage from the sensor pins
    tmp_volts = tmp_channel.voltage
    rv_wind_volts = rv_channel.voltage

    # --- Core Calculation Logic (Ported from Arduino) ---
    # The original formulas rely on a 10-bit ADC reading (0-1023) from a 5V source.
    # We must simulate this by converting our measured voltage into an
    # equivalent 10-bit ADC value.
    # Arduino ADC Value = Voltage * (1023 / 5.0)
    
    # Prevent division by zero or negative log errors if voltage is zero.
    if tmp_volts <= 0:
        tmp_volts = 0.001

    equiv_tmp_adunits = tmp_volts * (1023.0 / 5.0)

    # 1. Calculate temperature in C*100 based on the thermistor reading
    # This is a quadratic regression from the original sketch
    temp_c_times_100 = (0.005 * (equiv_tmp_adunits**2)) - \
                       (16.862 * equiv_tmp_adunits) + 9075.4

    # 2. Calculate the theoretical zero-wind ADC value for the current temperature
    # This is the core of the temperature compensation
    zero_wind_adunits = (-0.0006 * (equiv_tmp_adunits**2)) + \
                        (1.0727 * equiv_tmp_adunits) + 47.172

    # 3. Convert the theoretical zero-wind ADC value to volts and apply manual calibration
    zero_wind_volts = (zero_wind_adunits * (5.0 / 1023.0)) - ZERO_WIND_ADJUSTMENT

    # 4. Calculate the wind speed using the power regression formula
    # V_raw = V_zero + b * WindSpeed^c
    # We solve for WindSpeed: WindSpeed = ((V_raw - V_zero) / b)^(1/c)
    wind_speed_mph = 0.0
    # Ensure the measured voltage is greater than the zero-wind voltage
    if rv_wind_volts > zero_wind_volts:
        wind_speed_mph = math.pow(((rv_wind_volts - zero_wind_volts) / 0.2300), 2.7265)

    # --- Final values ---
    temperature_c = temp_c_times_100 / 100.0
    wind_speed_mps = wind_speed_mph / 2.237

    return temperature_c, rv_wind_volts, zero_wind_volts, wind_speed_mps


def get_wind_speed_mps():
    """
    A simple wrapper function that returns only the wind speed in MPS.

    Returns:
        float: Wind speed in meters per second (MPS).
               Returns None if hardware fails.
    """
    _temp, _rv, _zero, wind_mps = get_wind_data()
    return wind_mps


# --- Main Loop ---
# This block only runs if the script is executed directly (e.g., "python wind_sensor.py")
# It will NOT run when the script is imported by another file.
if __name__ == "__main__":
    print("Starting wind sensor readings...")
    print("Press Ctrl+C to exit.")
    
    if tmp_channel is None or rv_channel is None:
        print("Exiting due to hardware initialization error.")
    else:
        try:
            while True:
                # Get all data from the sensor
                temp_c, rv_volts, zero_volts, wind_mps = get_wind_data()
                
                # --- Print Results ---
                print(f"Temp: {temp_c:.2f}°C | "
                      f"RV Volts: {rv_volts:.3f}V | "
                      f"Zero Wind Volts: {zero_volts:.3f}V | "
                      f"Wind Speed: {wind_mps:.2f} MPS")

                # Wait for 1 second before the next reading
                time.sleep(1)

        except KeyboardInterrupt:
            print("\nStopping script.")
