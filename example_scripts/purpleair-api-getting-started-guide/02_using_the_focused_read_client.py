#!/usr/bin/env python3
"""Example script for: Getting Started with the Python PurpleAir API Wrapper: Sensor Discovery, Keys & Rate Limits
Source: https://carlkidcrypto.github.io/blog/purpleair-api-getting-started-guide.html
"""

import os
from purpleair_api.PurpleAirReadAPI import PurpleAirReadAPI

read_key = os.getenv("PURPLEAIR_READ_KEY")
read_client = PurpleAirReadAPI(api_read_key=read_key)

# Request specific environmental telemetry fields
fields = [
    "name",
    "pm2.5_atm",
    "pm2.5_cf_1",
    "temperature",
    "humidity",
    "pressure",
]
telemetry = read_client.request_sensor_data(
    sensor_index=282168,
    fields=",".join(fields)
)

sensor = telemetry["sensor"]
print(f"Station: {sensor.get('name')}")
print(f"PM2.5 (ATM): {sensor.get('pm2.5_atm')} ug/m3")
print(f"Temperature: {sensor.get('temperature')} deg F")
