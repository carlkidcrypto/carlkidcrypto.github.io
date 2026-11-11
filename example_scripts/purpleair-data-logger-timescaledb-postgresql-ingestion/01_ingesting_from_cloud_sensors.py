#!/usr/bin/env python3
"""Example script for: Automated TimescaleDB & PostgreSQL Ingestion for PurpleAir Sensors
Source: https://carlkidcrypto.github.io/blog/purpleair-data-logger-timescaledb-postgresql-ingestion.html
"""

import os
import pg8000
from purpleair_data_logger.PurpleAirPSQLDataLogger import (
    PurpleAirPSQLDataLogger,
)

# Establish PG8000 PostgreSQL database connection
conn = pg8000.connect(
    user="ts_user",
    password=os.environ["DB_PASSWORD"],
    host="localhost",
    port=5432,
    database="airquality",
)

# Initialize data logger with API keys and database connection
logger = PurpleAirPSQLDataLogger(
    PurpleAirAPIReadKey=os.environ["PURPLEAIR_READ_KEY"],
    PurpleAirAPIWriteKey=None,
    psql_db_conn=conn,
)

# Execute polling via JSON configuration file
logger.validate_parameters_and_run(
    paa_single_sensor_request_json_file="single_sensor_config.json"
)
