.. meta::
   :description: Automate continuous ingestion of PurpleAir sensor telemetry into PostgreSQL with TimescaleDB hypertables, automated compression, and fast SQL analytical queries.
   :keywords: PurpleAir, TimescaleDB, PostgreSQL, Python, IoT, Air Quality, Data Logger, PM2.5, Time Series, DevOps, carlkidcrypto
   :author: Carlos Santos (@carlkidcrypto)
   :property=og:title: Automated TimescaleDB & PostgreSQL Ingestion for PurpleAir Sensors
   :property=og:description: Automate continuous ingestion of PurpleAir sensor telemetry into PostgreSQL with TimescaleDB hypertables, automated compression, and fast SQL analytical queries.
   :property=og:type: article
   :property=og:url: https://carlkidcrypto.github.io/blog/purpleair-data-logger-timescaledb-postgresql-ingestion.html
   :property=og:image: https://carlkidcrypto.github.io/_static/logo.png
   :name=twitter:card: summary
   :name=twitter:title: Automated TimescaleDB & PostgreSQL Ingestion for PurpleAir Sensors
   :name=twitter:description: Automate continuous ingestion of PurpleAir sensor telemetry into PostgreSQL with TimescaleDB hypertables, automated compression, and fast SQL analytical queries.
   :name=twitter:image: https://carlkidcrypto.github.io/_static/logo.png

==================================================================
Automated TimescaleDB & PostgreSQL Ingestion for PurpleAir Sensors
==================================================================

.. note::

   * **Published:** November 05, 2026
   * **Authors:** Written by Gemini 3.8 Flash, Co-Authored & Reviewed by `Carlos Santos (@carlkidcrypto) <https://github.com/carlkidcrypto>`_
   * **Estimated Reading Time:** 5 minutes
   * **Tags:** `PurpleAir` • `TimescaleDB` • `PostgreSQL` • `Python` • `IoT` • `Air-Quality` • `Data-Logger`

Hyper-local air quality sensors produce high-velocity telemetry streams. While
the official `purpleair_api <https://github.com/carlkidcrypto/purpleair_api>`_
wrapper simplifies retrieving instantaneous readings, storing months or years
of particulate data (PM1.0, PM2.5, PM10), temperature, humidity, and atmospheric
pressure requires a dedicated time-series storage architecture.

Ad-hoc CSV exports or naive relational tables quickly suffer performance
degradation when queries scan millions of timestamped rows. To solve this,
`purpleair_data_logger
<https://github.com/carlkidcrypto/purpleair_data_logger>`_ (available on PyPI
as `purpleair-data-logger
<https://pypi.org/project/purpleair-data-logger/>`_) automates continuous
data logging from both cloud-connected and local LAN sensors directly into
PostgreSQL enhanced with the `TimescaleDB <https://www.timescale.com/>`_
extension.

In this tutorial, we will configure automated ingestion pipelines using
``purpleair_data_logger``, explore hypertable schema design, configure automated
chunk partitioning, and run analytical time-bucket queries.

Why TimescaleDB for Sensor Telemetry?
=====================================

Standard PostgreSQL handles structured relational models with enterprise
robustness, but high-frequency IoT logging exposes classic write and read
bottlenecks:

- **B-tree Index Bloat**: As table sizes exceed available RAM, indexing random
  inserts degrades write throughput.
- **Expensive Time Scans**: Aggregating raw sensor records across arbitrary time
  windows (e.g. 15-minute moving averages over 90 days) forces sequential table
  scans across large disk extents.
- **Data Lifecycle Overhead**: Deleting aged telemetry requires costly
  ``DELETE`` operations that trigger table bloat and vacuuming overhead.

TimescaleDB transforms standard PostgreSQL tables into **hypertables**.
Hypertables automatically partition incoming records into temporal chunks
(e.g., 7-day intervals). Writes are always directed to the active, memory-cached
chunk, while analytical queries prune unneeded chunks at the query
planner level. Furthermore, TimescaleDB introduces native columnar
compression (saving up to 90% disk space) and continuous materialization
engines.

Installation & Prerequisites
============================

Ensure you have Python 3.10+ installed alongside a running PostgreSQL instance
with the TimescaleDB extension enabled.

Install the package via pip:

.. code-block:: bash

    pip install purpleair-data-logger

You can also install the package alongside database drivers:

.. code-block:: bash

    pip install psycopg2-binary purpleair-api

Database Schema and Hypertable Definition
=========================================

