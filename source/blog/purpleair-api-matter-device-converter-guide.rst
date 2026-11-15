.. meta::
   :description: Convert PurpleAir PM2.5, VOC, temperature, humidity, and pressure readings into CSA Matter 1.5.1 cluster payloads and US EPA AQI ratings in Python.
   :keywords: PurpleAir, Python, Matter, IoT, Smart-Home, Air-Quality, purpleair_api, Open-Source
   :author: Carlos Santos (@carlkidcrypto)
   :property=og:title: Working with the Matter Device Converter: Mapping Sensor Data to Matter 1.5.1 Clusters
   :property=og:description: Convert PurpleAir PM2.5, VOC, temperature, humidity, and pressure readings into CSA Matter 1.5.1 cluster payloads and US EPA AQI ratings in Python.
   :property=og:type: article
   :property=og:url: https://carlkidcrypto.github.io/blog/purpleair-api-matter-device-converter-guide.html
   :property=og:image: https://carlkidcrypto.github.io/_static/logo.png
   :name=twitter:card: summary
   :name=twitter:title: Working with the Matter Device Converter: Mapping Sensor Data to Matter 1.5.1 Clusters
   :name=twitter:description: Convert PurpleAir PM2.5, VOC, temperature, humidity, and pressure readings into CSA Matter 1.5.1 cluster payloads and US EPA AQI ratings in Python.
   :name=twitter:image: https://carlkidcrypto.github.io/_static/logo.png

======================================================================================
Working with the Matter Device Converter: Mapping Sensor Data to Matter 1.5.1 Clusters
======================================================================================

.. note::

   * **Published:** November 12, 2026
   * **Authors:** Written by Gemini 3.8 Flash, Co-Authored & Reviewed by `Carlos Santos (@carlkidcrypto) <https://github.com/carlkidcrypto>`_
   * **Estimated Reading Time:** 5 minutes
   * **Tags:** `PurpleAir` • `Python` • `Matter` • `IoT` • `Smart-Home` • `Air-Quality` • `Open-Source`

Smart home interoperability has entered a new era with the Connectivity
Standards Alliance (CSA) Matter specification. Standardized device definitions
allow certified environmental hardware to communicate directly with Apple Home,
Home Assistant, Google Home, and Amazon Alexa over local IPv6 networks.

However, bridging raw sensor measurements into Matter schemas often requires
complex, error-prone transformations: converting Fahrenheit to signed 16-bit
Celsius values scaled by 100, calculating EPA Air Quality Index (AQI) ratings
from PM2.5 concentrations, and structuring nested cluster dictionaries.

To solve this for Python developers, the official `purpleair_api
<https://github.com/carlkidcrypto/purpleair_api>`_ package (available on PyPI
as `purpleair-api <https://pypi.org/project/purpleair-api/>`_) includes a
dedicated submodule: ``PurpleAirMatterConverter``.

In this tutorial, we will explore the architecture of
``PurpleAirMatterConverter``, examine how it generates Matter 1.5.1-compliant
data structures, and demonstrate how to convert cloud and local sensor payloads
for smart home bridges.

The Architecture of PurpleAirMatterConverter
============================================

The ``PurpleAirMatterConverter`` acts as a deterministic schema adapter. It
ingests raw telemetry dictionaries produced by ``PurpleAirReadAPI`` (cloud) or
``PurpleAirLocalAPI`` (LAN) and emits normalized objects aligned with the
Matter 1.5.1 Application Cluster Specification.

Key responsibilities handled automatically by the converter:

- **US EPA AQI Calculation**: Ingests raw PM2.5 readings (in ug/m3) and
  calculates both the continuous numeric EPA AQI (0–500+) and categorical health
  ratings according to official US EPA breakpoints.
- **Matter AirQuality Cluster (0x005D) Mapping**: Maps EPA AQI categories to
  standard ``MatterAirQualityRating`` enum ratings (``UNKNOWN``,
  ``EXCELLENT``, ``GOOD``, ``FAIR``, ``POOR``, ``VERY_POOR``, and
  ``EXTREMELY_POOR``).
