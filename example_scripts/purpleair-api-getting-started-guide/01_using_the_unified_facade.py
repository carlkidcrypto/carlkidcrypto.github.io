#!/usr/bin/env python3
"""Example script for: Getting Started with the Python PurpleAir API Wrapper: Sensor Discovery, Keys & Rate Limits
Source: https://carlkidcrypto.github.io/blog/purpleair-api-getting-started-guide.html
"""

import os
from purpleair_api.PurpleAirAPI import PurpleAirAPI

# Retrieve credentials from environment variables
read_key = os.getenv("PURPLEAIR_READ_KEY")
write_key = os.getenv("PURPLEAIR_WRITE_KEY")

# Initialize the unified wrapper
paa = PurpleAirAPI(
    your_api_read_key=read_key,
    your_api_write_key=write_key
)

# Query sensor data directly through the facade
sensor_id = 282168
sensor_data = paa.request_sensor_data(sensor_index=sensor_id)
print(f"Sensor Name: {sensor_data['sensor']['name']}")
