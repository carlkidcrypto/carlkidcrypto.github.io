#!/usr/bin/env python3
"""Example script for: Local Sensor Polling & Offline CSV/SQLite Archival with purpleair_data_logger
Source: https://carlkidcrypto.github.io/blog/purpleair-data-logger-local-csv-sqlite-archival.html
"""

import os
from purpleair_data_logger.PurpleAirCSVDataLogger import (
    PurpleAirCSVDataLogger,
)

# Output directory for historical CSV archives
csv_output_dir = "./air_quality_csv_records"
os.makedirs(csv_output_dir, exist_ok=True)

# Initialize CSV data logger for local LAN IP addresses
local_sensor_ips = ["192.168.1.150", "192.168.1.151"]

csv_logger = PurpleAirCSVDataLogger(
    save_file_path=csv_output_dir,
    local_sensor_ip_list=local_sensor_ips
)

# Ingest from local sensor endpoints directly to CSV
csv_logger.store_local_sensors_data()
print("Successfully appended local readings to CSV log.")
