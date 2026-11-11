#!/usr/bin/env python3
"""Example script for: Local Sensor Polling & Offline CSV/SQLite Archival with purpleair_data_logger
Source: https://carlkidcrypto.github.io/blog/purpleair-data-logger-local-csv-sqlite-archival.html
"""

import sqlite3
import requests
from datetime import datetime, timezone

DB_FILE = "purpleair_local_telemetry.db"

def initialize_database():
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sensor_readings (
                timestamp INTEGER NOT NULL,
                sensor_ip TEXT NOT NULL,
                mac_address TEXT,
                pm2_5_atm REAL,
                pm2_5_cf_1 REAL,
                pm10_0_atm REAL,
                temperature REAL,
                humidity REAL,
                pressure REAL,
                PRIMARY KEY (timestamp, sensor_ip)
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_sensor_time
            ON sensor_readings (sensor_ip, timestamp DESC)
        """)
        # Enable Write-Ahead Logging (WAL) for concurrent read/write
        conn.execute("PRAGMA journal_mode=WAL;")

def log_local_sensor(sensor_ip: str):
    url = f"http://{sensor_ip}/json"
    response = requests.get(url, timeout=5)
    response.raise_for_status()
    data = response.json()

    epoch = int(datetime.now(timezone.utc).timestamp())
    mac = data.get("SensorId") or data.get("mac")
    pm25 = data.get("pm2_5_atm")
    pm25_cf1 = data.get("pm2_5_cf_1")
    pm10 = data.get("pm10_0_atm")
    temp = data.get("current_temp_f")
    humidity = data.get("current_humidity")
    pressure = data.get("pressure")

    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("""
            INSERT OR IGNORE INTO sensor_readings (
                timestamp, sensor_ip, mac_address, pm2_5_atm,
                pm2_5_cf_1, pm10_0_atm, temperature, humidity, pressure
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            epoch, sensor_ip, mac, pm25, pm25_cf1, pm10,
            temp, humidity, pressure
        ))

if __name__ == "__main__":
    initialize_database()
    # Poll configured local sensors (replace IP with your local sensor's LAN address)
    configured_sensors = ["192.168.1.100"]
    for ip in configured_sensors:
        try:
            log_local_sensor(ip)
            print(f"Successfully recorded telemetry from {ip}")
        except Exception as err:
            print(f"Sensor polling skipped or failed for {ip}: {err}")
