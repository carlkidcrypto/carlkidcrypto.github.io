#!/usr/bin/env python3
"""Example script for: Local Sensor Polling & Offline CSV/SQLite Archival with purpleair_data_logger
Source: https://carlkidcrypto.github.io/blog/purpleair-data-logger-local-csv-sqlite-archival.html
"""

import json
import os
from pathlib import Path
from purpleair_data_logger.PurpleAirCSVDataLogger import (
    PurpleAirCSVDataLogger,
)

# Output directory for historical CSV archives
csv_output_dir = "./air_quality_csv_records"
os.makedirs(csv_output_dir, exist_ok=True)

# Initialize CSV data logger for local LAN IP addresses
local_sensor_ips = ["192.168.1.150", "192.168.1.151"]

# Ensure local configuration file exists
config_file = Path("local_sensor_config.json")
if not config_file.exists():
    config_file.write_text(
        json.dumps(
            {
                "sensor_ip_list": local_sensor_ips,
                "poll_interval_seconds": 60,
            },
            indent=4,
        )
    )

csv_logger = PurpleAirCSVDataLogger(
    PurpleAirApiIpv4Address=local_sensor_ips,
    path_to_save_csv_files_in=csv_output_dir,
)

# Ingest from local sensor endpoints directly to CSV
csv_logger.validate_parameters_and_run(
    paa_local_sensor_request_json_file=str(config_file)
)
print("Successfully appended local readings to CSV log.")
