#!/usr/bin/env python3
"""Example script for: Working with the Matter Device Converter: Mapping Sensor Data to Matter 1.5.1 Clusters
Source: https://carlkidcrypto.github.io/blog/purpleair-api-matter-device-converter-guide.html
"""

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
