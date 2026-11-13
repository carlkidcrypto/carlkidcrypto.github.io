.. meta::
   :description: :Author: Written by Gemini :Co-Author: Carlos Santos :Date: November 8, 2026 :Category: Environmental Data Science :Tags: purpleair, python, api,...
   :keywords: Purpleair, Python, Api, Open-Source, Gis, Environmental-Data, Air-Quality, Python, ezsnmp, Networking, DevOps
   :author: Carlos Santos (@carlkidcrypto)
   :property=og:title: Historical Sensor Data Extraction and Bounding Box Geographic Queries with purpleair_api
   :property=og:description: :Author: Written by Gemini :Co-Author: Carlos Santos :Date: November 8, 2026 :Category: Environmental Data Science :Tags: purpleair, python, api,...
   :property=og:type: article
   :property=og:url: https://carlkidcrypto.github.io/blog/purpleair-api-historical-data-bounding-box-queries.html
   :property=og:image: https://carlkidcrypto.github.io/_static/logo.png
   :name=twitter:card: summary
   :name=twitter:title: Historical Sensor Data Extraction and Bounding Box Geographic Queries with purpleair_api
   :name=twitter:description: :Author: Written by Gemini :Co-Author: Carlos Santos :Date: November 8, 2026 :Category: Environmental Data Science :Tags: purpleair, python, api,...
   :name=twitter:image: https://carlkidcrypto.github.io/_static/logo.png

========================================================================================
Historical Sensor Data Extraction and Bounding Box Geographic Queries with purpleair_api
========================================================================================

.. note::

   * **Published:** November 8, 2026
   * **Authors:** Written by Gemini 3.8 Flash, Co-Authored & Reviewed by `Carlos Santos (@carlkidcrypto) <https://github.com/carlkidcrypto>`_
   * **Estimated Reading Time:** 5 minutes
   * **Tags:** `Purpleair` • `Python` • `Api` • `Open-Source` • `Gis` • `Environmental-Data` • `Air-Quality`

purpleair_api
================================================================================

:Author: Written by Gemini
:Co-Author: Carlos Santos
:Date: November 8, 2026
:Category: Environmental Data Science
:Tags: purpleair, python, api, open-source, gis, environmental-data, air-quality
:Estimated Reading Time: 5 minutes

Environmental researchers, municipal air districts, and data scientists
frequently require localized, historical air quality datasets to study wildfire
smoke dispersion, assess public exposure patterns, or validate atmospheric
models. While instantaneous telemetry reflects current conditions, historical
analysis requires pulling dense sensor records across precise geographic regions
and multi-week time horizons.

The official Python wrapper, `purpleair_api
<https://github.com/carlkidcrypto/purpleair_api>`_ (available on PyPI as
`purpleair-api <https://pypi.org/project/purpleair-api/>`_), provides high-level
abstractions for two critical analytical workflows:

1. **Bounding Box Spatial Queries**: Discovering and extracting all active
   outdoor and indoor sensors within arbitrary geographic coordinates.
2. **Historical Time-Series Retrieval**: Fetching historical sensor averages
   (10-minute, 30-minute, 1-hour, or 1-day bins) across custom date ranges.

In this tutorial, we will explore the geometric structure of PurpleAir bounding
box queries, examine historical API constraints, and build a reusable data
pipeline that chunks historical requests and parses results into analytical
structures.

Spatial Filtering via Bounding Boxes
====================================

The PurpleAir API allows callers to define rectangular bounding boxes in decimal
degrees to filter sensors across cities, watersheds, or geopolitical boundaries.

Bounding boxes are parameterized by four geospatial coordinates:

- ``nwlng``: Northwest Longitude (Western boundary)
- ``nwlat``: Northwest Latitude (Northern boundary)
- ``selng``: Southeast Longitude (Eastern boundary)
- ``selat``: Southeast Latitude (Southern boundary)

Using ``PurpleAirReadAPI.request_multiple_sensors_data()``, developers can
combine coordinate constraints with metadata filtering to reduce network payload
size and preserve API credit points:

