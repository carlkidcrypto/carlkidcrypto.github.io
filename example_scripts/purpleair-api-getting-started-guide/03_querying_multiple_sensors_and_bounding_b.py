#!/usr/bin/env python3
"""Example script for: Getting Started with the Python PurpleAir API Wrapper: Sensor Discovery, Keys & Rate Limits
Source: https://carlkidcrypto.github.io/blog/purpleair-api-getting-started-guide.html
"""

import os
from purpleair_api.PurpleAirReadAPI import PurpleAirReadAPI

read_client = PurpleAirReadAPI(os.getenv("PURPLEAIR_READ_KEY"))

# Bounding box coordinates for the Inland Northwest (Palouse region)
nwlng = -117.20
nwlat = 46.80
selng = -116.90
selat = 46.65

# Request specific fields to minimize payload overhead
query_fields = "name,latitude,longitude,pm2.5_atm,temperature"

response = read_client.request_multiple_sensors_data(
    fields=query_fields,
    nwlng=nwlng,
    nwlat=nwlat,
    selng=selng,
    selat=selat,
    location_type=0  # 0 = Outside sensors, 1 = Inside sensors
)

fields_header = response.get("fields", [])
data_rows = response.get("data", [])
print(f"Discovered {len(data_rows)} sensors in bounding box.")

# Map fields to values for easy dictionary access
for row in data_rows[:5]:
    row_dict = dict(zip(fields_header, row))
    print(
        f"Sensor {row_dict.get('name')}: "
        f"PM2.5 = {row_dict.get('pm2.5_atm')} ug/m3"
    )
