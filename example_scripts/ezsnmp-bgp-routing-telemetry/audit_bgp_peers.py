#!/usr/bin/env python3
"""Example script for: BGP Routing Telemetry: Peering States & Prefix Counts in ezsnmp
Source: https://carlkidcrypto.github.io/blog/ezsnmp-bgp-routing-telemetry.html
"""

from ezsnmp import Session
from ezsnmp.exceptions import GenericError

BGP_STATE_MAP = {
    1: "IDLE",
    2: "CONNECT",
    3: "ACTIVE",
    4: "OPENSENT",
    5: "OPENCONFIRM",
    6: "ESTABLISHED",
}

def extract_peer_ip(var) -> str:
    """Extract the 4-octet IPv4 peer address from index or full OID."""
    idx_parts = var.index.split(".")
    if len(idx_parts) >= 4:
        return ".".join(idx_parts[:4])
    oid_parts = [p for p in var.oid.split(".") if p.isdigit()]
    if len(oid_parts) >= 4:
        return ".".join(oid_parts[-4:])
    return var.index

def audit_bgp_peers(hostname: str, community: str = "public"):
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
        # 1. Bulk-walk standard BGP4-MIB peer table columns
        state_vars = session.bulk_walk("bgpPeerState")
        as_vars = session.bulk_walk("bgpPeerRemoteAs")
        uptime_vars = session.bulk_walk("bgpPeerFsmEstablishedTime")

        # Reconstruct 4-octet peer IP suffix
        as_map = {extract_peer_ip(v): v.value for v in as_vars}
        uptime_map = {extract_peer_ip(v): int(v.value) for v in uptime_vars}

        # 2. Collect accepted prefix counts (CISCO-BGP4-MIB / Vendor MIBs)
        # Index format: [peer_ip (4 octets)].[afi].[safi]
        prefix_map = {}
        try:
            prefix_vars = session.bulk_walk("cbgpPeerAcceptedPrefixes")
            for v in prefix_vars:
                parts = [p for p in v.index.split(".") if p]
                if len(parts) < 4:
                    parts = [p for p in v.oid.split(".") if p.isdigit()]
                if len(parts) >= 6:
                    peer_ip = ".".join(parts[-6:-2])
                    afi, safi = parts[-2], parts[-1]
                    family_key = f"{peer_ip}/AFI{afi}-SAFI{safi}"
                    prefix_map[peer_ip] = int(v.value)
                    prefix_map[family_key] = int(v.value)
                elif len(parts) >= 4:
                    peer_ip = ".".join(parts[-4:])
                    prefix_map[peer_ip] = int(v.value)
        except GenericError:
            # Gracefully handle non-Cisco devices without prefix extension MIB
            pass

        peer_report = []

        for var in state_vars:
            peer_ip = extract_peer_ip(var)
            state_code = int(var.value)
            state_name = BGP_STATE_MAP.get(state_code, "UNKNOWN")
            remote_as = as_map.get(peer_ip, "Unknown")
            established_sec = uptime_map.get(peer_ip, 0)
            accepted_prefixes = prefix_map.get(peer_ip, 0)

            # Flag down or recently flapped sessions (< 5 minutes)
            is_down = state_code != 6
            is_flapping = state_code == 6 and established_sec < 300

            if is_down:
                reason = "DOWN"
            elif is_flapping:
                reason = "FLAPPING"
            else:
                reason = "OK"

            peer_report.append({
                "peer_ip": peer_ip,
                "remote_as": remote_as,
                "state": state_name,
                "uptime_sec": established_sec,
                "prefixes": accepted_prefixes,
                "alert": is_down or is_flapping,
                "reason": reason
            })

        return peer_report

    except GenericError as exc:
        print(f"[{hostname}] BGP audit failed: {exc}")
        return []

if __name__ == "__main__":
    peers = audit_bgp_peers("edge-gw01.internal")
    print("--- BGP Peering Telemetry Report ---")
    for p in peers:
        status_flag = f" [{p['reason']}]" if p["alert"] else ""
        print(
            f"  Peer {p['peer_ip']:<15} (AS{p['remote_as']:<5}) | "
            f"State: {p['state']:<11} | Uptime: {p['uptime_sec']:>6}s | "
            f"Prefixes: {p['prefixes']:>5}{status_flag}"
        )
