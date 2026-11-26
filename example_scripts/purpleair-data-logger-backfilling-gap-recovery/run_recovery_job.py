#!/usr/bin/env python3
"""Example script for: Automated Data Backfilling & Gap Recovery with purpleair_data_logger
Source: https://carlkidcrypto.github.io/blog/purpleair-data-logger-backfilling-gap-recovery.html
"""

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
    sql = """
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
    """
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

    insert_sql = """
        INSERT INTO purpleair_sensor_data (
            time_stamp, sensor_index, pm2_5_atm, pm2_5_cf_1,
            temperature, humidity, pressure
        ) VALUES (
            :ts, :sid, :pm25_atm, :pm25_cf1, :temp, :hum, :pres
        )
        ON CONFLICT (time_stamp, sensor_index) DO NOTHING
    """

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
