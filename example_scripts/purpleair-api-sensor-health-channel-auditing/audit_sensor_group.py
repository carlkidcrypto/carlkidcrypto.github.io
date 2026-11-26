#!/usr/bin/env python3
"""Example script for: Automated Sensor Health Auditing with purpleair_api
Source: https://carlkidcrypto.github.io/blog/purpleair-api-sensor-health-channel-auditing.html
"""

import os
from typing import Any, Dict, List

from purpleair_api.PurpleAirAPIError import PurpleAirAPIError
from purpleair_api.PurpleAirReadAPI import PurpleAirReadAPI

AUDIT_FIELDS = [
    "name",
    "pm2.5_atm_a",
    "pm2.5_atm_b",
    "channel_flags",
    "confidence",
    "uptime",
    "rssi",
]

CHANNEL_FLAG_LABELS = {
    0: "Normal",
    1: "A-Downgraded",
    2: "B-Downgraded",
    3: "A+B-Downgraded",
}


def evaluate_channel_agreement(pm_a: float, pm_b: float) -> Dict[str, Any]:
    abs_diff = abs(pm_a - pm_b)
    mean_val = (pm_a + pm_b) / 2.0
    rpd_pct = (abs_diff / mean_val * 100.0) if mean_val > 0 else 0.0

    if mean_val <= 25.0:
        passed = abs_diff <= 5.0
        rule = "abs_diff <= 5.0 ug/m3"
    else:
        passed = rpd_pct <= 20.0
        rule = "RPD <= 20%"

    return {
        "passed": passed,
        "abs_diff": round(abs_diff, 2),
        "rpd_pct": round(rpd_pct, 1),
        "rule": rule,
    }


def audit_sensor_group(read_key: str, group_id: int) -> List[Dict[str, Any]]:
    client = PurpleAirReadAPI(api_read_key=read_key)
    findings: List[Dict[str, Any]] = []

    try:
        response = client.request_members_data(
            group_id=group_id,
            fields=",".join(AUDIT_FIELDS),
        )
    except PurpleAirAPIError as err:
        print(f"[-] PurpleAir API error auditing group {group_id}: {err}")
        return findings

    headers = response.get("fields", [])
    for row in response.get("data", []):
        record = dict(zip(headers, row))
        name = record.get("name", "Unknown")
        pm_a = record.get("pm2.5_atm_a")
        pm_b = record.get("pm2.5_atm_b")
        flag = record.get("channel_flags", 0)
        conf = record.get("confidence", 100)

        if pm_a is None or pm_b is None:
            findings.append(
                {
                    "name": name,
                    "status": "DEGRADED",
                    "reason": "Missing dual-channel readings",
                }
            )
            continue

        qa = evaluate_channel_agreement(float(pm_a), float(pm_b))
        flag_label = CHANNEL_FLAG_LABELS.get(flag, f"Flag-{flag}")

        if flag != 0 or conf < 80 or not qa["passed"]:
            findings.append(
                {
                    "name": name,
                    "status": "ALERT",
                    "flag": flag_label,
                    "confidence": conf,
                    "pm_a": pm_a,
                    "pm_b": pm_b,
                    "rpd_pct": qa["rpd_pct"],
                }
            )

    return findings


if __name__ == "__main__":
    key = os.environ["PURPLEAIR_READ_KEY"]
    group = int(os.environ.get("PURPLEAIR_GROUP_ID", "1234"))
    alerts = audit_sensor_group(read_key=key, group_id=group)

    if not alerts:
        print("[+] All monitored sensors passed dual-channel QA/QC.")
    else:
        print(f"[!] Found {len(alerts)} sensors needing inspection:")
        for item in alerts:
            print(f"    - {item}")
