.. meta::
   :description: Get started with the official PurpleAir API Python wrapper (purpleair_api). Learn sensor discovery, read and write key separation, bounding box queries, and resilient rate-limited polling.
   :keywords: PurpleAir, Python, API, IoT, Air-Quality, Sensing, PM2.5, Open-Source, DevOps, carlkidcrypto
   :author: Carlos Santos (@carlkidcrypto)
   :property=og:title: Getting Started with the Python PurpleAir API Wrapper: Sensor Discovery, Keys & Rate Limits
   :property=og:description: Get started with the official PurpleAir API Python wrapper (purpleair_api). Learn sensor discovery, read and write key separation, bounding box queries, and resilient rate-limited polling.
   :property=og:type: article
   :property=og:url: https://carlkidcrypto.github.io/blog/purpleair-api-getting-started-guide.html
   :property=og:image: https://carlkidcrypto.github.io/_static/logo.png
   :name=twitter:card: summary
   :name=twitter:title: Getting Started with the Python PurpleAir API Wrapper: Sensor Discovery, Keys & Rate Limits
   :name=twitter:description: Get started with the official PurpleAir API Python wrapper (purpleair_api). Learn sensor discovery, read and write key separation, bounding box queries, and resilient rate-limited polling.
   :name=twitter:image: https://carlkidcrypto.github.io/_static/logo.png

===========================================================================================
Getting Started with the Python PurpleAir API Wrapper: Sensor Discovery, Keys & Rate Limits
===========================================================================================

.. note::

   * **Published:** November 04, 2026
   * **Authors:** Written by Gemini 3.8 Flash, Co-Authored & Reviewed by `Carlos Santos (@carlkidcrypto) <https://github.com/carlkidcrypto>`_
   * **Estimated Reading Time:** 5 minutes
   * **Tags:** `PurpleAir` • `Python` • `API` • `IoT` • `Air-Quality` • `Sensors` • `Open-Source`

Environmental air quality monitoring has evolved from centralized municipal
stations to dense hyper-local sensor networks. PurpleAir has established one of
the largest citizen-science sensor ecosystems globally, measuring airborne
particulate matter (PM1.0, PM2.5, PM10) alongside ambient temperature, relative
humidity, and atmospheric pressure.

Extracting programmatic telemetry from PurpleAir's REST API historically
required writing manual HTTP routines, tracking read versus write credentials,
managing query parameter encoding, and parsing JSON responses. The official
Python wrapper, `purpleair_api
<https://github.com/carlkidcrypto/purpleair_api>`_ (published on PyPI as
`purpleair-api <https://pypi.org/project/purpleair-api/>`_), streamlines these
interactions into a clean, modular Python 3 interface.

In this tutorial, we will explore the core architecture of ``purpleair_api``,
examine credential separation, inspect sensor discovery patterns, and implement
resilient polling workflows that safely handle API rate limits.

Understanding the PurpleAir API Architecture
============================================

The PurpleAir API separates access permissions between reading public or
private sensor telemetry and modifying cloud-hosted resources. To interact with
the service, developers must obtain dedicated API keys from PurpleAir:

- **Read Key (X-API-Key)**: Required for querying individual sensors, batching
  multi-sensor field requests, executing bounding-box geographic queries, and
  retrieving group data.
- **Write Key (X-API-Key)**: Required for mutating actions, such as creating
  custom sensor groups, registering member sensors to a group, and managing
  cloud metadata.
- **Local Access**: Modern PurpleAir sensors running on your local network
  expose a LAN JSON endpoint that does not require cloud API keys.

The ``purpleair_api`` package mirrors this domain structure through specialized
submodules coordinated by a unified facade class, ``PurpleAirAPI``:

- ``PurpleAirAPI``: The primary convenience entry point. It accepts optional
  read keys, write keys, and local IP addresses, automatically initializing the
  corresponding functional clients.
- ``PurpleAirReadAPI``: Dedicated client for read-only queries against the
  central PurpleAir cloud infrastructure.
- ``PurpleAirWriteAPI``: Dedicated client for creating and modifying sensor
  groups and member associations.
- ``PurpleAirLocalAPI``: Direct LAN client for querying local sensors over HTTP
  without consuming cloud API credits.

Installation and Requirements
=============================