- **Physical Attribute Scaling**: Scales ambient temperature into 0.01 deg C
  signed integers (Cluster ``0x0402``), relative humidity into 0.01% unsigned
  integers (Cluster ``0x0405``), and atmospheric pressure from PSI into 0.1 kPa
  (hPa) integers via ``pressure_psi_to_kpa`` (Cluster ``0x0403``).
- **Standardized Device Models**: Emits full endpoint topologies for the
  **Air Quality Sensor Device Type (0x002D)**, **Temperature Sensor (0x0302)**,
  and **Environmental Sensor (0x0307)**.

Converting Cloud Sensor Telemetry
=================================

When monitoring remote sensors via the PurpleAir cloud API, you can fetch live
station data using ``PurpleAirReadAPI`` and convert it into a Matter device in a
single functional call:

.. code-block:: python

    import os
    from purpleair_api.PurpleAirReadAPI import PurpleAirReadAPI
    from purpleair_api.PurpleAirMatterConverter import PurpleAirMatterConverter

    # Initialize read client with your PurpleAir API Read Key
    read_key = os.environ["PURPLEAIR_READ_KEY"]
    pa_client = PurpleAirReadAPI(api_read_key=read_key)

    # Fetch raw station telemetry (e.g., station 282168)
    sensor_index = 282168
    raw_payload = pa_client.request_sensor_data(sensor_index=sensor_index)

    # Convert to Matter 1.5.1 Air Quality Sensor schema
    matter_device = PurpleAirMatterConverter.to_air_quality_sensor(raw_payload)

    # Inspect the high-level EPA air quality assessment
    summary = matter_device["air_quality_summary"]
    print(f"Station: {raw_payload['sensor']['name']}")
    print(f"EPA AQI: {summary['epa_aqi']}")
    print(f"EPA Category: {summary['epa_category']}")
    print(f"Matter Rating: {summary['matter_air_quality_rating']}")

📥 `Download this script: 01_converting_cloud_sensor_telemetry.py <https://raw.githubusercontent.com/carlkidcrypto/carlkidcrypto.github.io/main/example_scripts/purpleair-api-matter-device-converter-guide/01_converting_cloud_sensor_telemetry.py>`_

Inspecting Matter Cluster Payloads
==================================

The converted dictionary exposes calibrated clusters under semantic keys mapped
to Matter Application Cluster IDs and attributes:

.. code-block:: python

    from purpleair_api.PurpleAirMatterConverter import PurpleAirMatterConverter

    # Simulated PurpleAir cloud telemetry payload (pressure in PSI)
    cloud_payload = {
        "sensor": {
            "sensor_index": 282168,
            "name": "Outdoor Station",
            "pm2.5": 12.5,
            "pm1.0": 5.7,
            "pm10.0": 18.4,
            "voc": 85.0,
            "temperature": 72.0,
            "humidity": 45.0,
            "pressure": 14.696,
        }
    }

    matter_device = PurpleAirMatterConverter.to_air_quality_sensor(cloud_payload)
    clusters = matter_device["clusters"]

    # 1. Air Quality & Particulate Measurements (Cluster 0x005D)
    aq_attrs = clusters["air_quality_measurement"]["attributes"]
    print(f"AirQuality Enum (0x005D): {aq_attrs['airQuality']}")
    print(f"PM2.5 MeasuredValue (ug/m3 x 100): {aq_attrs['measuredValue']}")
    print(f"PM1.0 Density (ug/m3 x 100): {aq_attrs['pm1Density']}")

    # 2. Temperature Measurement (0x0402) - Scaled 0.01 deg C
    temp_val = clusters["temperature_measurement"]["attributes"]["measuredValue"]
    print(f"Temperature: {temp_val / 100.0:.2f} deg C (int16: {temp_val})")

    # 3. Relative Humidity Measurement (0x0405) - Scaled 0.01 %
    rh_val = clusters["humidity_measurement"]["attributes"]["measuredValue"]
    print(f"Relative Humidity: {rh_val / 100.0:.2f} % (uint16: {rh_val})")

    # 4. Pressure Measurement (0x0403) - Scaled 0.1 kPa (hPa)
    pres_val = clusters["pressure_measurement"]["attributes"]["measuredValue"]
    print(f"Pressure: {pres_val / 10.0:.1f} kPa (int16: {pres_val})")

