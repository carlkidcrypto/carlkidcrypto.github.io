#!/usr/bin/env python3
"""Example script for: Auditing Spanning Tree (STP/RSTP) Stability with ezsnmp
Source: https://carlkidcrypto.github.io/blog/ezsnmp-stp-rstp-topology-auditing.html
"""

from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Any, Dict, List

from ezsnmp import Session
from ezsnmp.exceptions import ConnectionError, GenericError, TimeoutError

OID_TIME_SINCE_TC = "1.3.6.1.2.1.17.2.3.0"
OID_TOP_CHANGES = "1.3.6.1.2.1.17.2.4.0"
OID_DESIGNATED_ROOT = "1.3.6.1.2.1.17.2.5.0"
OID_ROOT_COST = "1.3.6.1.2.1.17.2.6.0"
OID_ROOT_PORT = "1.3.6.1.2.1.17.2.7.0"

OID_BASE_PORT_IFINDEX = "1.3.6.1.2.1.17.1.4.1.2"
OID_STP_PORT_STATE = "1.3.6.1.2.1.17.2.15.1.3"
OID_STP_FWD_TRANS = "1.3.6.1.2.1.17.2.15.1.10"
OID_IF_DESCR = "1.3.6.1.2.1.2.2.1.2"

STP_STATES = {
    1: "disabled",
    2: "blocking",
    3: "listening",
    4: "learning",
    5: "forwarding",
    6: "broken",
}


def safe_int(val: Any, default: int = 0) -> int:
    digits = "".join(c for c in str(val) if c.isdigit() or c == "-")
    return int(digits) if digits and digits != "-" else default


def decode_bridge_id(raw_val: str) -> str:
    cleaned = raw_val.replace("Hex-STRING:", "").replace(":", " ").strip()
    hex_str = cleaned.replace(" ", "")
    if len(hex_str) == 16:
        raw_bytes = bytes.fromhex(hex_str)
        priority = int.from_bytes(raw_bytes[:2], "big")
        mac = ":".join(f"{b:02x}" for b in raw_bytes[2:])
        return f"{priority}/{mac}"
    return raw_val.strip()


def audit_switch_stp(
    host: str, expected_root_mac: str, community: str = "public"
) -> Dict[str, Any]:
    session = Session(
        hostname=host,
        community=community,
        version=2,
        timeout=2,
        retries=1,
        set_max_repeaters_to_num=25,
        print_enums_numerically=True,
    )

    report: Dict[str, Any] = {"host": host, "alerts": []}

    try:
        # 1. Batch scalar STP lookups in one get() call
        scalars = session.get(
            [
                OID_TIME_SINCE_TC,
                OID_TOP_CHANGES,
                OID_DESIGNATED_ROOT,
                OID_ROOT_COST,
                OID_ROOT_PORT,
            ]
        )

        time_since_tc_cs = safe_int(scalars[0].value)
        top_changes = safe_int(scalars[1].value)
        root_id = decode_bridge_id(scalars[2].value)
        root_cost = safe_int(scalars[3].value)
        root_port = safe_int(scalars[4].value)

        report["root_id"] = root_id
        report["root_cost"] = root_cost
        report["root_port"] = root_port
        report["top_changes"] = top_changes

        if expected_root_mac.lower() not in root_id.lower():
            report["alerts"].append(f"Unexpected STP Root Bridge: {root_id}")

        if time_since_tc_cs < 30000:  # < 300 seconds
            secs = time_since_tc_cs / 100.0
            report["alerts"].append(
                f"Recent topology change {secs:.1f}s ago " f"(total={top_changes})"
            )

        # 2. Map bridge ports to IF-MIB interface names
        if_descrs = {
            v.index: v.value
            for v in session.bulk_walk(OID_IF_DESCR)
            if v.type not in ("NOSUCHOBJECT", "NOSUCHINSTANCE")
        }
        port_to_if = {
            v.index: str(safe_int(v.value))
            for v in session.bulk_walk(OID_BASE_PORT_IFINDEX)
            if v.type not in ("NOSUCHOBJECT", "NOSUCHINSTANCE")
        }

        # 3. Audit per-port states and forward transitions
        port_states = session.bulk_walk(OID_STP_PORT_STATE)
        fwd_trans = {
            v.index: safe_int(v.value) for v in session.bulk_walk(OID_STP_FWD_TRANS)
        }

        blocked_ports: List[str] = []
        for var in port_states:
            if var.type in ("NOSUCHOBJECT", "NOSUCHINSTANCE"):
                continue
            bport = var.index
            state_code = safe_int(var.value)
            state_name = STP_STATES.get(state_code, f"state-{state_code}")
            if_idx = port_to_if.get(bport, bport)
            if_name = if_descrs.get(if_idx, f"port-{bport}")
            transitions = fwd_trans.get(bport, 0)

            if state_code == 6:  # broken
                report["alerts"].append(f"{if_name} STP state BROKEN")
            elif state_code == 2:
                blocked_ports.append(f"{if_name} (trans={transitions})")

        report["blocked_ports"] = blocked_ports

    except (TimeoutError, ConnectionError, GenericError) as err:
        report["alerts"].append(f"SNMP error: {err}")

    return report


def audit_campus_fleet(hosts: List[str], expected_root_mac: str) -> None:
    with ProcessPoolExecutor(max_workers=4) as pool:
        futures = {
            pool.submit(audit_switch_stp, h, expected_root_mac): h for h in hosts
        }
        for fut in as_completed(futures):
            res = fut.result()
            print(
                f"[{res['host']}] Root={res.get('root_id')} "
                f"TCs={res.get('top_changes')}"
            )
            for alert in res["alerts"]:
                print(f"    [!] {alert}")
