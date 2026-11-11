#!/usr/bin/env python3
"""Example script for: Automated TimescaleDB & PostgreSQL Ingestion for PurpleAir Sensors
Source: https://carlkidcrypto.github.io/blog/purpleair-data-logger-timescaledb-postgresql-ingestion.html
"""

import os
import pg8000
from purpleair_data_logger.PurpleAirPSQLDataLogger import (
    PurpleAirPSQLDataLogger,
)

conn = pg8000.connect(
    user="ts_user",
    password=os.environ["DB_PASSWORD"],
    host="localhost",
    port=5432,
    database="airquality",
)

# Initialize data logger for local network sensors
logger = PurpleAirPSQLDataLogger(
    PurpleAirAPIReadKey=None,
    PurpleAirAPIWriteKey=None,
    psql_db_conn=conn,
)

# Ingest directly across local network sockets using local config
logger.validate_parameters_and_run(
    paa_local_sensor_request_json_file="local_sensor_config.json"
)
print("Local sensor poll completed successfully.")
