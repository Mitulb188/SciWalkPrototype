**SciWalK Weather Station**

A Raspberry Pi-based mobile weather station project designed to log environmental data, calculate thermal comfort indices (UTCI, MRT), and interface with a mobile client application. This system is part of the SciWalK Pilot Phase.

📋 Overview

This project runs a Flask server that integrates multiple environmental sensors to capture real-time weather data. It performs complex calculations for human thermal comfort and logs everything to a structured Excel file.

Key Features

**Multi-Sensor Integration:** Reads Air Temperature, Relative Humidity, Globe Temperature, and Wind Speed.

**Thermal Comfort Calculations:** Automatically calculates Mean Radiant Temperature (MRT) and Universal Thermal Climate Index (UTCI).

**Data Logging:** Generates date-specific Excel (.xlsx) files with formatted metadata and headers.

**REST API:** Provides endpoints for mobile apps to initiate sessions and inject GPS/Altitude data.

**Automated Scheduling: **Logs data automatically every 15 seconds (at :00, :15, :30, :45).

🛠 Hardware Requirements

Raspberry Pi (Any model with GPIO headers and I2C/SPI support)

Sensors:

**Air Temp/Humidity:** Sensirion SHT31-D

**Globe Temperature:** PT100/PT1000 RTD with MAX31865 Amplifier

**Wind Sensor:** Modern Device Wind Sensor Rev. C

**ADC:** ADS1115 (for reading the analog wind sensor)

**Light Sensor:** To be implemented(currently in works)



📦 Installation

Clone the Repository

git clone [https://github.com/yourusername/sciwalk-weather-station.git](https://github.com/yourusername/sciwalk-weather-station.git)
cd sciwalk-weather-station


Install Dependencies
You will need Python 3 installed. Install the required libraries using pip:

pip install flask apscheduler openpyxl pythermalcomfort adafruit-circuitpython-sht31d adafruit-circuitpython-max31865 adafruit-circuitpython-ads1x15


Note: You may also need to enable I2C and SPI interfaces via raspi-config.

🚀 Usage

1. Start the Server

Run the main server script to start the Flask application and initialize sensors.

python live_server_latest2.py


The server runs on port 8081 by default.

2. Client Interaction (API Endpoints)

The server waits for a client (mobile app) to set up a session before logging begins.

POST /setup: Initializes the logging session.

Payload: JSON object containing metadata (Collector, Focus, Weather Conditions, etc.).

Action: Creates the Excel file and starts the 15-second scheduler.

POST /update_client_data: Updates GPS and Altitude.

Payload: {"latitude": float, "longitude": float, "altitude": float, "timestamp": str}

Action: Updates the global state used for the next log entry.

3. Output

Data is saved to a file named weather_data_YYYY-MM-DD.xlsx in the same directory.

📂 Project Structure

live_server_latest2.py: Main Entry Point. Runs the Flask server, handles API requests, and coordinates the 15-second logging schedule.

datalogger.py: Handles Excel file creation, metadata formatting, and appending new data rows.

windsensor.py: Driver for the Modern Device Wind Sensor using ADS1115. Includes logic to convert voltage to wind speed (MPS).

TemperatureSensor.py: Driver for the MAX31865 Globe Temperature sensor.

humidity_temp.py: Driver for the SHT31 Air Temperature & Humidity sensor.

⚙️ Calibration

Wind Sensor:
In windsensor.py, adjust the ZERO_WIND_ADJUSTMENT variable to calibrate the zero-wind voltage baseline.

# windsensor.py
ZERO_WIND_ADJUSTMENT = 0.2  # Adjust this value based on your specific sensor


📄 License

[Insert License Here]