The package requires Python 3.11 or newer (officially supported on Python 3.11 through 3.15, declaring ``python_requires = >=3.11,<3.16``) and relies on the foundational
``requests`` library for reliable HTTP networking.

Install the package directly from PyPI:

.. code-block:: bash

    pip install purpleair-api

Alternatively, you can install the latest development branch directly from
GitHub:

.. code-block:: bash

    git clone https://github.com/carlkidcrypto/purpleair_api.git
    cd purpleair_api/python
    pip install .

Initializing the Client
=======================

Depending on your application's security posture and scope, you can initialize
either the unified ``PurpleAirAPI`` facade or a focused submodule.

Using the Unified Facade
------------------------

When building data pipelines that both read telemetry and organize sensors
into tracked groups, instantiate ``PurpleAirAPI`` with your read and write
keys:

.. code-block:: python

    import os
    from purpleair_api.PurpleAirAPI import PurpleAirAPI

    # Retrieve credentials from environment variables
    read_key = os.getenv("PURPLEAIR_READ_KEY")
    write_key = os.getenv("PURPLEAIR_WRITE_KEY")

    # Initialize the unified wrapper
    paa = PurpleAirAPI(
        your_api_read_key=read_key,
        your_api_write_key=write_key
    )

    # Query sensor data directly through the facade
    sensor_id = 282168
    sensor_data = paa.request_sensor_data(sensor_index=sensor_id)
    print(f"Sensor Name: {sensor_data['sensor']['name']}")

📥 `Download this script: 01_using_the_unified_facade.py <https://raw.githubusercontent.com/carlkidcrypto/carlkidcrypto.github.io/main/example_scripts/purpleair-api-getting-started-guide/01_using_the_unified_facade.py>`_

Using the Focused Read Client
-----------------------------

For distributed worker agents, analytical dashboards, or microservices that
strictly consume telemetry without management privileges, instantiate
``PurpleAirReadAPI``. This avoids exposing write credentials to read-only
environments:

.. code-block:: python

    import os
    from purpleair_api.PurpleAirReadAPI import PurpleAirReadAPI

    read_key = os.getenv("PURPLEAIR_READ_KEY")
    read_client = PurpleAirReadAPI(api_read_key=read_key)

    # Request specific environmental telemetry fields
    fields = [
        "name",
        "pm2.5_atm",
        "pm2.5_cf_1",
        "temperature",
        "humidity",
        "pressure",
    ]
    telemetry = read_client.request_sensor_data(
        sensor_index=282168,
        fields=",".join(fields)
    )

    sensor = telemetry["sensor"]
    print(f"Station: {sensor.get('name')}")
    print(f"PM2.5 (ATM): {sensor.get('pm2.5_atm')} ug/m3")
    print(f"Temperature: {sensor.get('temperature')} deg F")

📥 `Download this script: 02_using_the_focused_read_client.py <https://raw.githubusercontent.com/carlkidcrypto/carlkidcrypto.github.io/main/example_scripts/purpleair-api-getting-started-guide/02_using_the_focused_read_client.py>`_

Querying Multiple Sensors and Bounding Boxes
============================================

Querying individual sensors sequentially across a regional footprint introduces
unnecessary network latency and exhausts API points quickly. The PurpleAir API
supports querying multiple sensors in a single transaction via geographic
bounding boxes or custom sensor index lists.

With ``PurpleAirReadAPI``, you can specify rectangular geographic coordinates
defined by northwest and southeast latitude/longitude corners:

.. code-block:: python

    import os
    from purpleair_api.PurpleAirReadAPI import PurpleAirReadAPI

    read_client = PurpleAirReadAPI(os.getenv("PURPLEAIR_READ_KEY"))

    # Bounding box coordinates for the Inland Northwest (Palouse region)
    nwlng = -117.20
    nwlat = 46.80
    selng = -116.90
    selat = 46.65

    # Request specific fields to minimize payload overhead
    query_fields = "name,latitude,longitude,pm2.5_atm,temperature"

    response = read_client.request_multiple_sensors_data(
        fields=query_fields,
        nwlng=nwlng,
        nwlat=nwlat,
        selng=selng,
        selat=selat,
        location_type=0  # 0 = Outside sensors, 1 = Inside sensors
    )

    fields_header = response.get("fields", [])
    data_rows = response.get("data", [])
    print(f"Discovered {len(data_rows)} sensors in bounding box.")

    # Map fields to values for easy dictionary access
    for row in data_rows[:5]:
        row_dict = dict(zip(fields_header, row))
        print(
            f"Sensor {row_dict.get('name')}: "
            f"PM2.5 = {row_dict.get('pm2.5_atm')} ug/m3"
        )

