.. meta::
   :description: Enterprise cloud data warehouses and managed time-series databases like TimescaleDB offer exceptional query performance for central dashboards. However,...
   :keywords: Purpleair, Python, Sqlite, Csv, Edge-Computing, Iot, Air-Quality, Python, ezsnmp, Networking, DevOps
   :author: Carlos Santos (@carlkidcrypto)
   :property=og:title: Local Sensor Polling & Offline CSV/SQLite Archival with purpleair_data_logger
   :property=og:description: Enterprise cloud data warehouses and managed time-series databases like TimescaleDB offer exceptional query performance for central dashboards. However,...
   :property=og:type: article
   :property=og:url: https://carlkidcrypto.github.io/blog/purpleair-data-logger-local-csv-sqlite-archival.html
   :property=og:image: https://carlkidcrypto.github.io/_static/logo.png
   :name=twitter:card: summary
   :name=twitter:title: Local Sensor Polling & Offline CSV/SQLite Archival with purpleair_data_logger
   :name=twitter:description: Enterprise cloud data warehouses and managed time-series databases like TimescaleDB offer exceptional query performance for central dashboards. However,...
   :name=twitter:image: https://carlkidcrypto.github.io/_static/logo.png

=============================================================================
Local Sensor Polling & Offline CSV/SQLite Archival with purpleair_data_logger
=============================================================================

.. note::

   * **Published:** November 9, 2026
   * **Authors:** Written by Gemini 3.8 Flash, Co-Authored & Reviewed by `Carlos Santos (@carlkidcrypto) <https://github.com/carlkidcrypto>`_
   * **Estimated Reading Time:** 5 minutes
   * **Tags:** `Purpleair` • `Python` • `Sqlite` • `Csv` • `Edge-Computing` • `Iot` • `Air-Quality`

Enterprise cloud data warehouses and managed time-series databases like
TimescaleDB offer exceptional query performance for central dashboards.
However, relying exclusively on remote cloud infrastructure introduces severe
vulnerabilities during environmental emergencies.

Wildfire events, severe storms, and rural deployments frequently disrupt WAN
backhauls, cellular modems, or satellite uplinks. If a sensor logger relies
solely on cloud APIs, telemetry generated during network blackouts is lost.
Furthermore, continuous high-frequency cloud API polling can rapidly deplete
API points and incur unnecessary recurring operational expenses.

The `purpleair_data_logger
<https://github.com/carlkidcrypto/purpleair_data_logger>`_ package (published on
PyPI as `purpleair-data-logger
<https://pypi.org/project/purpleair-data-logger/>`_) addresses these edge
resilience requirements by decoupling telemetry ingestion from cloud services.
In addition to its PostgreSQL/TimescaleDB drivers, the package provides native
support for zero-dependency local network polling, direct SQLite relational
storage, and structured CSV flat-file archival.

In this tutorial, we will explore local LAN polling mechanics, configure
offline SQLite and CSV data logging, and implement an automated edge logging
pipeline suitable for low-power gateways like a Raspberry Pi or home server.

Understanding Local Sensor LAN Polling
======================================

PurpleAir hardware devices operating on a local area network (LAN) host an
internal HTTP web server. Every device exposes a real-time JSON endpoint
accessible directly across the local subnet:

.. code-block:: text

    http://<local_sensor_ip>/json

Polling this local endpoint provides critical operational advantages:

- **Zero Cloud API Credit Cost**: Telemetry is retrieved directly across the
  local network interface without debiting PurpleAir developer credits.
- **High-Frequency Real-Time Telemetry**: While cloud APIs enforce rate limits,
  local sensors update particulate readings dynamically every few seconds.
- **Offline Survivability**: Logging persists seamlessly even if the internet
  service provider (ISP) experiences an outage.

The ``purpleair_data_logger`` package queries local IP addresses using
submodules designed to write structured records directly to disk.

Offline Relational Archival with SQLite
=======================================

SQLite is an ideal storage engine for edge computing. It requires zero
background daemon management, operates in a single portable file, and supports
standard SQL queries with indexed lookups.

Configuring SQLite Ingestion
----------------------------

We can establish an indexed SQLite database schema and continuously log local
readings using Python:

.. code-block:: python

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
        mac = data.get("mac")
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

📥 `Download this script: 01_log_local_sensor.py <https://raw.githubusercontent.com/carlkidcrypto/carlkidcrypto.github.io/main/example_scripts/purpleair-data-logger-local-csv-sqlite-archival/01_log_local_sensor.py>`_

Flat CSV Archival with Rolling Partitions
=========================================

For embedded field research units or air quality stations where downstream
tools lack SQL support, flat CSV logging provides human-readable data
portability.

Using ``PurpleAirCSVDataLogger`` from ``purpleair_data_logger``, telemetry
streams can be appended directly to daily or monthly CSV files:

.. code-block:: python

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

📥 `Download this script: 02_flat_csv_archival_with_rolling_partition.py <https://raw.githubusercontent.com/carlkidcrypto/carlkidcrypto.github.io/main/example_scripts/purpleair-data-logger-local-csv-sqlite-archival/02_flat_csv_archival_with_rolling_partition.py>`_

Deploying as a Resilient Systemd Edge Service
=============================================

To run the offline data logger continuously on an edge device (such as an SEL
gateway, Debian appliance, or Raspberry Pi), configure a systemd service unit.

Create ``/etc/systemd/system/purpleair-local-logger.service``:

.. code-block:: ini

    [Unit]
    Description=PurpleAir Local Sensor Logging Service
    After=network.target

    [Service]
    Type=simple
    User=pi
    WorkingDirectory=/home/pi/purpleair-logging
    ExecStart=/home/pi/purpleair-logging/venv/bin/python local_logger.py
    Restart=always
    RestartSec=15

    [Install]
    WantedBy=multi-user.target

Reload and enable the service:

.. code-block:: bash

    sudo systemctl daemon-reload
    sudo systemctl enable --now purpleair-local-logger.service

Production Best Practices for Edge Archival
===========================================

1. **Enable SQLite WAL Mode**: Always execute ``PRAGMA journal_mode=WAL;`` upon
   database initialization. Write-Ahead Logging allows background analytics
   and dashboards to read the database without locking active sensor inserts.
2. **Implement Storage Volume Pruning**: On flash memory devices (such as
   SD cards or eMMC), monitor disk usage to prevent log accumulation from
   exhausting storage. Establish automated cron jobs to compress CSV files
   older than 30 days into gzip archives.
3. **Handle DHCP IP Drift**: Assign static DHCP reservations in your router or
   gateway for each PurpleAir device to ensure LAN IP addresses remain constant
   across reboots.

Summary & What's Next
=====================

By combining direct LAN polling with lightweight CSV and SQLite backends via
`purpleair_data_logger
<https://github.com/carlkidcrypto/purpleair_data_logger>`_, environmental
practitioners achieve air quality monitoring that survives connectivity
blackouts, eliminates cloud API fees, and preserves data fidelity.

In our next blog post, we will rotate to `purpleair-matterbridge
<https://github.com/carlkidcrypto/purpleair-matterbridge>`_, exploring Matter
device clustering, sensor telemetry mapping, and local diagnostic routines for
smart home controllers.

----

.. warning::

   AI-generated content may contain misinformation or mistakes. A human does review this, but we are only human.

