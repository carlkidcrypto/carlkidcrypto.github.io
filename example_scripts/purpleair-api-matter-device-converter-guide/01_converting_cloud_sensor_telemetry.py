#!/usr/bin/env python3
"""Example script for: Working with the Matter Device Converter: Mapping Sensor Data to Matter 1.5.1 Clusters
Source: https://carlkidcrypto.github.io/blog/purpleair-api-matter-device-converter-guide.html
"""

import os
from purpleair_api.PurpleAirReadAPI import PurpleAirReadAPI
from purpleair_api.PurpleAirMatterConverter import PurpleAirMatterConverter

# Initialize read client with your PurpleAir API Read Key
read_key = os.environ["PURPLEAIR_READ_KEY"]
pa_client = PurpleAirReadAPI(api_read_key=read_key)

# Fetch raw station telemetry (e.g., station 282168)
sensor_index = 282168
raw_payload = pa_client.request_sensor_data(sensor_index=sensor_index)

# Convert to Matter 1.5.1 Air Quality Sensor schema
matter_device = PurpleAirMatterConverter.to_air_quality_sensor(raw_payload)

# Inspect the high-level EPA air quality assessment
summary = matter_device["air_quality_summary"]
print(f"Station: {raw_payload['sensor']['name']}")
print(f"EPA AQI: {summary['epa_aqi']}")
print(f"EPA Category: {summary['epa_category']}")
print(f"Matter Rating: {summary['matter_air_quality_rating']}")
