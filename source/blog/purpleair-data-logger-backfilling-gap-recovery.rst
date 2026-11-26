.. meta::
   :description: Continuous air quality monitoring pipelines inevitably encounter data gaps. Home routers reboot, ISP links drop during winter storms, and edge gateways...
   :keywords: Purpleair, Python, Timescaledb, Sqlite, Data-Logger, Recovery, Python, ezsnmp, Networking, DevOps
   :author: Carlos Santos (@carlkidcrypto)
   :property=og:title: Automated Data Backfilling & Gap Recovery with purpleair_data_logger
   :property=og:description: Continuous air quality monitoring pipelines inevitably encounter data gaps. Home routers reboot, ISP links drop during winter storms, and edge gateways...
   :property=og:type: article
   :property=og:url: https://carlkidcrypto.github.io/blog/purpleair-data-logger-backfilling-gap-recovery.html
   :property=og:image: https://carlkidcrypto.github.io/_static/logo.png
   :name=twitter:card: summary
   :name=twitter:title: Automated Data Backfilling & Gap Recovery with purpleair_data_logger
   :name=twitter:description: Continuous air quality monitoring pipelines inevitably encounter data gaps. Home routers reboot, ISP links drop during winter storms, and edge gateways...
   :name=twitter:image: https://carlkidcrypto.github.io/_static/logo.png

====================================================================
Automated Data Backfilling & Gap Recovery with purpleair_data_logger
====================================================================

.. note::

   * **Published:** November 23, 2026
   * **Authors:** Written by Gemini 3.8 Flash, Co-Authored & Reviewed by `Carlos Santos (@carlkidcrypto) <https://github.com/carlkidcrypto>`_
   * **Estimated Reading Time:** 7 minutes
   * **Tags:** `Purpleair` • `Python` • `Timescaledb` • `Sqlite` • `Data-Logger` • `Recovery`

Continuous air quality monitoring pipelines inevitably encounter data gaps.
Home routers reboot, ISP links drop during winter storms, and edge gateways
undergo maintenance reboots. Even when `purpleair_data_logger
<https://github.com/carlkidcrypto/purpleair_data_logger>`_ (published on PyPI
as `purpleair-data-logger
<https://pypi.org/project/purpleair-data-logger/>`_) runs reliably inside a
container or systemd service, upstream outages can still leave multi-hour
holes in your PostgreSQL/TimescaleDB or SQLite archives.

Fortunately, PurpleAir sensors buffer measurements locally and upload missed
intervals to PurpleAir's cloud servers once connectivity returns. By combining
SQL gap-detection queries with `purpleair_api
<https://github.com/carlkidcrypto/purpleair_api>`_ historical endpoints and
idempotent ``ON CONFLICT`` upserts, you can automatically detect and heal
missing intervals without introducing duplicate rows.

In this tutorial, we will write TimescaleDB and SQLite gap-detection queries,
fetch historical chunks safely within PurpleAir API limits, and implement an
idempotent backfill worker using ``pg8000`` and ``PurpleAirReadAPI``.

Detecting Missing Intervals in TimescaleDB & SQLite
===================================================

Before fetching historical records from the cloud, query your local database
to pinpoint the exact ``[gap_start, gap_end]`` windows where telemetry stopped
arriving.

Using Window Functions (``LEAD``) in TimescaleDB
------------------------------------------------

In PostgreSQL/TimescaleDB, the SQL ``LEAD()`` window function compares each
row's timestamp against the next consecutive timestamp for the same sensor. Any
difference exceeding your expected polling cadence (for example, 10 minutes)
identifies a gap:

.. code-block:: sql

    WITH ordered_samples AS (
        SELECT
            sensor_index,
            time_stamp AS current_ts,
            LEAD(time_stamp) OVER (
                PARTITION BY sensor_index
                ORDER BY time_stamp
            ) AS next_ts
        FROM purpleair_sensor_data
        WHERE time_stamp >= NOW() - INTERVAL '14 days'
    )
    SELECT
        sensor_index,
        current_ts AS gap_start,
        next_ts AS gap_end,
        EXTRACT(EPOCH FROM (next_ts - current_ts)) AS gap_seconds
    FROM ordered_samples
    WHERE next_ts - current_ts > INTERVAL '10 minutes'
    ORDER BY gap_start DESC;

