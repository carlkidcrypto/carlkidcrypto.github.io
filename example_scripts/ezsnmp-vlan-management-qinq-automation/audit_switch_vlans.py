#!/usr/bin/env python3
"""Example script for: Automating VLAN Management & Q-in-Q Tagging with ezsnmp
Source: https://carlkidcrypto.github.io/blog/ezsnmp-vlan-management-qinq-automation.html
"""

from ezsnmp import Session
from ezsnmp.exceptions import GenericError

def parse_hex_or_bytes(val: str | bytes) -> bytes:
    """Convert ezsnmp Hex-STRING representation or raw octets to bytes."""
    if isinstance(val, bytes):
        return val
    cleaned = val.replace(" ", "").replace(":", "").replace("-", "")
    try:
        return bytes.fromhex(cleaned)
    except ValueError:
        return val.encode("latin1")

def decode_port_bitmask(raw_val: str | bytes) -> list[int]:
    """Decode an SNMP PortList (Hex-STRING or octets) into active port numbers."""
    raw_bytes = parse_hex_or_bytes(raw_val)
    active_ports = []
    for byte_idx, byte_val in enumerate(raw_bytes):
        for bit_idx in range(8):
            # Check bits from MSB (0x80) to LSB (0x01)
            if byte_val & (0x80 >> bit_idx):
                port_num = (byte_idx * 8) + bit_idx + 1
                active_ports.append(port_num)
    return active_ports

def audit_switch_vlans(hostname: str, community: str = "public"):
    session = Session(
        hostname=hostname,
        community=community,
        version=2,
        timeout=2,
        retries=1,
        print_hex_strings=True,
        set_max_repeaters_to_num=25
    )

    try:
        # 1. Collect Port Default VLAN IDs (Native VLANs)
        pvid_vars = session.bulk_walk("dot1qPvid")
        pvids = {v.index: v.value for v in pvid_vars}

        # 2. Bulk-walk VLAN Egress and Untagged bitmasks
        egress_vars = session.bulk_walk("dot1qVlanCurrentEgressPorts")
        untagged_vars = session.bulk_walk("dot1qVlanCurrentUntaggedPorts")

        untagged_map = {
            v.index: set(decode_port_bitmask(v.value))
            for v in untagged_vars
        }

        vlan_report = []

        for var in egress_vars:
            # OID format: [time_filter].[vlan_id]
            vlan_id = var.index.split(".")[-1]
            egress_ports = decode_port_bitmask(var.value)
            untagged_ports = untagged_map.get(var.index, set())

            tagged_ports = [
                p for p in egress_ports if p not in untagged_ports
            ]

            vlan_report.append({
                "vlan_id": vlan_id,
                "tagged_ports": tagged_ports,
                "untagged_ports": list(untagged_ports),
            })

        return pvids, vlan_report

    except GenericError as err:
        print(f"[{hostname}] VLAN audit failed: {err}")
        return {}, []

if __name__ == "__main__":
    pvids, vlans = audit_switch_vlans("dist-sw01.internal")

    print("--- Port Native VLANs (PVID) ---")
    for port, pvid in sorted(pvids.items(), key=lambda x: int(x[0])):
        print(f"  Port {port:>2}: Native VLAN {pvid}")

    print("\n--- VLAN Membership Matrix ---")
    for v in vlans:
        tagged = ",".join(map(str, v["tagged_ports"])) or "None"
        untagged = ",".join(map(str, v["untagged_ports"])) or "None"
        print(
            f"  VLAN {v['vlan_id']:>4} | "
            f"Tagged: [{tagged}] | Untagged: [{untagged}]"
        )
