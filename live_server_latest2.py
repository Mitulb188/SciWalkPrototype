# live_server.py (New Scheduled Version)

from flask import Flask, jsonify, request
from datetime import datetime
from zoneinfo import ZoneInfo
import math
import threading
from apscheduler.schedulers.background import BackgroundScheduler

# --- Import your sensor and logger modules ---
from windsensor import get_wind_speed_mps
from humidity_temp import get_sensor_data
from TemperatureSensor import get_globe_temperature
from datalogger import setup_workbook, append_data
from pythermalcomfort.models import utci

app = Flask(__name__)

# --- Global Data Store & Threading Lock ---
# This dictionary will hold the most recent data sent from the client app.
# A lock is crucial to prevent two threads (Flask vs. Scheduler) from
# writing/reading at the same time.
client_data_store = {
    "latitude": "N/A",
    "longitude": "N/A",
    "altitude": "N/A",
    "last_update_time": "N/A"
}
client_data_lock = threading.Lock()

# --- Background Scheduler ---
scheduler = BackgroundScheduler(daemon=True, timezone=ZoneInfo("Europe/Berlin"))

walking_speed = 1.2 #in m/s

# --- Helper functions (Unchanged) ---
def calculate_tmrt(Tg, Ta, Va, epsilon=0.95, D=0.1):
    """Calculates the Mean Radiant Temperature (Tmrt) in Celsius."""
    tmrt = (
        (Tg + 273.15)**4 + 
        ( (1.335e8 * (Va**0.71)) / (epsilon * (D**0.4)) ) * (Tg - Ta)
    )**0.25 - 273.15
    return tmrt

def adjust_wind_speed(v_measured, h_measured = 1.55):
    """Adjusts wind speed from a measured height to the standard 10m height. Also assumes that the direction is opposite"""
    if (v_measured < walking_speed) and (h_measured != 10):
        v_10m = (v_measured) * (math.log(10 / 0.01) / (math.log(h_measured / 0.01) if h_measured != 0.01 else 1))
    if (v_measured >= walking_speed) and (h_measured != 10):
        v_10m = (v_measured - walking_speed) * (math.log(10 / 0.01) / (math.log(h_measured / 0.01) if h_measured != 0.01 else 1))
    elif (v_measured >= walking_speed) and h_measured == 10:
        v_10m = v_measured - walking_speed
    else:
        v_10m = (v_measured - walking_speed) * (math.log(10 / 0.01) / (math.log(h_measured / 0.01) if h_measured != 0.01 else 1))
    return v_10m

# --- Scheduled Job ---
def perform_measurement():
    """
    This is the core logging function.
    It runs automatically every 15 seconds on the server.
    """
    global client_data_store, client_data_lock
    
    # 1. Get a thread-safe copy of the last known client data
    with client_data_lock:
        lat = client_data_store["latitude"]
        lon = client_data_store["longitude"]
        alt = client_data_store["altitude"]
        last_client_update = client_data_store["last_update_time"]

    # 2. Get the *server's* current time for the log entry
    now = datetime.now(ZoneInfo("Europe/Berlin"))
    date_str = now.strftime('%Y-%m-%d')
    time_str = now.strftime('%H:%M:%S')

    print(f"--- Logging at {time_str} ---")

    # 3. Read all local Raspberry Pi sensors
    try:
        sensor_data = get_sensor_data()
        globe_data = get_globe_temperature()
        air_speed = get_wind_speed_mps()
        
        humidity = sensor_data.get('humidity', 'N/A') if sensor_data else 'N/A'
        globe_temp = globe_data.get('globe_temp', 'N/A') if globe_data else 'N/A'
        air_temp = sensor_data.get('temperature', 'N/A') if sensor_data else 'N/A'

    except Exception as e:
        print(f"Error reading local sensors: {e}")
        # Log N/A for all sensor data if any sensor fails
        humidity, globe_temp, air_temp, air_speed = "N/A", "N/A", "N/A", "N/A"

    # 4. Format GPS data (from the last known client update)
    gps_coords = f"Lat = {float(lat):.6f}, Long = {float(lon):.6f}" if all(isinstance(i, (int, float)) for i in [lat, lon]) else "N/A"

    # 5. Perform calculations
    tmrt, utci_value = "N/A", "N/A"
    if all(isinstance(i, (int, float)) for i in [globe_temp, air_temp, air_speed, humidity]):
        try:
            adjusted_v_10m = adjust_wind_speed(air_speed)
            if adjusted_v_10m <= float(0.5):
                adjusted_v_10m = 0.5
            tmrt = calculate_tmrt(globe_temp, air_temp, adjusted_v_10m)
            # adjusted_v_10m = adjust_wind_speed(air_speed)
            # if adjusted_v_10m <= float(0.5):
            #     adjusted_v_10m = 0.5
            utci_result = utci(tdb=air_temp, tr=tmrt, v=adjusted_v_10m, rh=humidity)
            utci_value = utci_result["utci"]
        except Exception as e:
            print(f"Error during comfort calculation: {e}")
            tmrt, utci_value = "Error", "Error"

    # 6. Assemble the final data row and log it
    full_data_to_log = [
        date_str, time_str, gps_coords, alt, 
        f"{humidity:.2f}" if isinstance(humidity, (int, float)) else "N/A",
        f"{globe_temp:.2f}" if isinstance(globe_temp, (int, float)) else "N/A",
        f"{air_temp:.2f}" if isinstance(air_temp, (int, float)) else "N/A",
        f"{adjusted_v_10m:.2f}" if isinstance(adjusted_v_10m, (int, float)) else "N/A", # Adjusted air_speed
        f"{air_speed:.2f}" if isinstance(air_speed, (int, float)) else "N/A", # Original air_speed
        f"{tmrt:.2f}" if isinstance(tmrt, (int, float)) else "N/A",
        f"{utci_value:.2f}" if isinstance(utci_value, (int, float)) else "N/A" # Formatted UTCI
    ]
    append_data(full_data_to_log)
    print(f"Logged: {full_data_to_log}")
    print(f"(Client data was last updated at: {last_client_update})")