Detecting Gaps in Local SQLite Archives
---------------------------------------

SQLite 3.25+ also supports ``LEAD()``. If your edge logger stores Unix epoch
integers in ``timestamp``, gap detection reduces to simple subtraction:

.. code-block:: sql

    WITH ordered_samples AS (
        SELECT
            sensor_ip,
            timestamp AS current_ts,
            LEAD(timestamp) OVER (
                PARTITION BY sensor_ip
                ORDER BY timestamp
            ) AS next_ts
        FROM sensor_readings
    )
    SELECT
        sensor_ip,
        current_ts AS gap_start_epoch,
        next_ts AS gap_end_epoch,
        (next_ts - current_ts) AS gap_seconds
    FROM ordered_samples
    WHERE (next_ts - current_ts) > 600
    ORDER BY gap_start_epoch DESC;

Idempotent Historical Backfill with pg8000
==========================================

Once you identify missing intervals, fetch historical 10-minute or 1-hour
averages via ``PurpleAirReadAPI.request_sensor_historic_data()`` and insert them
with ``ON CONFLICT DO NOTHING``. Using idempotent inserts ensures re-running a
backfill job never corrupts primary keys or double-counts samples.

Note that ``purpleair_data_logger`` uses ``pg8000`` as its PostgreSQL driver,
and ``PurpleAirPSQLDataLogger`` automatically provisions hypertables,
compression policies, and continuous aggregates. Here is a standalone backfill
utility matching that same ``pg8000`` stack:

.. code-block:: python

    import os
    import time
    from datetime import datetime, timedelta, timezone
    from typing import List, Tuple

    import pg8000.native
    from purpleair_api.PurpleAirAPIError import PurpleAirAPIError
    from purpleair_api.PurpleAirReadAPI import PurpleAirReadAPI

    HISTORIC_FIELDS = [
        "pm2.5_atm",
        "pm2.5_cf_1",
        "temperature",
        "humidity",
        "pressure",
    ]

    def find_gaps_pg(
        conn: pg8000.native.Connection, lookback_days: int = 7
    ) -> List[Tuple[int, datetime, datetime]]:
        cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)
        sql = '''
            WITH ordered AS (
                SELECT
                    sensor_index,
                    time_stamp,
                    LEAD(time_stamp) OVER (
                        PARTITION BY sensor_index
                        ORDER BY time_stamp
                    ) AS next_ts
                FROM purpleair_sensor_data
                WHERE time_stamp >= :cutoff
            )
            SELECT sensor_index, time_stamp, next_ts
            FROM ordered
            WHERE next_ts - time_stamp > INTERVAL '15 minutes'
            ORDER BY time_stamp ASC
        '''
        rows = conn.run(sql, cutoff=cutoff)
        return [(int(r[0]), r[1], r[2]) for r in rows]

    def backfill_gap(
        conn: pg8000.native.Connection,
        client: PurpleAirReadAPI,
        sensor_index: int,
        gap_start: datetime,
        gap_end: datetime,
    ) -> int:
        start_epoch = int(gap_start.timestamp())
        end_epoch = int(gap_end.timestamp())
        fields_str = ",".join(HISTORIC_FIELDS)

        try:
            payload = client.request_sensor_historic_data(
                sensor_index=sensor_index,
                fields=fields_str,
                start_timestamp=start_epoch,
                end_timestamp=end_epoch,
                average=10,  # 10-minute historical bins
            )
        except PurpleAirAPIError as err:
            print(f"[-] API error backfilling {sensor_index}: {err}")
            return 0

        headers = payload.get("fields", [])
        data_rows = payload.get("data", [])
        inserted = 0

        insert_sql = '''
            INSERT INTO purpleair_sensor_data (
                time_stamp, sensor_index, pm2_5_atm, pm2_5_cf_1,
                temperature, humidity, pressure
            ) VALUES (
                :ts, :sid, :pm25_atm, :pm25_cf1, :temp, :hum, :pres
            )
            ON CONFLICT (time_stamp, sensor_index) DO NOTHING
        '''

        for row in data_rows:
            rec = dict(zip(headers, row))
            ts = datetime.fromtimestamp(rec["time_stamp"], tz=timezone.utc)
            conn.run(
                insert_sql,
                ts=ts,
                sid=sensor_index,
                pm25_atm=rec.get("pm2.5_atm"),
                pm25_cf1=rec.get("pm2.5_cf_1"),
                temp=rec.get("temperature"),
                hum=rec.get("humidity"),
                pres=rec.get("pressure"),
            )
            inserted += 1

        return inserted

    def run_recovery_job() -> None:
        api = PurpleAirReadAPI(api_read_key=os.environ["PURPLEAIR_READ_KEY"])
        conn = pg8000.native.Connection(
            user=os.environ["DB_USER"],
            password=os.environ["DB_PASSWORD"],
            host=os.environ.get("DB_HOST", "localhost"),
            port=int(os.environ.get("DB_PORT", "5432")),
            database=os.environ.get("DB_NAME", "airquality"),
        )

        try:
            gaps = find_gaps_pg(conn, lookback_days=7)
            print(f"[*] Detected {len(gaps)} telemetry gaps to evaluate.")

            for sensor_id, start_dt, end_dt in gaps:
                t0 = time.monotonic()
                count = backfill_gap(conn, api, sensor_id, start_dt, end_dt)
                print(
                    f"[+] Sensor {sensor_id}: backfilled {count} rows "
                    f"({start_dt.isoformat()} -> {end_dt.isoformat()})"
                )
                # Respect PurpleAir historical API cooldown (>= 1.0s)
                elapsed = time.monotonic() - t0
                if elapsed < 1.2:
                    time.sleep(1.2 - elapsed)
        finally:
            conn.close()

    if __name__ == "__main__":
        run_recovery_job()

