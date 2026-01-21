# live_server.py (Final Headless Version)

from flask import Flask, jsonify, request
from datetime import datetime
from zoneinfo import ZoneInfo
import math

# --- Import your sensor and logger modules ---
from windsensor import get_wind_speed_mps
from humidity_temp import get_sensor_data
from TemperatureSensor import get_globe_temperature
from datalogger import setup_workbook, append_data
from pythermalcomfort.models import utci

app = Flask(__name__)

# --- Helper functions ---
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

# --- Endpoint for Session Setup ---
@app.route('/setup', methods=['POST'])
def setup_session():
    """Receives detailed metadata from the app and sets up the Excel log file."""
    metadata_json = request.get_json()
    
    if not metadata_json:
        return jsonify({"status": "error", "message": "Invalid metadata format"}), 400
    
    # Create the detailed metadata list for the datalogger
    session_metadata = {
        "Collector": metadata_json.get("Collector"),
        "Measurement Device": "Raspberry Pi Weather Station",
        "Measurement Height": metadata_json.get("Measurement Height"),
        "Focus": metadata_json.get("Focus"),
        "Weather Conditions": metadata_json.get("Weather Conditions"),
        "Comments": metadata_json.get("Comments"),
        "Collection Date": datetime.now(ZoneInfo("Europe/Berlin")).strftime('%Y-%m-%d')
    }
    
    setup_workbook(session_metadata)
    
    print("Workbook setup complete with metadata from app.")
    return jsonify({"status": "success", "message": "Session setup complete. Ready to log data."})

# --- Endpoint for Receiving Data ---
@app.route('/log_data', methods=['POST'])
def log_data():
    """Receives GPS, Altitude, and Timestamp, reads local sensors, logs all data, and returns a response."""
    
    client_data = request.get_json()
    required_keys = ['latitude', 'longitude', 'timestamp', 'altitude']
    if not client_data or not all(key in client_data for key in required_keys):
        return jsonify({"status": "error", "message": "Invalid data format. Requires latitude, longitude, altitude, and timestamp."}), 400

    latitude = client_data['latitude']
    longitude = client_data['longitude']
    timestamp_str = client_data['timestamp']
    altitude = client_data['altitude']
    
    try:
        dt_object = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
        date_str = dt_object.strftime('%Y-%m-%d')
        time_str = dt_object.strftime('%H:%M:%S')
    except ValueError:
        return jsonify({"status": "error", "message": "Invalid timestamp format. Use 'YYYY-MM-DD HH:MM:SS'."}), 400

    sensor_data = get_sensor_data()
    globe_data = get_globe_temperature()
    
    gps_coords = f"Lat = {float(latitude):.6f}, Long = {float(longitude):.6f}"
    humidity = sensor_data.get('humidity', 'N/A') if sensor_data else 'N/A'
    globe_temp = globe_data.get('globe_temp', 'N/A') if globe_data else 'N/A'
    air_temp = sensor_data.get('temperature', 'N/A') if sensor_data else 'N/A'
    air_speed = get_wind_speed_mps()
    
    tmrt, utci_value = "N/A", "N/A"
    if all(isinstance(i, (int, float)) for i in [globe_temp, air_temp, air_speed, humidity]):
        tmrt = calculate_tmrt(globe_temp, air_temp, air_speed)
        adjusted_v_10m = adjust_wind_speed(air_speed)
        if adjusted_v_10m <= float(0.5):
            adjusted_v_10m = 0.5
        utci_result = utci(tdb=air_temp, tr=tmrt, v=adjusted_v_10m, rh=humidity)
        utci_value = utci_result["utci"]

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
    
    response_data = {
        "status": "success",
        "message": "Data logged successfully",
        "logged_timestamp": timestamp_str
    }
    return jsonify(response_data)


if __name__ == '__main__':
    print("Starting Flask server... Waiting for session setup from app via the /setup endpoint.")
    app.run(host='0.0.0.0', port=8081, debug=True)