When initialized, ``PurpleAirPSQLDataLogger`` automatically creates normalized,
domain-separated tables in PostgreSQL and registers each as a TimescaleDB
hypertable partitioned by ``data_time_stamp`` in 7-day chunks:

- ``pm2_5_fields``: Stores particulate matter readings (``pm2_5_atm``,
  ``pm2_5_atm_a``, ``pm2_5_atm_b``, ``pm2_5_cf_1``, ``pm2_5_alt``).
- ``environmental_fields``: Stores meteorological metrics (``temperature``,
  ``humidity``, ``pressure``).
- ``station_information_and_status_fields``: Tracks hardware metadata, device
  names, coordinates, uptime, and firmware versions.
- Additional specialized tables: ``pm1_0_fields``, ``pm10_0_fields``, and
  ``miscellaneous_fields``.

Each table uses a composite primary key of ``(data_time_stamp, sensor_index)``.
If creating or inspecting the underlying schema manually, the core definitions
are:

.. code-block:: sql

    -- Enable TimescaleDB extension
    CREATE EXTENSION IF NOT EXISTS timescaledb;

    -- Create PM2.5 telemetry table
    CREATE TABLE IF NOT EXISTS pm2_5_fields (
        data_time_stamp TIMESTAMPTZ NOT NULL,
        sensor_index INT NOT NULL,
        pm2_5_atm FLOAT NULL,
        pm2_5_atm_a FLOAT NULL,
        pm2_5_atm_b FLOAT NULL,
        pm2_5_cf_1 FLOAT NULL,
        PRIMARY KEY (data_time_stamp, sensor_index)
    );

    -- Create environmental telemetry table
    CREATE TABLE IF NOT EXISTS environmental_fields (
        data_time_stamp TIMESTAMPTZ NOT NULL,
        sensor_index INT NOT NULL,
        humidity INT NULL,
        temperature INT NULL,
        pressure FLOAT NULL,
        PRIMARY KEY (data_time_stamp, sensor_index)
    );

    -- Convert standard tables into TimescaleDB hypertables
    SELECT create_hypertable('pm2_5_fields', 'data_time_stamp',
        chunk_time_interval => INTERVAL '7 days', if_not_exists => TRUE);
    SELECT create_hypertable('environmental_fields', 'data_time_stamp',
        chunk_time_interval => INTERVAL '7 days', if_not_exists => TRUE);

Automating Remote Ingestion via PurpleAirPSQLDataLogger
=======================================================

The ``PurpleAirPSQLDataLogger`` module orchestrates fetching telemetry via
``purpleair_api`` and streaming rows into your PostgreSQL database.

Ingesting from Cloud Sensors
----------------------------

Cloud sensor queries require a JSON configuration file specifying the target
station and polling interval. Create ``single_sensor_config.json`` in your
working directory:

.. code-block:: json

    {
        "poll_interval_seconds": 60,
        "sensor_index": 53,
        "read_key": null,
        "fields": null
    }

Then configure and launch the Python ingestion routine:

.. code-block:: python

    import json
    import os
    from pathlib import Path
    import pg8000
    from purpleair_data_logger.PurpleAirPSQLDataLogger import (
        PurpleAirPSQLDataLogger,
    )

    # Ensure configuration file exists
    config_file = Path("single_sensor_config.json")
    if not config_file.exists():
        config_file.write_text(
            json.dumps({
                "poll_interval_seconds": 60,
                "sensor_index": 53,
                "read_key": None,
                "fields": None
            }, indent=4)
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
        paa_single_sensor_request_json_file=str(config_file)
    )

📥 `Download this script: 01_ingesting_from_cloud_sensors.py <https://raw.githubusercontent.com/carlkidcrypto/carlkidcrypto.github.io/main/example_scripts/purpleair-data-logger-timescaledb-postgresql-ingestion/01_ingesting_from_cloud_sensors.py>`_

Ingesting from Local LAN Sensors Without API Credits
----------------------------------------------------

When sensors reside on your local network (e.g., in a smart home or lab), you
can poll them directly over HTTP using their LAN IP address. This bypasses the
PurpleAir cloud API entirely, preserving API credits and maintaining data
logging during internet outages.

Create a ``local_sensor_config.json`` file specifying the LAN IP addresses:

.. code-block:: json

    {
        "sensor_ip_list": [
            "192.168.1.100"
        ],
        "poll_interval_seconds": 60
    }

