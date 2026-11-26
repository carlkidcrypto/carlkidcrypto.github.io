.. meta::
   :description: Low-cost optical particulate sensors democratize hyper-local air quality monitoring, yet outdoor deployments face harsh environmental stressors. Spider webs...
   :keywords: Purpleair, Python, Api, Qaqc, Air-Quality, Iot, Open-Source, Python, ezsnmp, Networking, DevOps
   :author: Carlos Santos (@carlkidcrypto)
   :property=og:title: Automated Sensor Health Auditing with purpleair_api
   :property=og:description: Low-cost optical particulate sensors democratize hyper-local air quality monitoring, yet outdoor deployments face harsh environmental stressors. Spider webs...
   :property=og:type: article
   :property=og:url: https://carlkidcrypto.github.io/blog/purpleair-api-sensor-health-channel-auditing.html
   :property=og:image: https://carlkidcrypto.github.io/_static/logo.png
   :name=twitter:card: summary
   :name=twitter:title: Automated Sensor Health Auditing with purpleair_api
   :name=twitter:description: Low-cost optical particulate sensors democratize hyper-local air quality monitoring, yet outdoor deployments face harsh environmental stressors. Spider webs...
   :name=twitter:image: https://carlkidcrypto.github.io/_static/logo.png

============================================================
Automated Sensor Health Auditing with purpleair_api
============================================================

.. note::

   * **Published:** November 22, 2026
   * **Authors:** Written by Gemini 3.8 Flash, Co-Authored & Reviewed by `Carlos Santos (@carlkidcrypto) <https://github.com/carlkidcrypto>`_
   * **Estimated Reading Time:** 7 minutes
   * **Tags:** `Purpleair` • `Python` • `Api` • `Qaqc` • `Air-Quality` • `Iot` • `Open-Source`

Low-cost optical particulate sensors democratize hyper-local air quality
monitoring, yet outdoor deployments face harsh environmental stressors. Spider
webs inside optical chambers, spider mites, high-humidity condensation, and
aging laser diodes can cause a sensor to report wildly inflated PM2.5 readings
even while its Wi-Fi telemetry remains online.

To guard against silent hardware drift, outdoor PurpleAir monitors (such as the
PA-II and Flex models) incorporate **two independent Plantower laser particle
counters**: Channel A and Channel B. Under healthy operating conditions, both
lasers sample the same ambient air stream and track closely together.

Using `purpleair_api <https://github.com/carlkidcrypto/purpleair_api>`_
(available on PyPI as `purpleair-api
<https://pypi.org/project/purpleair-api/>`_), developers can query both
individual channels alongside PurpleAir's ``channel_flags`` and ``confidence``
fields to automate fleet-wide Quality Assurance / Quality Control (QA/QC)
auditing.

In this tutorial, we will inspect PurpleAir's dual-channel API fields, apply
concentration-dependent EPA QA/QC agreement thresholds, and build an automated
fleet auditor using ``PurpleAirReadAPI``.

Understanding Dual-Channel Telemetry & Flags
============================================

When you request the standard ``pm2.5_atm`` field, the PurpleAir API returns an
average of Channel A and Channel B (excluding any channel already marked as
downgraded). To audit hardware health directly, explicitly request the
per-channel fields and diagnostic metadata:

- ``pm2.5_atm_a`` and ``pm2.5_atm_b``: Independent ATM-corrected PM2.5 mass
  concentrations (ug/m3) from laser counters A and B.
- ``channel_flags``: Integer status bitmask indicating whether PurpleAir's
  backend has flagged a channel:
  ``0`` (Normal), ``1`` (A-Downgraded), ``2`` (B-Downgraded), or ``3``
  (A+B-Downgraded).
- ``confidence``: PurpleAir's 0–100% rolling agreement score between channels.
- ``uptime`` and ``rssi``: Seconds since last sensor reboot and Wi-Fi signal
  strength (dBm), useful for separating hardware drift from power or network
  instability.

