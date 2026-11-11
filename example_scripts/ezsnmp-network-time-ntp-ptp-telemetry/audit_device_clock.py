#!/usr/bin/env python3
"""Example script for: Network Time & Clock Synchronization Telemetry with ezsnmp
Source: https://carlkidcrypto.github.io/blog/ezsnmp-network-time-ntp-ptp-telemetry.html
"""

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

def parse_numeric(val, default=0.0):
    try:
        return float(str(val).strip())
    except (ValueError, TypeError):
        return default

def parse_int(val, default=0):
    digits = "".join(c for c in str(val) if c.isdigit() or c == "-")
    try:
        return int(digits)
    except (ValueError, TypeError):
        return default

def audit_device_clock(hostname: str, community: str = "public"):
    """Audit NTP synchronization status, stratum, and offset via ezsnmp."""
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

        raw_mode = str(mode_var.value).strip()
        if raw_mode.isdigit():
            mode_code = int(raw_mode)
            mode_name = NTP_MODE_MAP.get(mode_code, f"UNKNOWN_{mode_code}")
        else:
            mode_name = raw_mode.upper()
            mode_code = {v: k for k, v in NTP_MODE_MAP.items()}.get(mode_name, 0)

        stratum = parse_int(stratum_var.value, 16)
        active_source = active_src_var.value
        offset = parse_numeric(offset_var.value, 0.0)
        dispersion = parse_numeric(dispersion_var.value, 0.0)

        # Evaluate health: must be mode 5 or 6, stratum < 16, offset < 10ms
        is_synced = mode_code in (5, 6)
        stratum_ok = 1 <= stratum <= 4
        offset_ok = abs(offset) < 10.0  # Alert if clock skew exceeds 10ms

        alert = (not is_synced) or (not stratum_ok) or (not offset_ok)

        status = "HEALTHY"
        if not is_synced:
            status = "UNSYNCHRONIZED"
        elif not stratum_ok:
            status = f"HIGH_STRATUM_{stratum}"
        elif not offset_ok:
            status = f"CLOCK_SKEW_EXCESSIVE_{offset:.2f}ms"

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
