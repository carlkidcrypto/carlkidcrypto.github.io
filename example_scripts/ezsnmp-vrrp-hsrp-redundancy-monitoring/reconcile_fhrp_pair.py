#!/usr/bin/env python3
"""Example script for: First-Hop Redundancy Monitoring: VRRP & HSRP with ezsnmp
Source: https://carlkidcrypto.github.io/blog/ezsnmp-vrrp-hsrp-redundancy-monitoring.html
"""

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

def extract_vrid(index_str: str, oid_str: str) -> str:
    parts = [p for p in index_str.split(".") if p.isdigit()]
    if parts:
        return parts[-1]
    oid_parts = [p for p in oid_str.split(".") if p.isdigit()]
    if oid_parts:
        return oid_parts[-1]
    return index_str or "0"

def collect_vrrp_state(hostname: str, community: str = "public") -> dict:
    """Query VRRP operational parameters on a target router."""
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
        master_map = {v.index: v.value for v in master_vars}

        vrid_data = {}
        for v in state_vars:
            # OID index format: [ifIndex].[vrid]
            idx = v.index
            raw_state = str(v.value).strip()
            if raw_state.isdigit():
                state_code = int(raw_state)
                state_name = VRRP_STATE_MAP.get(state_code, "UNKNOWN")
            else:
                state_name = raw_state.upper()
                state_code = {val: k for k, val in VRRP_STATE_MAP.items()}.get(state_name, 0)

            vrid = extract_vrid(idx, v.oid)

            vrid_data[vrid] = {
                "vrid": vrid,
                "state": state_name,
                "state_code": state_code,
                "priority": prio_map.get(idx, 0),
                "master_ip": master_map.get(idx, "Unknown"),
            }

        return vrid_data

    except GenericError as exc:
        print(f"[{hostname}] VRRP query failed: {exc}")
        return {}

def reconcile_fhrp_pair(rtr1_host: str, rtr2_host: str):
    """Cross-reconcile VRRP states across an HA router pair."""
    rtr1_vrids = collect_vrrp_state(rtr1_host)
    rtr2_vrids = collect_vrrp_state(rtr2_host)

    all_vrids = set(rtr1_vrids.keys()) | set(rtr2_vrids.keys())

    print(f"--- FHRP Reconciliation: {rtr1_host} vs {rtr2_host} ---")
    for vrid in sorted(all_vrids, key=lambda x: parse_numeric(x)):
        g1 = rtr1_vrids.get(vrid, {})
        g2 = rtr2_vrids.get(vrid, {})

        s1 = g1.get("state", "MISSING")
        s2 = g2.get("state", "MISSING")
        p1 = g1.get("priority", 0)
        p2 = g2.get("priority", 0)

        # Detect split-brain (both master) or no-master (both backup/init)
        alert = False
        status = "HEALTHY"

        if s1 == "MASTER" and s2 == "MASTER":
            status = "CRITICAL_SPLIT_BRAIN_DUAL_MASTER"
            alert = True
        elif s1 != "MASTER" and s2 != "MASTER":
            status = "CRITICAL_NO_ACTIVE_MASTER"
            alert = True

        flag = f" [{status}]" if alert else " [OK]"
        print(
            f"  VRID {vrid:>3} | "
            f"{rtr1_host}: {s1:<6} (Prio {p1:>3}) | "
            f"{rtr2_host}: {s2:<6} (Prio {p2:>3}){flag}"
        )

if __name__ == "__main__":
    reconcile_fhrp_pair("gw-core01.internal", "gw-core02.internal")