Concentration-Dependent QA/QC Thresholds
========================================

A naive percentage-difference check fails at low ambient concentrations. For
example, if Channel A reads ``1.0 ug/m3`` and Channel B reads ``2.0 ug/m3``,
the relative percent difference (RPD) is 66.7%, even though both lasers are
within normal optical noise limits.

Following US EPA (Barkjohn et al.) and community air-quality QA/QC conventions,
a hybrid agreement rule evaluates both absolute and relative differences:

1. **Low-Concentration Regime** (Mean PM2.5 <= 25 ug/m3):

   - Flag a channel mismatch only if the absolute difference
     ``|A - B| > 5.0 ug/m3``.

2. **Elevated-Concentration Regime** (Mean PM2.5 > 25 ug/m3):

   - Flag a channel mismatch if the Relative Percent Difference exceeds 20%
     (or 70% for coarse wildfire screening):
     ``RPD = |A - B| / ((A + B) / 2) * 100``.

3. **Flagged or Stalled Hardware**:

   - Flag any monitor where ``channel_flags != 0`` or ``confidence < 80``.

Building the Fleet Health Auditor with purpleair_api
====================================================

Using ``PurpleAirReadAPI.request_members_data()`` (or
``request_sensor_data()`` for individual stations), we can audit an entire
monitored sensor group in a single API transaction and handle
``PurpleAirAPIError`` cleanly:

.. code-block:: python

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

    def evaluate_channel_agreement(
        pm_a: float, pm_b: float
    ) -> Dict[str, Any]:
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

    def audit_sensor_group(
        read_key: str, group_id: int
    ) -> List[Dict[str, Any]]:
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
                findings.append({
                    "name": name,
                    "status": "DEGRADED",
                    "reason": "Missing dual-channel readings",
                })
                continue

            qa = evaluate_channel_agreement(float(pm_a), float(pm_b))
            flag_label = CHANNEL_FLAG_LABELS.get(flag, f"Flag-{flag}")

            if flag != 0 or conf < 80 or not qa["passed"]:
                findings.append({
                    "name": name,
                    "status": "ALERT",
                    "flag": flag_label,
                    "confidence": conf,
                    "pm_a": pm_a,
                    "pm_b": pm_b,
                    "rpd_pct": qa["rpd_pct"],
                })

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

📥 `Download this script: audit_sensor_group.py <https://raw.githubusercontent.com/carlkidcrypto/carlkidcrypto.github.io/main/example_scripts/purpleair-api-sensor-health-channel-auditing/audit_sensor_group.py>`_

Field Maintenance & Diagnostics Checklist
=========================================

When an automated audit flags a station in your fleet:

1. **Inspect ``channel_flags`` and ``confidence`` History**:

   - A sudden drop in ``confidence`` alongside one channel spiking above
     ``500 ug/m3`` typically indicates an insect or debris inside that laser
     housing.

2. **Blow Out Optical Chambers Gently**:

   - Use clean, dry compressed air (never liquids or solvents) on the underside
     fan intakes to clear dust or cobwebs from the Plantower PMS5003 sensors.

3. **Check ``rssi`` and ``uptime``**:

   - Frequent reboots (low ``uptime``) paired with ``rssi < -80 dBm`` point to
     marginal USB power supplies or weak Wi-Fi coverage rather than laser
     failure.

Summary & What's Next
=====================

Automated dual-channel QA/QC auditing with `purpleair_api
<https://github.com/carlkidcrypto/purpleair_api>`_ catches optical drift and
hardware degradation early, keeping downstream dashboards and scientific
datasets trustworthy.

In our next blog post, we will rotate to `purpleair_data_logger
<https://github.com/carlkidcrypto/purpleair_data_logger>`_, exploring automated
data backfilling and gap recovery for TimescaleDB and SQLite telemetry
pipelines.

----

.. warning::

   AI-generated content may contain misinformation or mistakes. A human does
   review this, but we are only human.
