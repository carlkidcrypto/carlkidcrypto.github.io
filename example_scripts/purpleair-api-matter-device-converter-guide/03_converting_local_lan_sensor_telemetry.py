#!/usr/bin/env python3
"""Example script for: Working with the Matter Device Converter: Mapping Sensor Data to Matter 1.5.1 Clusters
Source: https://carlkidcrypto.github.io/blog/purpleair-api-matter-device-converter-guide.html
"""

import requests
from purpleair_api.PurpleAirMatterConverter import (
    PurpleAirMatterConverter as Conv,
)

# Query local sensor web server directly over LAN
local_sensor_ip = "192.168.1.150"
response = requests.get(f"http://{local_sensor_ip}/json", timeout=5)
response.raise_for_status()
lan_data = response.json()

# Normalise LAN /json keys (convert pressure from hPa/mbar to PSI)
normalized_data = {
    "name": lan_data.get("SensorId", local_sensor_ip),
    "pm2.5": lan_data.get("pm2_5_atm"),
    "pm1.0": lan_data.get("pm1_0_atm"),
    "pm10.0": lan_data.get("pm10_0_atm"),
    "temperature": lan_data.get("current_temp_f"),
    "humidity": lan_data.get("current_humidity"),
    "pressure": (
        lan_data["pressure"] / 68.94757
        if lan_data.get("pressure") is not None
        else None
    ),
}

# Convert directly to Matter Air Quality Sensor representation
local_matter_sensor = Conv.to_air_quality_sensor(normalized_data)

print("Successfully mapped local sensor to Matter endpoint structure:")
print(f"Node Device Type: {local_matter_sensor['device_type']['label']}")
print(f"EPA AQI: {local_matter_sensor['air_quality_summary']['epa_aqi']}")