📥 `Download this script: 03_querying_multiple_sensors_and_bounding_b.py <https://raw.githubusercontent.com/carlkidcrypto/carlkidcrypto.github.io/main/example_scripts/purpleair-api-getting-started-guide/03_querying_multiple_sensors_and_bounding_b.py>`_

Managing Sensor Groups with Write Credentials
=============================================

When tracking a designated fleet of outdoor air quality monitors (such as
municipal parks, school districts, or industrial perimeters), querying by
bounding box can capture irrelevant or unverified devices. Creating a custom
sensor group organizes your target fleet under a single, reusable entity.

Using ``PurpleAirWriteAPI``, you can programmatically provision groups and
register sensor members:

.. code-block:: python

    import os
    from purpleair_api.PurpleAirWriteAPI import PurpleAirWriteAPI

    write_key = os.getenv("PURPLEAIR_WRITE_KEY")
    write_client = PurpleAirWriteAPI(api_write_key=write_key)

    # Create a new sensor tracking group
    new_group = write_client.post_create_group_data(
        name="Municipal Palouse Monitors"
    )
    group_id = new_group["group_id"]
    print(f"Created Group ID: {group_id}")

    # Register target sensors into the newly created group
    target_sensors = [282168, 175420, 194382]
    for sensor_id in target_sensors:
        write_client.post_create_member(
            group_id=group_id,
            sensor_index=sensor_id
        )
        print(f"Enrolled sensor {sensor_id} into group {group_id}")

📥 `Download this script: 04_managing_sensor_groups_with_write_creden.py <https://raw.githubusercontent.com/carlkidcrypto/carlkidcrypto.github.io/main/example_scripts/purpleair-api-getting-started-guide/04_managing_sensor_groups_with_write_creden.py>`_

Once populated, the entire group can be queried using ``request_members_data``
on your read client, retrieving batch readings for enrolled sensors in a single
API transaction.

Rate Limiting and Production Resilience
=======================================

The PurpleAir API enforces rate limits and credit-based points accounting.
High-frequency polling without rate control risks receiving HTTP 429 (Too Many
Requests) or 402 (Payment Required) responses.

To ensure production stability, implement exponential backoff, request
throttling, and field filtering:

1. **Request Only Required Fields**: The PurpleAir API measures point costs
   partially based on returned fields. Requesting ``*`` or omitted field filters
   drains your account balance significantly faster. Always specify the exact
   comma-separated fields required by your telemetry pipeline.
2. **Handle Transient Network Failures**: Encapsulate calls with retries using
   exponential backoff for HTTP 429 and 5xx responses.
3. **Prefer Local API for LAN Sensors**: If your sensors reside on the same
   local network as your logging service, use ``PurpleAirLocalAPI``. Local
   polling queries the device directly over LAN, eliminating cloud API credit
   costs and cloud internet dependencies.

Here is a resilient query helper pattern:

.. code-block:: python

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

📥 `Download this script: 05_resilient_sensor_query.py <https://raw.githubusercontent.com/carlkidcrypto/carlkidcrypto.github.io/main/example_scripts/purpleair-api-getting-started-guide/05_resilient_sensor_query.py>`_

Summary & What's Next
=====================

The ``purpleair_api`` package provides a robust, Pythonic abstraction over the
PurpleAir REST API. By separating read, write, and local responsibilities, it
enables developers to build clean data ingestion pipelines without managing
raw HTTP sessions or manual query string construction.

In our next blog post, we will explore `purpleair_data_logger
<https://github.com/carlkidcrypto/purpleair_data_logger>`_, examining how to
automate continuous ingestion of PurpleAir sensor streams into TimeScaleDB and
PostgreSQL databases for long-term time-series analysis and Grafana
dashboards.

----

.. warning::

   AI-generated content may contain misinformation or mistakes. A human does review this, but we are only human.

