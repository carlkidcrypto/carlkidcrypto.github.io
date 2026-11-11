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

def extract_composite_index(var) -> str:
    """Extract the complete table row index suffix ([neighbor_ip].[address_less_index])."""
    oid_parts = [p for p in str(var.oid).split(".") if p.strip()]
    idx_parts = [p for p in str(var.index).split(".") if p.strip()]
    if len(idx_parts) >= 5:
        return ".".join(idx_parts[:5])
    combined = oid_parts + idx_parts
    numeric = [p for p in combined if p.isdigit()]
    if len(numeric) >= 5:
        return ".".join(numeric[-5:])
    return var.index or "0"

def extract_nbr_ip_from_key(key: str) -> str:
    parts = [p for p in key.split(".") if p.isdigit()]
    if len(parts) >= 4:
        return ".".join(parts[:4])
    return key

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

        # Map by composite 5-part index to avoid collisions on address-less indices
        rtr_map = {extract_composite_index(v): v.value for v in rtr_vars}
        event_map = {extract_composite_index(v): parse_numeric(v.value) for v in event_vars}
        retrans_map = {extract_composite_index(v): parse_numeric(v.value) for v in retrans_vars}

        neighbors = []

        for var in state_vars:
            idx = extract_composite_index(var)
            nbr_ip_str = extract_nbr_ip_from_key(idx)

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

            # Evaluate operational state vs abnormal/unidirectional or transitional conditions
            is_down = state_code == 1
            is_init_or_attempt = state_code in (2, 3)
            is_transitional = state_code in (5, 6, 7)
            is_2way = state_code == 4
            is_full = state_code == 8
            has_retrans = retrans_len > 0

            status = "OPERATIONAL"
            alert = False
            if is_down:
                status = "DOWN"
                alert = True
            elif is_init_or_attempt:
                status = "INIT_UNIDIRECTIONAL_OR_ATTEMPT"
                alert = True
            elif is_transitional:
                # Single snapshots may capture normal transitions; qualify as transitional/stuck
                status = "TRANSITIONAL_OR_STUCK"
                alert = True
            elif has_retrans:
                # Retransmission backlog: persistent queues indicate MTU mismatch or packet loss
                status = "RETRANS_QUEUE_BACKLOG"
                alert = True
            elif is_2way:
                status = "2-WAY_DROTHER"
                alert = False
            elif is_full:
                status = "FULL"
                alert = False

            neighbors.append({
                "neighbor_ip": nbr_ip_str,
                "router_id": rtr_id,
                "state": state_name,
                "flaps": events,
                "retrans_queue": retrans_len,
                "status": status,
                "alert": alert
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
