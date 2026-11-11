#!/usr/bin/env python3
"""Example script for: Hardware Health & Optical Power Monitoring (DOM/DDM) in ezsnmp
Source: https://carlkidcrypto.github.io/blog/ezsnmp-hardware-optical-dom-monitoring.html
"""

from ezsnmp import Session
from ezsnmp.exceptions import GenericError

# RFC 3433 sensor scale exponents advancing in powers of 1,000 (10^3)
SCALE_EXPONENTS = {
    1: -24, 2: -21, 3: -18, 4: -15, 5: -12, 6: -9, 7: -6, 8: -3,
    9: 0, 10: 3, 11: 6, 12: 9, 13: 12, 14: 15, 15: 18, 16: 21, 17: 24,
}

def audit_optical_sensors(hostname: str, community: str = "public"):
    session = Session(
        hostname=hostname,
        community=community,
        version=2,
        timeout=2,
        retries=1,
        print_enums_numerically=True,
        set_max_repeaters_to_num=25
    )

    try:
        # 1. Map physical sensor IDs to human-readable names
        name_vars = session.bulk_walk("entPhysicalName")
        sensor_names = {v.index: v.value for v in name_vars}

        # 2. Bulk-walk sensor telemetry columns (RFC 3433 standard)
        # Falls back to vendor/Cisco entSensor* columns if MIB uses legacy names
        try:
            type_vars = session.bulk_walk("entPhySensorType")
            scale_vars = session.bulk_walk("entPhySensorScale")
            prec_vars = session.bulk_walk("entPhySensorPrecision")
            val_vars = session.bulk_walk("entPhySensorValue")
            status_vars = session.bulk_walk("entPhySensorOperStatus")
        except GenericError:
            type_vars = session.bulk_walk("entSensorType")
            scale_vars = session.bulk_walk("entSensorScale")
            prec_vars = session.bulk_walk("entSensorPrecision")
            val_vars = session.bulk_walk("entSensorValue")
            status_vars = session.bulk_walk("entSensorStatus")

        scales = {v.index: int(v.value) for v in scale_vars}
        precisions = {v.index: int(v.value) for v in prec_vars}
        values = {v.index: int(v.value) for v in val_vars}
        statuses = {v.index: int(v.value) for v in status_vars}

        optical_report = []

        for v in type_vars:
            idx = v.index
            sensor_type = int(v.value)
            name = sensor_names.get(idx, f"Sensor-{idx}")

            # Focus on optical power sensors (dBm = 14) and temperature (celsius = 8)
            if sensor_type in (8, 14) and statuses.get(idx) == 1:
                raw_val = values.get(idx, 0)
                scale = scales.get(idx, 9)
                precision = precisions.get(idx, 0)

                # Compute calibrated floating-point metric with scale exponent
                scale_exp = SCALE_EXPONENTS.get(scale, (scale - 9) * 3)
                calibrated = raw_val * (10 ** (scale_exp - precision))
                unit = "dBm" if sensor_type == 14 else "C"

                # Flag optical signal attenuation based on optics class
                warning = False
                is_rx_power = sensor_type == 14 and "Rx" in name
                # Standard 10G-SR baseline warning floor (-12.0 dBm)
                if is_rx_power and calibrated < -12.0:
                    warning = True

                optical_report.append({
                    "sensor": name,
                    "value": round(calibrated, 2),
                    "unit": unit,
                    "warning": warning
                })

        return optical_report

    except GenericError as exc:
        print(f"[{hostname}] Optical telemetry audit failed: {exc}")
        return []

if __name__ == "__main__":
    telemetry = audit_optical_sensors("edge-leaf01.internal")
    print("--- Optical Diagnostic Monitoring Report ---")
    for item in telemetry:
        flag = " [LOW SIGNAL ALERT]" if item["warning"] else ""
        sensor = item["sensor"]
        val = item["value"]
        unit = item["unit"]
        print(f"  {sensor:<28} : {val:>6.2f} {unit}{flag}")