📥 `Download this script: 02_inspecting_matter_cluster_payloads.py <https://raw.githubusercontent.com/carlkidcrypto/carlkidcrypto.github.io/main/example_scripts/purpleair-api-matter-device-converter-guide/02_inspecting_matter_cluster_payloads.py>`_

Converting Local LAN Sensor Telemetry
=====================================

For local, zero-cloud smart home automation, fetch raw JSON payloads directly
from your monitor's LAN IP endpoint (``http://<sensor_ip>/json``), normalise the
LAN field names into ``PurpleAirMatterConverter``'s canonical keys, and convert
them into Matter clusters:

.. code-block:: python

    import requests
    from purpleair_api.PurpleAirMatterConverter import (
        PurpleAirMatterConverter as Conv,
    )

    # Query local sensor web server directly over LAN
    local_sensor_ip = "192.168.1.150"
    response = requests.get(f"http://{local_sensor_ip}/json", timeout=5)
    response.raise_for_status()
    lan_data = response.json()

    # Normalise LAN /json keys (convert pressure from hPa/mbar to PSI)
    normalized_data = {
        "name": lan_data.get("SensorId", local_sensor_ip),
        "pm2.5": lan_data.get("pm2_5_atm"),
        "pm1.0": lan_data.get("pm1_0_atm"),
        "pm10.0": lan_data.get("pm10_0_atm"),
        "temperature": lan_data.get("current_temp_f"),
        "humidity": lan_data.get("current_humidity"),
        "pressure": (
            lan_data["pressure"] / 68.94757
            if lan_data.get("pressure") is not None
            else None
        ),
    }

    # Convert directly to Matter Air Quality Sensor representation
    local_matter_sensor = Conv.to_air_quality_sensor(normalized_data)

    print("Successfully mapped local sensor to Matter endpoint structure:")
    print(f"Node Device Type: {local_matter_sensor['device_type']['label']}")
    print(f"EPA AQI: {local_matter_sensor['air_quality_summary']['epa_aqi']}")

📥 `Download this script: 03_converting_local_lan_sensor_telemetry.py <https://raw.githubusercontent.com/carlkidcrypto/carlkidcrypto.github.io/main/example_scripts/purpleair-api-matter-device-converter-guide/03_converting_local_lan_sensor_telemetry.py>`_

Integration with Smart Home Bridges
===================================

The data structures produced by ``PurpleAirMatterConverter`` can be served
directly to Matter ecosystems:

1. **Matterbridge Plugins**: The JSON payload can be exposed via an internal
   REST or WebSocket endpoint, consumed directly by `purpleair-matterbridge
   <https://github.com/carlkidcrypto/purpleair-matterbridge>`_ to instantiate
   Bridged Node endpoints.
2. **Python Matter Server**: For custom integrations using
   ``python-matter-server`` (Home Assistant's native Matter backend), the
   attribute dictionaries map 1:1 to Matter cluster attribute write requests.
3. **Automated Handoffs**: By separating data acquisition from Matter protocol
   encoding, telemetry ingestion scripts remain clean and decoupled from
   smart home transport specifics.

Summary & What's Next
=====================

The ``PurpleAirMatterConverter`` in `purpleair_api
<https://github.com/carlkidcrypto/purpleair_api>`_ bridges the gap between raw
environmental data and formal Matter smart home specifications. Developers gain
instant EPA AQI math, attribute scaling, and standardized cluster mappings in
pure Python.

In our next blog post, we will rotate to `purpleair_data_logger
<https://github.com/carlkidcrypto/purpleair_data_logger>`_, exploring how to
build automated Grafana dashboards over TimescaleDB to visualize historical air
quality trends, heatmaps, and particulate anomalies.

----

.. warning::

   AI-generated content may contain misinformation or mistakes. A human does review this, but we are only human.

