#!/usr/bin/env python3
"""Example script for: Network Time & Clock Synchronization Telemetry with ezsnmp
Source: https://carlkidcrypto.github.io/blog/ezsnmp-network-time-ntp-ptp-telemetry.html
"""

import re
from ezsnmp import Session
from ezsnmp.exceptions import GenericError

NTP_MODE_MAP = {
    1: "NOT_RUNNING",
    2: "NOT_SYNCHRONIZED",
    3: "NONE_CONFIGURED",
    4: "SYNC_TO_LOCAL",
    5: "SYNC_TO_REFCLOCK",
    6: "SYNC_TO_REMOTE_SERVER",
}

MAX_OFFSET_MS = 10.0
MAX_DISPERSION_MS = 1000.0  # Alert if root dispersion exceeds 1000ms

def parse_offset_ms(val) -> float | None:
    """Parse magnitude and unit, normalizing to milliseconds."""
    if val is None:
        return None
    s = str(val).strip().lower()
    m = re.match(r"^([+-]?\d+(?:\.\d+)?)\s*([a-z]*)$", s)
    if not m:
        return None
    num = float(m.group(1))
    unit = m.group(2)
    if unit in ("s", "sec", "second", "seconds"):
        return num * 1000.0
    elif unit in ("us", "usec", "microsecond", "microseconds"):
        return num / 1000.0
    elif unit in ("ns", "nsec", "nanosecond", "nanoseconds"):
        return num / 1000000.0
    return num

def parse_int(val, default=0):
    digits = "".join(c for c in str(val) if c.isdigit() or c == "-")
    try:
        return int(digits)
    except (ValueError, TypeError):
        return default

def is_valid_result(var) -> bool:
    if var is None:
        return False
    t = getattr(var, "type", None)
    if t in ("NOSUCHOBJECT", "NOSUCHINSTANCE", "ENDOFMIBVIEW"):
        return False
    return True

def audit_device_clock(hostname: str, community: str = "public"):
    """Audit NTP synchronization status, stratum, offset, and dispersion via ezsnmp."""
    session = Session(
        hostname=hostname,
        community=community,
        version=2,
        timeout=2,
        retries=1,
        print_enums_numerically=True
    )

    try:
        # 1. Query System NTP Status scalar objects
        vars = session.get([
            "ntpEntStatusCurrentMode.0",
            "ntpEntStatusStratum.0",
            "ntpEntStatusActiveRefSourceId.0",
            "ntpEntStatusActiveOffset.0",
            "ntpEntStatusDispersion.0",
        ])
        mode_var, stratum_var, active_src_var, offset_var, dispersion_var = vars

        # Verify scalar presence before treating as 0
        if not all(is_valid_result(v) for v in vars):
            return {
                "hostname": hostname,
                "mode": "UNKNOWN",
                "stratum": 16,
                "source": "None",
                "offset_ms": 0.0,
                "dispersion_ms": 0.0,
                "status": "TELEMETRY_UNAVAILABLE",
                "alert": True,
            }

        raw_mode = str(mode_var.value).strip()
        if raw_mode.isdigit():
            mode_code = int(raw_mode)
            mode_name = NTP_MODE_MAP.get(mode_code, f"UNKNOWN_{mode_code}")
        else:
            mode_name = raw_mode.upper()
            mode_code = {v: k for k, v in NTP_MODE_MAP.items()}.get(mode_name, 0)

        stratum = parse_int(stratum_var.value, 16)
        active_source = active_src_var.value
        offset = parse_offset_ms(offset_var.value)
        dispersion = parse_offset_ms(dispersion_var.value)

        if offset is None or dispersion is None:
            return {
                "hostname": hostname,
                "mode": mode_name,
                "stratum": stratum,
                "source": str(active_source),
                "offset_ms": 0.0,
                "dispersion_ms": 0.0,
                "status": "PARSE_ERROR_INVALID_UNITS",
                "alert": True,
            }

        is_synced = mode_code in (5, 6)
        stratum_ok = 1 <= stratum <= 4
        offset_ok = abs(offset) <= MAX_OFFSET_MS
        dispersion_ok = dispersion <= MAX_DISPERSION_MS

        alert = (not is_synced) or (not stratum_ok) or (not offset_ok) or (not dispersion_ok)

        status = "HEALTHY"
        if not is_synced:
            status = "UNSYNCHRONIZED"
        elif not stratum_ok:
            status = f"HIGH_STRATUM_{stratum}"
        elif not offset_ok:
            status = f"CLOCK_SKEW_EXCESSIVE_{offset:.2f}ms"
        elif not dispersion_ok:
            status = f"DISPERSION_EXCESSIVE_{dispersion:.2f}ms"

        return {
            "hostname": hostname,
            "mode": mode_name,
            "stratum": stratum,
            "source": active_source,
            "offset_ms": offset,
            "dispersion_ms": dispersion,
            "status": status,
            "alert": alert,
        }

    except GenericError as exc:
        print(f"[{hostname}] Clock telemetry audit failed: {exc}")
        return None

if __name__ == "__main__":
    result = audit_device_clock("core-rtr01.internal")
    if result:
        flag = " [CRITICAL TIME ALERT]" if result["alert"] else " [OK]"
        print("--- Network Time Telemetry Report ---")
        print(f"  Target Host         : {result['hostname']}")
        print(f"  Sync Status         : {result['mode']}{flag}")
        print(f"  Stratum Level       : {result['stratum']}")
        print(f"  Active Time Source  : {result['source']}")
        print(f"  Measured Offset     : {result['offset_ms']:.3f} ms")
        print(f"  Root Dispersion     : {result['dispersion_ms']:.3f} ms")
        print(f"  Overall Health      : {result['status']}")
