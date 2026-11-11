#!/usr/bin/env python3
"""Example script for: Automating Network Topology Discovery: LLDP and CDP with ezsnmp
Source: https://carlkidcrypto.github.io/blog/ezsnmp-network-topology-discovery-lldp-cdp.html
"""

from collections import defaultdict
from ezsnmp import Session
from ezsnmp.exceptions import GenericError

def extract_composite_index(oid: str, index: str) -> str:
    """Extract composite LLDP suffix (time_mark.local_port.rem_idx) from Result."""
    combined = f"{oid}.{index}" if index else oid
    parts = combined.split(".")
    # LLDP remote table indices consist of 3 sub-identifiers: [time_mark].[local_port].[rem_idx]
    return ".".join(parts[-3:]) if len(parts) >= 3 else index

def discover_lldp_topology(hostname: str, community: str = "public"):
    """Extract physical Layer-2 neighbors using ezsnmp bulk_walk."""
    session = Session(
        hostname=hostname,
        community=community,
        version=2,
        timeout=2,
        retries=1,
        set_max_repeaters_to_num=25
    )

    try:
        # 1. Map local port numbers to human-readable interface names using LLDP-MIB
        # lldpLocPortDesc uses the exact local port numbering space as lldpRemTable
        local_ports = {}
        loc_port_vars = session.bulk_walk("lldpLocPortDesc")
        for var in loc_port_vars:
            local_ports[var.index] = var.value

        # 2. Bulk-walk LLDP remote table columns
        remote_sys_vars = session.bulk_walk("lldpRemSysName")
        remote_port_vars = session.bulk_walk("lldpRemPortId")

        # 3. Index remote metrics by full composite index
        remote_systems = {
            extract_composite_index(v.oid, v.index): v.value
            for v in remote_sys_vars
        }
        remote_ports = {
            extract_composite_index(v.oid, v.index): v.value
            for v in remote_port_vars
        }

        adjacencies = []

        for comp_idx, remote_device in remote_systems.items():
            parts = comp_idx.split(".")
            # [time_mark].[local_port_num].[rem_idx]
            local_port_num = parts[1] if len(parts) >= 3 else parts[0]
            local_port_name = local_ports.get(
                local_port_num, f"Port-{local_port_num}"
            )
            remote_port_name = remote_ports.get(comp_idx, "Unknown")

            adjacencies.append({
                "local_device": hostname,
                "local_port": local_port_name,
                "remote_device": remote_device,
                "remote_port": remote_port_name,
            })

        return adjacencies

    except GenericError as exc:
        print(f"[{hostname}] Topology discovery failed: {exc}")
        return []

if __name__ == "__main__":
    links = discover_lldp_topology("core-sw01.internal")
    print(f"Discovered {len(links)} Layer-2 links:")
    for link in links:
        print(
            f"  {link['local_device']}:{link['local_port']} <---> "
            f"{link['remote_device']}:{link['remote_port']}"
        )
