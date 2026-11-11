#!/usr/bin/env python3
"""Example script for: Auditing Enterprise PoE Budgets & Power Delivery with ezsnmp
Source: https://carlkidcrypto.github.io/blog/ezsnmp-enterprise-poe-power-auditing.html
"""

from ezsnmp import Session
from ezsnmp.exceptions import GenericError

DETECTION_MAP = {
    1: "DISABLED",
    2: "SEARCHING",
    3: "DELIVERING_POWER",
    4: "FAULT",
    5: "TEST",
    6: "OTHER_FAULT",
}

PRIORITY_MAP = {1: "CRITICAL", 2: "HIGH", 3: "LOW"}

def parse_numeric(val: str) -> int:
    """Strip non-numeric characters (units like W, mW) and parse integer."""
    digits = "".join(c for c in str(val) if c.isdigit() or c == "-")
    return int(digits) if digits else 0

def extract_port_index(v) -> str:
    """Extract two-component [group].[port] index from index or OID."""
    if "." in v.index:
        return v.index
    parts = [p for p in v.oid.split(".") if p.isdigit()]
    if len(parts) >= 2:
        return f"{parts[-2]}.{parts[-1]}"
    return v.index

def audit_switch_poe(hostname: str, community: str = "public"):
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
        # 1. Query Chassis Total Capacity and Current Consumption (Watts)
        total_power_vars = session.bulk_walk("pethMainPsePower")
        used_power_vars = session.bulk_walk("pethMainPseConsumptionPower")

        total_watts = sum(parse_numeric(v.value) for v in total_power_vars)
        used_watts = sum(parse_numeric(v.value) for v in used_power_vars)
        util_pct = (used_watts / total_watts * 100) if total_watts else 0

        # 2. Collect per-port PoE detection states and priorities
        status_vars = session.bulk_walk("pethPsePortDetectionStatus")
        prio_vars = session.bulk_walk("pethPsePortPowerPriority")

        # Collect vendor real-time consumption measurements
        draw_map = {}
        try:
            draw_vars = session.bulk_walk("cpeExtPsePortPwrConsumption")
            draw_map = {extract_port_index(v): parse_numeric(v.value) for v in draw_vars}
        except GenericError:
            pass

        prio_map = {extract_port_index(v): parse_numeric(v.value) for v in prio_vars}

        active_ports = []
        for v in status_vars:
            idx = extract_port_index(v)
            status_code = parse_numeric(v.value)
            if status_code == 3:  # deliveringPower
                draw_mw = draw_map.get(idx)
                draw_watts = (draw_mw / 1000.0) if draw_mw is not None else None
                prio_code = prio_map.get(idx, 3)

                active_ports.append({
                    "port_index": idx,
                    "status": DETECTION_MAP.get(status_code, "UNKNOWN"),
                    "priority": PRIORITY_MAP.get(prio_code, "LOW"),
                    "watts": draw_watts,
                })

        return {
            "total_watts": total_watts,
            "used_watts": used_watts,
            "util_pct": util_pct,
            "active_ports": active_ports,
        }

    except GenericError as exc:
        print(f"[{hostname}] PoE audit failed: {exc}")
        return None

if __name__ == "__main__":
    report = audit_switch_poe("access-sw01.internal")
    if report:
        used_w = report['used_watts']
        pct = report['util_pct']
        print("--- PoE Chassis Power Budget ---")
        print(f"  Total Capacity : {report['total_watts']} W")
        print(f"  Current Draw   : {used_w} W ({pct:.1f}%)")
        print(f"  Active PoE Ports: {len(report['active_ports'])}\n")

        print("--- Delivering Power Ports (Top Consumers) ---")
        measured_ports = [p for p in report["active_ports"] if p["watts"] is not None]
        top_ports = sorted(
            measured_ports,
            key=lambda x: x["watts"],
            reverse=True
        )[:5]
        for p in top_ports:
            print(
                f"  Port {p['port_index']:<8} | "
                f"Priority: {p['priority']:<8} | "
                f"Draw: {p['watts']:>5.2f} W"
            )
