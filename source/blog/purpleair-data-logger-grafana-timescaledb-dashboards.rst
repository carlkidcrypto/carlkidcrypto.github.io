.. meta::
   :description: Connect Grafana to TimescaleDB and PostgreSQL telemetry from purpleair_data_logger with read-only roles, time_bucket panels, heatmaps, and spike alerts.
   :keywords: PurpleAir, Grafana, TimescaleDB, PostgreSQL, Visualization, Air-Quality, IoT, purpleair_data_logger
   :author: Carlos Santos (@carlkidcrypto)
   :property=og:title: Building Automated Grafana Dashboards over TimescaleDB PurpleAir Telemetry
   :property=og:description: Connect Grafana to TimescaleDB and PostgreSQL telemetry from purpleair_data_logger with read-only roles, time_bucket panels, heatmaps, and spike alerts.
   :property=og:type: article
   :property=og:url: https://carlkidcrypto.github.io/blog/purpleair-data-logger-grafana-timescaledb-dashboards.html
   :property=og:image: https://carlkidcrypto.github.io/_static/logo.png
   :name=twitter:card: summary
   :name=twitter:title: Building Automated Grafana Dashboards over TimescaleDB PurpleAir Telemetry
   :name=twitter:description: Connect Grafana to TimescaleDB and PostgreSQL telemetry from purpleair_data_logger with read-only roles, time_bucket panels, heatmaps, and spike alerts.
   :name=twitter:image: https://carlkidcrypto.github.io/_static/logo.png

==========================================================================
Building Automated Grafana Dashboards over TimescaleDB PurpleAir Telemetry
==========================================================================

.. note::

   * **Published:** November 13, 2026
   * **Authors:** Written by Gemini 3.8 Flash, Co-Authored & Reviewed by `Carlos Santos (@carlkidcrypto) <https://github.com/carlkidcrypto>`_
   * **Estimated Reading Time:** 5 minutes
   * **Tags:** `PurpleAir` • `Grafana` • `TimescaleDB` • `PostgreSQL` • `Visualization` • `Air-Quality`

Storing high-frequency environmental telemetry in PostgreSQL and TimescaleDB
solves the ingestion and retention challenges of long-term air quality
monitoring. Once `purpleair_data_logger
<https://github.com/carlkidcrypto/purpleair_data_logger>`_ (published on PyPI
as `purpleair-data-logger
<https://pypi.org/project/purpleair-data-logger/>`_) continuously streams
particulate matter, temperature, and humidity records into TimescaleDB
hypertables, the next step is turning raw rows into real-time operational
visibility.

`Grafana <https://grafana.com/>`_ pairs naturally with TimescaleDB. Because
TimescaleDB is a PostgreSQL extension, Grafana's built-in PostgreSQL data
source connects directly to your hypertables and continuous aggregates without
intermediate translation layers.

In this tutorial, we will configure a least-privilege PostgreSQL data source in
Grafana, construct time-bucketed PM2.5 panels and AQI heatmaps, and define
automated alert rules to flag sudden wildfire smoke spikes.

Configuring a Least-Privilege Data Source
=========================================

Before connecting Grafana to your telemetry database, create a dedicated
read-only PostgreSQL role. This ensures that dashboard panels and ad-hoc
queries can never mutate or drop stored sensor records:

.. code-block:: sql

    -- Create read-only role for Grafana queries
    CREATE ROLE grafana_reader WITH LOGIN PASSWORD 'strong_readonly_password';
    GRANT CONNECT ON DATABASE airquality TO grafana_reader;
    GRANT USAGE ON SCHEMA public TO grafana_reader;
    GRANT SELECT ON ALL TABLES IN SCHEMA public TO grafana_reader;

    -- Ensure future tables or views remain readable
    ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT ON TABLES TO grafana_reader;

In the Grafana UI, navigate to **Connections** -> **Data sources** -> **Add
data source** and select **PostgreSQL**:

1. **Host URL**: Enter ``<db_host>:5432`` and set **Database name** to
   ``airquality``.
2. **Authentication**: Supply ``grafana_reader`` and your read-only password.
3. **TLS/SSL Mode**: Set to ``require`` for remote database instances.
4. **PostgreSQL Options**: Enable the **TimescaleDB** toggle so Grafana
   optimizes ``$__timeGroup`` and ``time_bucket()`` macro expansion.

Click **Save & test** to verify connectivity.

Querying Hypertables with Grafana Macros
========================================

Grafana provides built-in SQL macros that synchronize dashboard time pickers
with TimescaleDB chunk pruning:

- ``$__timeFilter(time)``: Expands into a bounded ``WHERE`` clause matching the
  dashboard's active time range, allowing the TimescaleDB query planner to
  skip irrelevant temporal chunks.
- ``$__interval``: Dynamically scales the bucket granularity based on the
  selected window (e.g., ``1m`` for 6-hour views, ``1h`` for 30-day views).

Joining Normalized Telemetry Tables via a View
----------------------------------------------

In ``purpleair_data_logger``, PostgreSQL and TimescaleDB ingestion normalizes
sensor readings across category tables—including ``pm2_5_fields``,
``environmental_fields``, ``particle_count_fields``, and
``station_information_and_status_fields``—all keyed by
``(data_time_stamp, sensor_index)``. Create a unified compatibility view
``purpleair_sensor_data`` so Grafana panels can query station names alongside
PM2.5, environmental, and particle metrics without repeating joins:

