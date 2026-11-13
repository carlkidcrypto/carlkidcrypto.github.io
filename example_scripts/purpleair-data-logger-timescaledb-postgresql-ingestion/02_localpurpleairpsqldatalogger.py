#!/usr/bin/env python3
"""Example script for: Automated TimescaleDB & PostgreSQL Ingestion for PurpleAir Sensors
Source: https://carlkidcrypto.github.io/blog/purpleair-data-logger-timescaledb-postgresql-ingestion.html
"""

import json
import os
from pathlib import Path
import pg8000
from purpleair_api.PurpleAirAPI import PurpleAirAPI
from purpleair_data_logger.PurpleAirPSQLDataLogger import (
    PurpleAirPSQLDataLogger,
)

# Ensure configuration file exists
config_file = Path("local_sensor_config.json")
if not config_file.exists():
    config_file.write_text(
        json.dumps({
            "sensor_ip_list": ["192.168.1.100"],
            "poll_interval_seconds": 60
        }, indent=4)
    )

with open(config_file) as f:
    local_config = json.load(f)

conn = pg8000.connect(
    user="ts_user",
    password=os.environ["DB_PASSWORD"],
    host="localhost",
    port=5432,
    database="airquality",
)

class LocalPurpleAirPSQLDataLogger(PurpleAirPSQLDataLogger):
    """Adapter configuring local LAN sensor endpoints on the data logger."""
    def __init__(self, sensor_ip_list, psql_db_conn):
        super().__init__(None, None, psql_db_conn)
        if not isinstance(sensor_ip_list, list):
            sensor_ip_list = [sensor_ip_list]
        self._purpleair_api_obj = [
            PurpleAirAPI(your_ipv4_address=[ip])
            for ip in sensor_ip_list
        ]

# Initialize data logger with LAN sensor addresses
logger = LocalPurpleAirPSQLDataLogger(
    sensor_ip_list=local_config["sensor_ip_list"],
    psql_db_conn=conn,
)

# Ingest directly across local network sockets using local config
logger.validate_parameters_and_run(
    paa_local_sensor_request_json_file=str(config_file)
)
print("Local sensor poll completed successfully.")
