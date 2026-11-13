#!/usr/bin/env python3
"""Example script for: Getting Started with the Python PurpleAir API Wrapper: Sensor Discovery, Keys & Rate Limits
Source: https://carlkidcrypto.github.io/blog/purpleair-api-getting-started-guide.html
"""

import time
from purpleair_api.PurpleAirAPI import PurpleAirAPIError
from requests.exceptions import RequestException

def resilient_sensor_query(client, sensor_index, fields, max_retries=3):
    fields_str = ",".join(fields)
    backoff_seconds = 2.0

    for attempt in range(1, max_retries + 1):
        try:
            return client.request_sensor_data(
                sensor_index=sensor_index,
                fields=fields_str
            )
        except (RequestException, PurpleAirAPIError) as exc:
            msg = str(exc)
            if any(code in msg for code in ("400", "401", "403")):
                raise
            if attempt == max_retries:
                err_msg = (
                    f"Sensor {sensor_index} failed after {attempt} tries"
                )
                raise RuntimeError(err_msg) from exc
            time.sleep(backoff_seconds)
            backoff_seconds *= 2.0
