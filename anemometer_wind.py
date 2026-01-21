import time

import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn

# --- Sensor parameters ---
V_OFFSET = 0.4     # sensor zero-wind voltage
V_DEADBAND = 0.02  # tolerance (noise margin)
V_MAX = 2.0        # max sensor voltage
WIND_MAX = 32.4    # m/s

def voltage_to_wind_ms(v):
    # Treat sensor as "off / not moving"
    if v <= V_OFFSET + V_DEADBAND:
        return 0.0, 0.0  # voltage, wind

    # Clamp
    if v >= V_MAX:
        v = V_MAX

    # Remove offset
    v_eff = v - V_OFFSET
    wind = v_eff * WIND_MAX / (V_MAX - V_OFFSET)

    return v_eff, wind

# --- ADS1115 setup ---
i2c = busio.I2C(board.SCL, board.SDA)
ads = ADS.ADS1115(i2c)
ads.gain = 1
chan = AnalogIn(ads, 2)

print("Instantaneous wind speed (zeroed at rest)")
while True:
    raw_v = chan.voltage
    eff_v, wind_ms = voltage_to_wind_ms(raw_v)
    wind_kmh = wind_ms * 3.6

    print(
        f"Voltage V: {eff_v:.3f} V | "
        f"Wind: {wind_ms:.2f} m/s ({wind_kmh:.1f} km/h)"
    )

    time.sleep(0.2)
