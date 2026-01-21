# live_server.py (Final version with client GPS and Timestamp)

from flask import Flask, jsonify, request
from datetime import datetime
from zoneinfo import ZoneInfo
import math

# --- Import your sensor and logger modules ---
from humidity_temp import get_sensor_data
from TemperatureSensor import get_globe_temperature
from datalogger import setup_workbook, append_data
from pythermalcomfort.models import utci

app = Flask(__name__)

# --- Helper functions (from your main.py) ---
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

def calculate_tmrt(Tg, Ta, Va, epsilon=0.95, D=0.1):
    """Calculates the Mean Radiant Temperature (Tmrt) in Celsius."""
    tmrt = (
        (Tg + 273.15)**4 + 
        ( (1.335e8 * (Va**0.71)) / (epsilon * (D**0.4)) ) * (Tg - Ta)
    )**0.25 - 273.15
    return tmrt

def adjust_wind_speed(v_measured, h_measured=10):
  """Adjusts wind speed from a measured height to the standard 10m height."""
  if h_measured == 10:
      return v_measured
  v_10m = v_measured * (math.log(10 / 0.01) / (math.log(h_measured / 0.01) if h_measured != 0.01 else 1))
  return v_10m

# --- New Flask Endpoint for Receiving Data ---
@app.route('/log_data', methods=['POST'])
def log_data():
    """Receives GPS and Timestamp, reads local sensors, logs all data, and returns a response."""
    
    # --- 1. Get data from the client's request ---
    client_data = request.get_json()
    if not client_data or 'latitude' not in client_data or 'longitude' not in client_data or 'timestamp' not in client_data:
        return jsonify({"status": "error", "message": "Invalid data format. Requires latitude, longitude, and timestamp."}), 400

    latitude = client_data['latitude']
    longitude = client_data['longitude']
    timestamp_str = client_data['timestamp'] # e.g., "2025-09-16 01:15:30"
    altitude = client_data['altitude']
    
    # --- Use the timestamp from the app ---
    try:
        # Assuming the timestamp is sent in 'YYYY-MM-DD HH:MM:SS' format
        dt_object = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
        date_str = dt_object.strftime('%Y-%m-%d')
        time_str = dt_object.strftime('%H:%M:%S')
    except ValueError:
        return jsonify({"status": "error", "message": "Invalid timestamp format. Use 'YYYY-MM-DD HH:MM:SS'."}), 400

    # --- 2. Read the Pi's local sensors ---
    sensor_data = get_sensor_data()
    globe_data = get_globe_temperature()
    
    gps_coords = f"Lat = {float(latitude):.6f}, Long = {float(longitude):.6f}"
    altitude = altitude
    humidity = sensor_data.get('humidity', 'N/A') if sensor_data else 'N/A'
    globe_temp = globe_data.get('globe_temp', 'N/A') if globe_data else 'N/A'
    air_temp = sensor_data.get('temperature', 'N/A') if sensor_data else 'N/A'
    air_speed = 0.6
    
    # --- 3. Perform calculations ---
    tmrt, utci_value = "N/A", "N/A"
    if all(isinstance(i, (int, float)) for i in [globe_temp, air_temp, air_speed, humidity]):
        tmrt = calculate_tmrt(globe_temp, air_temp, air_speed)
        adjusted_v_10m = adjust_wind_speed(air_speed)
        utci_result = utci(tdb=air_temp, tr=tmrt, v=adjusted_v_10m, rh=humidity)
        utci_value = utci_result["utci"]

    # --- 4. Log the combined data to Excel ---
    full_data_to_log = [
        date_str, time_str, gps_coords, altitude, 
        f"{humidity:.2f}" if isinstance(humidity, (int, float)) else "N/A",
        f"{globe_temp:.2f}" if isinstance(globe_temp, (int, float)) else "N/A",
        f"{air_temp:.2f}" if isinstance(air_temp, (int, float)) else "N/A",
        air_speed,
        f"{tmrt:.2f}" if isinstance(tmrt, (int, float)) else "N/A",
        utci_value
    ]
    append_data(full_data_to_log)
    print(f"Logged: {full_data_to_log}")

    # --- 5. Return a confirmation response ---
    response_data = {
        "status": "success",
        "message": "Data logged successfully",
        "logged_timestamp": timestamp_str
    }
    
    return jsonify(response_data)

if __name__ == '__main__':
    session_metadata = get_user_metadata()
    setup_workbook(session_metadata)
    print("Workbook setup complete. Starting Flask server...")
    app.run(host='0.0.0.0', port=8081, debug=True)