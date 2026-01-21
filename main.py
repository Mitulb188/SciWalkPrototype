# main.py

import time
from datetime import datetime
from zoneinfo import ZoneInfo
import math
from pythermalcomfort.models import utci
# Import the functions from your sensor and datalogger files
from gps_test import get_gps_data
from humidity_temp import get_sensor_data
from TemperatureSensor import get_globe_temperature
from datalogger import setup_workbook, append_data

def get_user_metadata():
    """Prompts the user to enter metadata for the session."""
    print("\nPlease enter the following information for this measurement session:")
    metadata = {
        "Collection Date": datetime.now(ZoneInfo("Europe/Berlin")).strftime('%Y-%m-%d'),
        "Collector": input("Collector Name: "),
        "Measurement Device": "Raspberry Pi Weather Station", # Or make this an input
        "Measurement Height": input("Measurement Height (e.g., 1.5m): "),
        "Focus": input("Focus of Measurement (e.g., Urban Park): "),
        "Weather Conditions": input("General Weather Conditions (e.g., Sunny, clear sky): "),
        "Comments": input("Comments: ")
    }
    return metadata

def calculate_tmrt(Tg, Ta, Va, epsilon, D):
    """
    Calculates the Mean Radiant Temperature (Tmrt) in Celsius.

    This function implements the formula commonly used with globe thermometers
    to determine Tmrt, accounting for both radiative and convective heat exchange.

    Args:
        Tg (float): Globe temperature in degrees Celsius (°C).
        Ta (float): Air temperature in degrees Celsius (°C).
        Va (float): Air velocity in meters per second (m/s).
        epsilon (float): Emissivity of the globe's surface (dimensionless).
                        A standard black globe has an emissivity of 0.95.
        D (float): Diameter of the globe in meters (m).
                A standard globe is often 0.15 m (150 mm).

    Returns:
        float: The calculated Mean Radiant Temperature in degrees Celsius (°C).
    """
    # The formula can be calculated in a single expression.
    # We use **0.25 to calculate the fourth root.
    # The constant 1.335 * 10^8 can be written as 1.335e8.
    
    tmrt = (
        (Tg + 273.15)**4 + 
        ( (1.335e8 * (Va**0.71)) / (epsilon * (D**0.4)) ) * (Tg - Ta)
    )**0.25 - 273.15
    
    return tmrt


def adjust_wind_speed(v_measured, h_measured):
  """
  Adjusts wind speed from a measured height to the standard 10m height.

  Args:
    v_measured (float): The measured wind speed in m/s.
    h_measured (float): The height of measurement in meters (e.g., 2 for an anemometer on a tripod).

  Returns:
    float: The adjusted wind speed at 10m height.
  """
  if h_measured == 10:
      return v_measured # No adjustment needed if measured at 10m
  
  # This is the formula from your document
  v_10m = v_measured * (math.log(10 / 0.01) / math.log(h_measured / 0.01))
  return v_10m




def main():
    """Main function to fetch, display, and log sensor data."""
    # Get metadata from the user
    session_metadata = get_user_metadata()

    # Create the Excel file and sheets with the collected metadata
    setup_workbook(session_metadata)

    print("\nStarting weather station application...")
    # Get an initial GPS fix.
    gps_data = get_gps_data()
    if gps_data:
        print("Initial GPS fix acquired.")

    # Main loop to continuously get and print data
    while True:
        # Get data from all the modules
        gps_data = get_gps_data()
        sensor_data = get_sensor_data()
        globe_data = get_globe_temperature()

        # --- Process Data for Logging ---
        date_str, time_str = "N/A", "N/A"
        if gps_data and gps_data['timestamp']:
            utc_dt = datetime.strptime(gps_data['timestamp'], '%m/%d/%Y %H:%M:%S')
            utc_dt = utc_dt.replace(tzinfo=ZoneInfo("UTC"))
            german_tz = ZoneInfo("Europe/Berlin")
            local_dt = utc_dt.astimezone(german_tz)
            date_str = local_dt.strftime('%Y-%m-%d')
            time_str = local_dt.strftime('%H:%M:%S')

        gps_coords = "N/A"
        if gps_data and gps_data['latitude'] is not None:
            gps_coords = f"Lat = {gps_data['latitude']:.6f}, Long = {gps_data['longitude']:.6f}"

        altitude = gps_data.get('altitude', 'N/A')
        humidity = sensor_data.get('humidity', 'N/A')
        globe_temp = globe_data.get('globe_temp', 'N/A')
        air_temp = sensor_data.get('temperature', 'N/A')
        air_speed = 0.6
        tmrt = calculate_tmrt(globe_temp, air_temp, air_speed, 0.95, 0.1)
        adjusted_v_10m = adjust_wind_speed(float(air_speed), float(10))
        print(air_temp, adjusted_v_10m, tmrt, humidity)
        utci_result = utci(tdb=int(air_temp), tr=int(tmrt), v=float(adjusted_v_10m), rh=int(humidity))
        utci_value = utci_result["utci"]

        if isinstance(humidity, (int, float)): humidity = f"{humidity:.2f}"
        if isinstance(globe_temp, (int, float)): globe_temp = f"{globe_temp:.2f}"
        if isinstance(air_temp, (int, float)): air_temp = f"{air_temp:.2f}"
	

        # --- Print to Console ---
        print("\n" + "=" * 40)
        print(f"Weather Station Update - {date_str} {time_str}")
        print("-" * 40)
        print(f"GPS:         {gps_coords}")
        print(f"Altitude:    {altitude} meters")
        print(f"Humidity:    {humidity} %")
        print(f"Globe Temp:  {globe_temp} C")
        print(f"Air Temp:    {air_temp} C")
        print("=" * 40)
        print(f"Air Speed: {air_speed} m/s")
        print(f"TMRT: {tmrt} C")
        print(f"UTCI: {utci_value} ")

        # --- Append to Excel ---
        data_to_log = [date_str, time_str, gps_coords, altitude, humidity, globe_temp, air_temp, air_speed, tmrt, utci_value]
        append_data(data_to_log)
        print(f"Data successfully logged to CSV file")

        # Wait for 10 seconds before the next update
        time.sleep(10)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nApplication stopped by user.")
    except Exception as e:
        print(f"\nAn error occurred: {e}")