Because the base ``PurpleAirPSQLDataLogger`` constructor forwards API keys
without IP addresses, define a lightweight adapter subclass that initializes
``_purpleair_api_obj`` with the configured IP endpoints:

.. code-block:: python

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

📥 `Download this script: 02_localpurpleairpsqldatalogger.py <https://raw.githubusercontent.com/carlkidcrypto/carlkidcrypto.github.io/main/example_scripts/purpleair-data-logger-timescaledb-postgresql-ingestion/02_localpurpleairpsqldatalogger.py>`_

Continuous Aggregations & Analytical Queries
============================================

With telemetry flowing into TimescaleDB, querying massive datasets is fast and
expressive. TimescaleDB extends SQL with temporal primitives like
``time_bucket()``.

Calculating Hourly Rolling Averages
-----------------------------------

To calculate hourly average PM2.5, temperature, and humidity for Grafana
dashboards or analytical research, query ``pm2_5_fields`` and join
``environmental_fields`` using ``time_bucket()``:

.. code-block:: sql

    SELECT
        time_bucket('1 hour', p.data_time_stamp) AS bucket,
        p.sensor_index,
        ROUND(AVG(p.pm2_5_atm)::numeric, 2) AS avg_pm25,
        ROUND(AVG(e.temperature)::numeric, 1) AS avg_temp,
        ROUND(AVG(e.humidity)::numeric, 1) AS avg_humidity
    FROM pm2_5_fields p
    JOIN environmental_fields e
        ON p.data_time_stamp = e.data_time_stamp
        AND p.sensor_index = e.sensor_index
    WHERE p.data_time_stamp > NOW() - INTERVAL '30 days'
    GROUP BY bucket, p.sensor_index
    ORDER BY bucket DESC;

Creating Continuous Aggregate Materialized Views
------------------------------------------------

Rather than computing heavy rollups on every dashboard refresh, TimescaleDB
supports continuous aggregate views that automatically refresh in the background
as new rows are ingested:

.. code-block:: sql

    CREATE MATERIALIZED VIEW pm2_5_hourly_summary
    WITH (timescaledb.continuous) AS
    SELECT
        time_bucket('1 hour', data_time_stamp) AS bucket,
        sensor_index,
        AVG(pm2_5_atm) AS avg_pm25,
        MAX(pm2_5_atm) AS peak_pm25
    FROM pm2_5_fields
    GROUP BY bucket, sensor_index;

    -- Refresh policy: recompute recent 2 hours automatically every 15 minutes
    SELECT add_continuous_aggregate_policy(
        'pm2_5_hourly_summary',
        start_offset => INTERVAL '2 hours',
        end_offset => INTERVAL '15 minutes',
        schedule_interval => INTERVAL '15 minutes'
    );

Production Best Practices
=========================

When running ``purpleair_data_logger`` in 24/7 production environments:

1. **Enable Native Compression**: IoT data compresses exceptionally well.
   Configure TimescaleDB chunk compression after chunks age past 14 days:

   .. code-block:: sql

       ALTER TABLE purpleair_sensor_data SET (
           timescaledb.compress,
           timescaledb.compress_segmentby = 'sensor_index',
           timescaledb.compress_orderby = 'time DESC'
       );

       SELECT add_compression_policy('purpleair_sensor_data', INTERVAL '14d');

2. **Define Data Retention Policies**: For high-frequency collection, drop raw
   hypertable chunks older than 1 year while retaining continuous aggregate
   rollups indefinitely:

   .. code-block:: sql

       SELECT add_retention_policy('purpleair_sensor_data', INTERVAL '365d');

3. **Deploy as a Systemd Service or Docker Container**: Encapsulate your polling
   script within a systemd unit or container with restart policies to ensure
   resilience against network interruptions or database restarts.

Summary & What's Next
=====================

By combining `purpleair_data_logger
<https://github.com/carlkidcrypto/purpleair_data_logger>`_ with TimescaleDB,
developers can construct enterprise-grade, high-throughput environmental
telemetry archives. You gain partition automation, native columnar compression,
and blazing-fast SQL rollups without writing brittle custom ingestion code.

In our next blog post, we will rotate to `purpleair-matterbridge
<https://github.com/carlkidcrypto/purpleair-matterbridge>`_, examining how to
bridge PurpleAir sensor data directly into modern smart home platforms using the
CSA Matter 1.5 standard.

----

.. warning::

   AI-generated content may contain misinformation or mistakes. A human does review this, but we are only human.

