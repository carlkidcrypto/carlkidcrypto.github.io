#!/usr/bin/env python3
"""Example script for: Traffic Flow Auditing: Monitoring NetFlow & IPFIX with ezsnmp
Source: https://carlkidcrypto.github.io/blog/ezsnmp-traffic-flow-netflow-ipfix-auditing.html
"""

from ezsnmp import Session
from ezsnmp.exceptions import GenericError

def parse_numeric(val: str) -> int:
    """Extract integer digits from SNMP string or integer responses."""
    digits = "".join(c for c in str(val) if c.isdigit())
    if not digits:
        return 0
    result = int(digits)
    return -result if str(val).strip().startswith("-") else result

def audit_flow_exporter(hostname: str, community: str = "public"):
    session = Session(
        hostname=hostname,
        community=community,
        version=2,
        timeout=2,
        retries=1
    )

    try:
        # 1. Query exported and dropped flow packets from CISCO-NETFLOW-MIB scalars
        try:
            cisco_scalars = session.get(["cnfESPktsExported.0", "cnfESPktsDropped.0"])
            exported_pkts = parse_numeric(cisco_scalars[0].value)
            dropped_pkts = parse_numeric(cisco_scalars[1].value)
        except GenericError:
            exported_pkts = 0
            dropped_pkts = 0

        # Collect active cache flow count
        try:
            active_vars = session.bulk_walk("cnfCIActiveFlows")
            active_flows = sum(parse_numeric(v.value) for v in active_vars)
        except GenericError:
            active_flows = 0

        total_pkts = exported_pkts + dropped_pkts
        drop_ratio = (
            (dropped_pkts / total_pkts * 100.0) if total_pkts else 0.0
        )

        # 2. Check for standard IPFIX transport session discarded messages
        discarded_messages = 0
        try:
            ipfix_drops = session.bulk_walk("ipfixTransportSessionDiscardedMessages")
            discarded_messages = sum(parse_numeric(v.value) for v in ipfix_drops)
        except GenericError:
            pass

        alert = drop_ratio > 0.05 or discarded_messages > 0

        return {
            "hostname": hostname,
            "exported_packets": exported_pkts,
            "dropped_packets": dropped_pkts,
            "drop_ratio_pct": drop_ratio,
            "active_flows": active_flows,
            "discarded_messages": discarded_messages,
            "alert": alert,
        }

    except GenericError as exc:
        print(f"[{hostname}] Flow audit failed: {exc}")
        return None

if __name__ == "__main__":
    result = audit_flow_exporter("edge-router01.internal")
    if result:
        print("--- Flow Exporter Telemetry Report ---")
        print(f"  Target Router       : {result['hostname']}")
        print(f"  Active Flows in RAM : {result['active_flows']:,}")
        print(f"  Exported Packets    : {result['exported_packets']:,}")
        print(f"  Dropped Packets     : {result['dropped_packets']:,}")
        print(f"  Drop Ratio          : {result['drop_ratio_pct']:.4f}%")
        if result["alert"]:
            print("  [ALERT] Elevated flow buffer drops detected!")
        else:
            print(
                f"  [STATUS] Exporter drop ratio within acceptable threshold "
                f"({result['drop_ratio_pct']:.4f}% <= 0.05%)."
            )
