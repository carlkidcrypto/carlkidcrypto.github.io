#!/usr/bin/env python3
"""Example script for: Historical Sensor Data Extraction and Bounding Box Geographic Queries with purpleair_api
Source: https://carlkidcrypto.github.io/blog/purpleair-api-historical-data-bounding-box-queries.html
"""

import os
from purpleair_api.PurpleAirReadAPI import PurpleAirReadAPI

# Initialize read client with your API key
read_key = os.environ["PURPLEAIR_READ_KEY"]
paa = PurpleAirReadAPI(api_read_key=read_key)

# Bounding box for the Palouse region (Moscow, ID & Pullman, WA)
nwlng = -117.25  # West
nwlat = 46.78   # North
selng = -116.92  # East
selat = 46.68   # South

# Request essential fields to minimize point costs
fields_to_request = [
    "name",
    "latitude",
    "longitude",
    "location_type",
    "pm2.5_atm",
    "temperature",
]

response = paa.request_multiple_sensors_data(
    fields=",".join(fields_to_request),
    nwlng=nwlng,
    nwlat=nwlat,
    selng=selng,
    selat=selat,
    location_type=0,  # 0 = Outside only, 1 = Inside only
    max_age=3600      # Exclude sensors offline for > 1 hour
)

fields = response.get("fields", [])
records = response.get("data", [])
print(f"Located {len(records)} active outside sensors in bounding box.")