📥 `Download this script: run_recovery_job.py <https://raw.githubusercontent.com/carlkidcrypto/carlkidcrypto.github.io/main/example_scripts/purpleair-data-logger-backfilling-gap-recovery/run_recovery_job.py>`_

Handling Compressed Chunks & Continuous Aggregates
==================================================

When backfilling older gaps in TimescaleDB, remember two operational rules:

1. **Chunk Compression Policies**:

   - If a gap falls inside a compressed chunk (for example, older than 14
     days), TimescaleDB handles backfilled inserts into compressed chunks
     automatically in modern releases, though batching inserts by chunk
     minimizes recompression overhead.

2. **Refreshing Continuous Aggregates**:

   - Continuous aggregate materialized views only auto-refresh within their
     configured ``start_offset`` window. After backfilling historical data
     older than ``start_offset``, trigger a manual refresh:

   .. code-block:: sql

       CALL refresh_continuous_aggregate(
           'purpleair_hourly_summary',
           '2026-11-01',
           '2026-11-23'
       );

3. **Distinguishing Sensor Power Loss from Network Drops**:

   - If ``request_sensor_historic_data()`` returns zero rows for a gap, the
     PurpleAir unit itself was likely powered off. Log these unrecoverable
     windows in a separate audit table so nightly recovery jobs do not
     re-query them indefinitely.

Summary & What's Next
=====================

Combining SQL ``LEAD()`` gap detection with idempotent ``ON CONFLICT`` upserts
keeps your `purpleair_data_logger
<https://github.com/carlkidcrypto/purpleair_data_logger>`_ archives complete
even after ISP blackouts or gateway maintenance.

In our next blog post, we will rotate to `purpleair-matterbridge
<https://github.com/carlkidcrypto/purpleair-matterbridge>`_, exploring how to
customize Matter bridge device naming, sensor allowlists, and exclusion filters
for multi-sensor households.

----

.. warning::

   AI-generated content may contain misinformation or mistakes. A human does
   review this, but we are only human.
