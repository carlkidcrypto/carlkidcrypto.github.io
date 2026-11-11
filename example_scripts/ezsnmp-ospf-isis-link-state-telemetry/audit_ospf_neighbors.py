#!/usr/bin/env python3
"""Example script for: OSPF & IS-IS Link-State Telemetry: Neighbor Auditing in ezsnmp
Source: https://carlkidcrypto.github.io/blog/ezsnmp-ospf-isis-link-state-telemetry.html
"""

from ezsnmp import Session
from ezsnmp.exceptions import GenericError

OSPF_STATE_MAP = {
    1: "DOWN",
    2: "ATTEMPT",
    3: "INIT",
    4: "2-WAY",
    5: "EXSTART",
    6: "EXCHANGE",
    7: "LOADING",
    8: "FULL",
}

def parse_numeric(val, default=0):
    digits = "".join(c for c in str(val) if c.isdigit())
    return int(digits) if digits else default

def extract_nbr_ip(index_str: str, oid_str: str) -> str:
    parts = [p for p in index_str.split(".") if p.isdigit()]
    if len(parts) >= 4:
        return ".".join(parts[:4])
    oid_parts = [p for p in oid_str.split(".") if p.isdigit()]
    if len(oid_parts) >= 5:
        return ".".join(oid_parts[-5:-1])
    return index_str or "Unknown"

def audit_ospf_neighbors(hostname: str, community: str = "public"):
    """Audit OSPF neighbor states, flap events, and LSA queue depth."""
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
        # 1. Bulk-walk OSPF neighbor table columns
        state_vars = session.bulk_walk("ospfNbrState")
        rtr_vars = session.bulk_walk("ospfNbrRtrId")
        event_vars = session.bulk_walk("ospfNbrEvents")
        retrans_vars = session.bulk_walk("ospfNbrLsRetransQLen")

        rtr_map = {v.index: v.value for v in rtr_vars}
        event_map = {v.index: parse_numeric(v.value) for v in event_vars}
        retrans_map = {v.index: parse_numeric(v.value) for v in retrans_vars}

        neighbors = []

        for var in state_vars:
            # OID index format: [neighbor_ip].[address_less_index]
            idx = var.index
            nbr_ip_str = extract_nbr_ip(idx, var.oid)

            raw_state = str(var.value).strip()
            if raw_state.isdigit():
                state_code = int(raw_state)
                state_name = OSPF_STATE_MAP.get(
                    state_code, f"CODE_{state_code}"
                )
            else:
                state_name = raw_state.upper()
                state_code = {v: k for k, v in OSPF_STATE_MAP.items()}.get(state_name, 0)

            rtr_id = rtr_map.get(idx, "Unknown")
            events = event_map.get(idx, 0)
            retrans_len = retrans_map.get(idx, 0)

            # An operational point-to-point adjacency must be FULL (8)
            is_stuck = state_code in (5, 6, 7)  # ExStart/Exchange/Loading
            is_down = state_code == 1
            has_retrans = retrans_len > 0

            status = "OK"
            if is_down:
                status = "DOWN"
            elif is_stuck:
                status = "STUCK_MTU_MISMATCH"
            elif has_retrans:
                status = "LSA_PACKET_LOSS"

            neighbors.append({
                "neighbor_ip": nbr_ip_str,
                "router_id": rtr_id,
                "state": state_name,
                "flaps": events,
                "retrans_queue": retrans_len,
                "status": status,
                "alert": is_down or is_stuck or has_retrans
            })

        return neighbors

    except GenericError as exc:
        print(f"[{hostname}] OSPF audit failed: {exc}")
        return []

if __name__ == "__main__":
    results = audit_ospf_neighbors("core-rtr01.internal")
    print("--- OSPF Neighbor Telemetry Report ---")
    for n in results:
        flag = f" [{n['status']}]" if n["alert"] else ""
        print(
            f"  Neighbor {n['neighbor_ip']:<15} "
            f"(RID: {n['router_id']:<15}) | "
            f"State: {n['state']:<8} | Flaps: {n['flaps']:>3} | "
            f"RetransQ: {n['retrans_queue']:>2}{flag}"
        )