.. code-block:: python

    import os
    from purpleair_api.PurpleAirReadAPI import PurpleAirReadAPI

    # Initialize read client with your API key
    read_key = os.environ["PURPLEAIR_READ_KEY"]
    paa = PurpleAirReadAPI(api_read_key=read_key)

    # Bounding box for the Palouse region (Moscow, ID & Pullman, WA)
    nwlng = -117.25  # West
    nwlat = 46.78   # North
    selng = -116.92  # East
    selat = 46.68   # South

    # Request essential fields to minimize point costs
    fields_to_request = [
        "name",
        "latitude",
        "longitude",
        "location_type",
        "pm2.5_atm",
        "temperature",
    ]

    response = paa.request_multiple_sensors_data(
        fields=",".join(fields_to_request),
        nwlng=nwlng,
        nwlat=nwlat,
        selng=selng,
        selat=selat,
        location_type=0,  # 0 = Outside only, 1 = Inside only
        max_age=3600      # Exclude sensors offline for > 1 hour
    )

    fields = response.get("fields", [])
    records = response.get("data", [])
    print(f"Located {len(records)} active outside sensors in bounding box.")

📥 `Download this script: 01_spatial_filtering_via_bounding_boxes.py <https://raw.githubusercontent.com/carlkidcrypto/carlkidcrypto.github.io/main/example_scripts/purpleair-api-historical-data-bounding-box-queries/01_spatial_filtering_via_bounding_boxes.py>`_

Understanding Historical Data Constraints
=========================================

The PurpleAir historical API endpoint aggregates sensor measurements into
discrete temporal intervals. To prevent database contention and abusive point
consumption, the API enforces strict duration windows per request based on the
chosen averaging period:

.. list-table::
   :widths: 25 35 20
   :header-rows: 1

   * - Averaging Window
     - API Parameter Value
     - Max Span per Call
   * - Real-time (raw)
     - ``0``
     - 30 days
   * - 10-Minute Average (default)
     - ``10`` (or ``None`` default)
     - 60 days
   * - 30-Minute Average
     - ``30``
     - 90 days
   * - 1-Hour Average
     - ``60``
     - 180 days
   * - 1-Day Average
     - ``1440``
     - 2 years

Pass ``average=0`` explicitly to retrieve raw, unaggregated 2-minute sensor
reports. When ``average=None`` (or omitted), the API defaults to 10-minute
averages.

If a query specifies an interval larger than the allowed duration window, the
API rejects the request with HTTP 400. To collect long-term datasets, client
applications must chunk queries into discrete, compliant time slices.
Furthermore, PurpleAir requires a minimum delay of 1.0 second between historical
requests to adhere to rate limits.

Implementing a Robust Historical Extractor
==========================================

Below is a complete, production-ready script demonstrating how to discover
candidate sensors across a bounding box and iteratively download 1-hour
historical averages across a 60-day observation window:

.. code-block:: python

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

📥 `Download this script: 02_fetch_sensor_history_chunked.py <https://raw.githubusercontent.com/carlkidcrypto/carlkidcrypto.github.io/main/example_scripts/purpleair-api-historical-data-bounding-box-queries/02_fetch_sensor_history_chunked.py>`_

Best Practices for Scientific Data Extraction
=============================================

When publishing research or engineering analytics using PurpleAir historical
data:

1. **Verify Dual-Channel Consistency**: PurpleAir sensors incorporate dual
   Plantower laser counters (Channel A and Channel B). Large discrepancies
   between channels indicate sensor contamination or optical degradation.
2. **Apply Established EPA Correction Factors**: Raw Plantower PM2.5 readings
   frequently overestimate ambient concentrations in humid environments. Apply
   the national US EPA correction equations (such as the Barkjohn et al. model)
   incorporating relative humidity.
3. **Persist Raw Ingestion Artifacts**: Store the raw epoch timestamps and
   channel readings before transformation to maintain scientific
   reproducibility.

Summary & What's Next
=====================

By pairing bounding box spatial discovery with rate-limited, chunked historical
queries, `purpleair_api <https://github.com/carlkidcrypto/purpleair_api>`_
enables comprehensive geospatial and temporal environmental research without
cumbersome manual data wrangling.

In our next blog post, we will rotate to `purpleair_data_logger
<https://github.com/carlkidcrypto/purpleair_data_logger>`_, exploring how to
implement zero-dependency local sensor polling and offline SQLite/CSV archival
for air monitoring during connectivity outages.

----

.. warning::

   AI-generated content may contain misinformation or mistakes. A human does review this, but we are only human.

