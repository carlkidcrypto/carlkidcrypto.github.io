#!/usr/bin/env python3
"""Example script for: Monitoring Hardware Transceiver Optical Power (DOM/DDM) with ezsnmp
Source: https://carlkidcrypto.github.io/blog/ezsnmp-transceiver-optical-power-dom-telemetry.html
"""

import math
from ezsnmp import Session
from ezsnmp.exceptions import GenericError

# RFC 4133 & RFC 3433 OIDs
OID_ENT_PHYSICAL_NAME = "1.3.6.1.2.1.47.1.1.1.1.7"
OID_SENSOR_TYPE = "1.3.6.1.2.1.99.1.1.1.1"
OID_SENSOR_SCALE = "1.3.6.1.2.1.99.1.1.1.2"
OID_SENSOR_PRECISION = "1.3.6.1.2.1.99.1.1.1.3"
OID_SENSOR_VALUE = "1.3.6.1.2.1.99.1.1.1.4"

# SI Scale exponents per RFC 3433 EntitySensorDataScale
SCALE_EXPONENT = {
    "7": -6,   # micro
    "8": -3,   # milli
    "9": 0,    # units
}

def audit_optical_dom(
    host: str,
    community: str = "public",
    rx_warn_dbm: float = -12.0,
):
    session = Session(
        hostname=host,
        community=community,
        version=2,
        timeout=3,
        retries=1,
        set_max_repeaters_to_num=25,
    )

    try:
        print(f"[*] Auditing transceiver DOM/DDM power on {host}...")

        names = {
            v.index: v.value
            for v in session.bulk_walk(OID_ENT_PHYSICAL_NAME)
        }
        types = {
            v.index: v.value
            for v in session.bulk_walk(OID_SENSOR_TYPE)
        }
        scales = {
            v.index: v.value
            for v in session.bulk_walk(OID_SENSOR_SCALE)
        }
        precisions = {
            v.index: int(v.value)
            for v in session.bulk_walk(OID_SENSOR_PRECISION)
        }
        values = session.bulk_walk(OID_SENSOR_VALUE)

        for var in values:
            idx = var.index
            name = names.get(idx, f"Entity-{idx}")

            # Filter for optical power sensors (type 6 = watts)
            if types.get(idx) != "6":
                continue

            raw_val = int(var.value)
            precision = precisions.get(idx, 0)
            exp = SCALE_EXPONENT.get(scales.get(idx, "9"), 0)

            # Convert to watts, then to milliwatts, then to dBm
            watts = raw_val * (10 ** (-precision)) * (10 ** exp)
            mw = watts * 1000.0

            if mw <= 0:
                dbm_str = "-inf dBm (LOS)"
                is_low = True
            else:
                dbm = 10.0 * math.log10(mw)
                dbm_str = f"{dbm:.2f} dBm"
                is_low = ("rx" in name.lower()) and (dbm < rx_warn_dbm)

            prefix = "[!]" if is_low else "[+]"
            print(f"{prefix} {name:<36}: {dbm_str}")

    except GenericError as err:
        print(f"[-] SNMP optical audit failed: {err}")
