#!/usr/bin/env python3
"""Example script for: First-Hop Redundancy Monitoring: VRRP & HSRP with ezsnmp
Source: https://carlkidcrypto.github.io/blog/ezsnmp-vrrp-hsrp-redundancy-monitoring.html
"""

from concurrent.futures import ThreadPoolExecutor
from ezsnmp import Session
from ezsnmp.exceptions import GenericError

VRRP_STATE_MAP = {
    1: "INITIALIZE",
    2: "BACKUP",
    3: "MASTER",
}

def parse_numeric(val, default=0):
    digits = "".join(c for c in str(val) if c.isdigit())
    return int(digits) if digits else default

def extract_if_and_vrid(idx_str: str, oid_str: str) -> tuple[int, int]:
    """Extract local (ifIndex, vrid) from composite index."""
    parts = [int(p) for p in str(idx_str).split(".") if p.isdigit()]
    if len(parts) >= 2:
        return parts[0], parts[1]
    oid_parts = [int(p) for p in str(oid_str).split(".") if p.isdigit()]
    if len(oid_parts) >= 2:
        return oid_parts[-2], oid_parts[-1]
    return 0, 0

def collect_vrrp_state(hostname: str, community: str = "public") -> dict:
    """Collect VRRP group states with full (ifIndex, vrid) composite identity."""
    session = Session(
        hostname=hostname,
        community=community,
        version=2,
        timeout=2,
        retries=1,
        set_max_repeaters_to_num=25,
        print_enums_numerically=True
    )

    try:
        # Bulk-walk VRRP operational columns
        state_vars = session.bulk_walk("vrrpOperState")
        prio_vars = session.bulk_walk("vrrpOperPriority")
        master_vars = session.bulk_walk("vrrpOperMasterIpAddr")

        prio_map = {v.index: parse_numeric(v.value) for v in prio_vars}
        master_map = {v.index: str(v.value).strip() for v in master_vars}

        vrrp_groups = {}
        for v in state_vars:
            idx = v.index
            if_idx, vrid = extract_if_and_vrid(idx, v.oid)
            raw_state = str(v.value).strip()
            if raw_state.isdigit():
                state_code = int(raw_state)
                state_name = VRRP_STATE_MAP.get(state_code, "UNKNOWN")
            else:
                state_name = raw_state.upper()
                state_code = {val: k for k, val in VRRP_STATE_MAP.items()}.get(state_name, 0)

            master_ip = master_map.get(idx, "Unknown")
            group_key = (
                f"vrid_{vrid}_vip_{master_ip}"
                if master_ip not in ("Unknown", "0.0.0.0")
                else f"if_{if_idx}_vrid_{vrid}"
            )

            vrrp_groups[group_key] = {
                "if_index": if_idx,
                "vrid": vrid,
                "state": state_name,
                "state_code": state_code,
                "priority": prio_map.get(idx, 0),
                "master_ip": master_ip,
            }

        return vrrp_groups

    except GenericError as exc:
        print(f"[{hostname}] VRRP query failed: {exc}")
        return {}

def reconcile_fhrp_pair(rtr1_host: str, rtr2_host: str):
    """Cross-reconcile VRRP states across an HA router pair using concurrent polling."""
    with ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(collect_vrrp_state, rtr1_host)
        f2 = executor.submit(collect_vrrp_state, rtr2_host)
        rtr1_groups = f1.result()
        rtr2_groups = f2.result()

    all_keys = set(rtr1_groups.keys()) | set(rtr2_groups.keys())

    print(f"--- FHRP Reconciliation: {rtr1_host} vs {rtr2_host} ---")
    for key in sorted(all_keys):
        g1 = rtr1_groups.get(key, {})
        g2 = rtr2_groups.get(key, {})

        vrid = g1.get("vrid") or g2.get("vrid") or 0
        s1 = g1.get("state", "MISSING")
        s2 = g2.get("state", "MISSING")
        p1 = g1.get("priority", 0)
        p2 = g2.get("priority", 0)

        # Strict health decision: exactly one MASTER and one BACKUP
        alert = False
        status = "HEALTHY"

        if s1 == "MASTER" and s2 == "MASTER":
            status = "CRITICAL_SPLIT_BRAIN_DUAL_MASTER"
            alert = True
        elif s1 != "MASTER" and s2 != "MASTER":
            status = "CRITICAL_NO_ACTIVE_MASTER"
            alert = True
        elif (s1 == "MASTER" and s2 == "BACKUP") or (s1 == "BACKUP" and s2 == "MASTER"):
            status = "HEALTHY"
            alert = False
        else:
            status = f"DEGRADED_STATE_{s1}_{s2}"
            alert = True

        flag = f" [{status}]" if alert else " [OK]"
        print(
            f"  VRID {vrid:>3} ({key}) | "
            f"{rtr1_host}: {s1:<6} (Prio {p1:>3}) | "
            f"{rtr2_host}: {s2:<6} (Prio {p2:>3}){flag}"
        )

if __name__ == "__main__":
    reconcile_fhrp_pair("gw-core01.internal", "gw-core02.internal")
