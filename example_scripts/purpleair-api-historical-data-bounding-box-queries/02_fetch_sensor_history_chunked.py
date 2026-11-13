#!/usr/bin/env python3
"""Example script for: Historical Sensor Data Extraction and Bounding Box Geographic Queries with purpleair_api
Source: https://carlkidcrypto.github.io/blog/purpleair-api-historical-data-bounding-box-queries.html
"""

import os
import time
from datetime import datetime, timedelta, timezone
from purpleair_api.PurpleAirReadAPI import PurpleAirReadAPI

def fetch_sensor_history_chunked(
    client: PurpleAirReadAPI,
    sensor_index: int,
    start_dt: datetime,
    end_dt: datetime,
    average_minutes: int = 60,
    chunk_days: int = 14
):
    # Extract historical sensor data across compliant time chunks
    fields = ["pm2.5_atm", "pm2.5_cf_1", "temperature", "humidity"]
    fields_str = ",".join(fields)

    all_rows = []
    header = None

    current_start = start_dt
    while current_start < end_dt:
        current_end = min(
            current_start + timedelta(days=chunk_days),
            end_dt
        )

        start_epoch = int(current_start.timestamp())
        end_epoch = int(current_end.timestamp())

        backoff = 2.0
        for attempt in range(1, 4):
            try:
                result = client.request_sensor_historic_data(
                    sensor_index=sensor_index,
                    fields=fields_str,
                    start_timestamp=start_epoch,
                    end_timestamp=end_epoch,
                    average=average_minutes
                )

                if header is None:
                    header = result.get("fields", [])

                chunk_rows = result.get("data", [])
                all_rows.extend(chunk_rows)
                break

            except Exception as err:
                msg = (
                    f"Error querying {sensor_index} [{start_epoch}] "
                    f"attempt {attempt}: {err}"
                )
                print(msg)
                if attempt == 3:
                    raise RuntimeError(
                        f"Failed chunk {start_epoch}-{end_epoch} for "
                        f"sensor {sensor_index}"
                    ) from err
                time.sleep(backoff)
                backoff *= 2.0

        current_start = current_end
        time.sleep(1.2)  # Strict rate limit compliance

    return header, all_rows

if __name__ == "__main__":
    read_key = os.environ["PURPLEAIR_READ_KEY"]
    api = PurpleAirReadAPI(api_read_key=read_key)

    target_sensor = 282168
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=30)

    cols, data = fetch_sensor_history_chunked(
        client=api,
        sensor_index=target_sensor,
        start_dt=start_time,
        end_dt=end_time,
        average_minutes=60
    )

    msg = f"Downloaded {len(data)} hourly records for {target_sensor}"
    print(msg)
