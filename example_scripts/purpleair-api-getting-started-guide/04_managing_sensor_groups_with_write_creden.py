#!/usr/bin/env python3
"""Example script for: Getting Started with the Python PurpleAir API Wrapper: Sensor Discovery, Keys & Rate Limits
Source: https://carlkidcrypto.github.io/blog/purpleair-api-getting-started-guide.html
"""

import os
from purpleair_api.PurpleAirWriteAPI import PurpleAirWriteAPI

write_key = os.getenv("PURPLEAIR_WRITE_KEY")
write_client = PurpleAirWriteAPI(api_write_key=write_key)

# Create a new sensor tracking group
new_group = write_client.post_create_group_data(
    name="Municipal Palouse Monitors"
)
group_id = new_group["group_id"]
print(f"Created Group ID: {group_id}")

# Register target sensors into the newly created group
target_sensors = [282168, 175420, 194382]
for sensor_id in target_sensors:
    write_client.post_create_member(
        group_id=group_id,
        sensor_index=sensor_id
    )
    print(f"Enrolled sensor {sensor_id} into group {group_id}")