# --- Endpoint for Session Setup ---
@app.route('/setup', methods=['POST'])
def setup_session():
    """
    Receives metadata from the app, sets up the Excel file,
    AND starts the 15-second logging schedule.
    """
    metadata_json = request.get_json()
    
    if not metadata_json:
        return jsonify({"status": "error", "message": "Invalid metadata format"}), 400
    
    # Create metadata (same as before)
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
    
    # --- NEW: Start the scheduler ---
    try:
        if not scheduler.running:
            # Use 'cron' to align to the "real clock"
            # This triggers at 0, 15, 30, and 45 seconds past every minute
            scheduler.add_job(perform_measurement, 'cron', second='0,15,30,45', id='main_logging_job')
            scheduler.start()
            print("Workbook setup complete. Scheduler started. Logging every 15 seconds.")
        else:
            print("Workbook setup. Scheduler was already running.")
            
        return jsonify({"status": "success", "message": "Session setup complete. Server is now logging."})
    
    except Exception as e:
        print(f"Error starting scheduler: {e}")
        return jsonify({"status": "error", "message": f"Workbook setup, but scheduler failed: {e}"}), 500

# --- NEW Endpoint for Client Data ---
# The /log_data endpoint is GONE, replaced by this:
@app.route('/update_client_data', methods=['POST'])
def update_client_data():
    """
    Receives GPS, Altitude, and Timestamp from the client.
    Its ONLY job is to update the global client_data_store.
    """
    global client_data_store, client_data_lock
    
    client_data = request.get_json()
    required_keys = ['latitude', 'longitude', 'timestamp', 'altitude']
    if not client_data or not all(key in client_data for key in required_keys):
        return jsonify({"status": "error", "message": "Invalid data format. Requires latitude, longitude, altitude, and timestamp."}), 400

    # Update the global store in a thread-safe way
    with client_data_lock:
        client_data_store["latitude"] = float(client_data['latitude'])
        client_data_store["longitude"] = float(client_data['longitude'])
        client_data_store["altitude"] = float(client_data['altitude'])
        client_data_store["last_update_time"] = client_data['timestamp']
    
    # print(f"Client data updated: {client_data_store}")
    return jsonify({"status": "success", "message": "Client data received."})


if __name__ == '__main__':
    print("Starting Flask server...")
    print("Waiting for session setup from app via the /setup endpoint.")
    print("Once setup, server will log every 15s (at :00, :15, :30, :45).")
    print("Client app should send data to /update_client_data periodically.")
    
    # IMPORTANT: Set use_reloader=False.
    # If True (default with debug=True), Flask starts two processes,
    # which will run your scheduler TWICE.
    app.run(host='0.0.0.0', port=8081, debug=False, use_reloader=False)