.. code-block:: sql

    CREATE OR REPLACE VIEW purpleair_sensor_data AS
    SELECT
        p.data_time_stamp AS time,
        s.sensor_index,
        s.name,
        p.pm2_5_atm,
        e.temperature,
        e.humidity,
        e.pressure,
        pc.um_count_0_3,
        pc.um_count_2_5,
        pc.um_count_10_0
    FROM pm2_5_fields p
    JOIN station_information_and_status_fields s
        USING (data_time_stamp, sensor_index)
    JOIN environmental_fields e
        USING (data_time_stamp, sensor_index)
    LEFT JOIN particle_count_fields pc
        USING (data_time_stamp, sensor_index);

    GRANT SELECT ON purpleair_sensor_data TO grafana_reader;

Real-Time PM2.5 Time-Series Panel
---------------------------------

To plot multi-sensor PM2.5 trends with smooth downsampling, configure a **Time
series** panel using ``time_bucket()``:

.. code-block:: text

    SELECT
        time_bucket('$__interval', time) AS "time",
        name AS metric,
        ROUND(AVG(pm2_5_atm)::numeric, 2) AS pm25
    FROM purpleair_sensor_data
    WHERE $__timeFilter(time)
    GROUP BY 1, 2
    ORDER BY 1 ASC;

Mapping US EPA AQI Thresholds
-----------------------------

You can apply threshold bands directly inside the Grafana panel editor so lines
and gauge cards reflect standard US EPA air quality colors:

- **0 – 9.0 ug/m3**: Green (Good)
- **9.1 – 35.4 ug/m3**: Yellow (Moderate)
- **35.5 – 55.4 ug/m3**: Orange (Unhealthy for Sensitive Groups)
- **55.5+ ug/m3**: Red (Unhealthy)

Building Diurnal AQI Heatmaps
=============================

Line charts reveal acute spikes, but **Heatmaps** uncover recurring daily
patterns—such as evening woodsmoke accumulation or morning commuter traffic
peaks.

By extracting the hour of day alongside the calendar date, you can build a
multi-week diurnal concentration matrix:

.. code-block:: text

    SELECT
        time_bucket('1 hour', time) AS "time",
        sensor_index::text AS sensor,
        AVG(pm2_5_atm) AS pm25_avg
    FROM purpleair_sensor_data
    WHERE $__timeFilter(time)
    GROUP BY 1, 2
    ORDER BY 1 ASC;

In the Grafana **Heatmap** panel settings, set **Calculate from data** to
enabled, choose a spectral or orange-red color scheme, and set the unit to
``ug/m3``. High-particulate windows immediately stand out across multi-month
views.

Querying Continuous Aggregates for Speed
----------------------------------------

When dashboards span 90 days or a full year across dozens of sensors, querying
raw hypertable rows introduces unnecessary I/O. Point long-horizon panels at
your TimescaleDB continuous aggregate view (e.g., ``purpleair_hourly_summary``)
instead:

.. code-block:: text

    SELECT
        bucket AS "time",
        sensor_index::text AS sensor,
        avg_pm25,
        peak_pm25
    FROM purpleair_hourly_summary
    WHERE $__timeFilter(bucket)
    ORDER BY bucket ASC;

Configuring Automated Spike Alerts
==================================

Passive dashboards require manual inspection; automated alerting notifies you
the moment smoke plumes arrive. Grafana's unified alerting engine evaluates
SQL queries on a fixed schedule and dispatches notifications via Slack, email,
or webhooks.

Create an alert rule query that compares the 15-minute rolling PM2.5 average
against a critical threshold:

.. code-block:: sql

    SELECT
        sensor_index::text AS sensor,
        AVG(pm2_5_atm) AS current_pm25
    FROM purpleair_sensor_data
    WHERE time > NOW() - INTERVAL '15 minutes'
    GROUP BY sensor_index;

Configure the alert condition as follows:

1. **Reduce Expression**: Apply ``Last`` or ``Mean`` on ``current_pm25``.
2. **Threshold Expression**: Trigger when ``current_pm25`` is **IS ABOVE**
   ``35.5`` (US EPA Unhealthy for Sensitive Groups threshold).
3. **Evaluation Behavior**: Evaluate every ``5m`` with a pending period of
   ``10m`` to prevent transient sensor noise from firing false alarms.

Provisioning Dashboards as Code
===============================

For reproducible deployments alongside ``purpleair_data_logger``, export your
finalized dashboard JSON and store it in version control. Grafana supports
automatic file-based provisioning via ``/etc/grafana/provisioning/dashboards``:

.. code-block:: yaml

    apiVersion: 1

    providers:
      - name: "PurpleAir Telemetry"
        orgId: 1
        folder: "Air Quality"
        type: file
        disableDeletion: false
        updateIntervalSeconds: 30
        options:
          path: /var/lib/grafana/dashboards/purpleair

Summary & What's Next
=====================

Pairing `purpleair_data_logger
<https://github.com/carlkidcrypto/purpleair_data_logger>`_ and TimescaleDB with
Grafana delivers fast, least-privilege observability over hyper-local air
quality networks. With time-bucketed queries, continuous aggregates, and
automated spike alerts, you can track environmental shifts in real time.

In our next blog post, we will rotate to `purpleair-matterbridge
<https://github.com/carlkidcrypto/purpleair-matterbridge>`_, exploring
multi-fabric commissioning so you can share your PurpleAir Matterbridge
simultaneously across Apple Home and Google Home controllers.

----

.. warning::

   AI-generated content may contain misinformation or mistakes. A human does review this, but we are only human.

