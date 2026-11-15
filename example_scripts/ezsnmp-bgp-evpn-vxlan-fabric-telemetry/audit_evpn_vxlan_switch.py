#!/usr/bin/env python3
"""Example script for: Auditing BGP EVPN and VXLAN Overlay Fabric Health with ezsnmp
Source: https://carlkidcrypto.github.io/blog/ezsnmp-bgp-evpn-vxlan-fabric-telemetry.html
"""

from ezsnmp import Session
from ezsnmp.exceptions import GenericError

# Standard RFC MIB OIDs
OID_BGP_PEER_STATE = "1.3.6.1.2.1.15.3.1.2"
OID_BGP_PEER_ADMIN_STATUS = "1.3.6.1.2.1.15.3.1.3"
OID_BGP_PEER_REMOTE_AS = "1.3.6.1.2.1.15.3.1.9"

OID_IF_DESCR = "1.3.6.1.2.1.2.2.1.2"
OID_IF_OPER_STATUS = "1.3.6.1.2.1.2.2.1.8"

BGP_STATE_MAP = {
    "1": "IDLE",
    "2": "CONNECT",
    "3": "ACTIVE",
    "4": "OPENSENT",
    "5": "OPENCONFIRM",
    "6": "ESTABLISHED",
}

OPER_STATUS_MAP = {
    "1": "UP",
    "2": "DOWN",
    "3": "TESTING",
    "4": "UNKNOWN",
    "5": "DORMANT",
    "6": "NOT_PRESENT",
    "7": "LOWER_LAYER_DOWN",
}


def audit_evpn_vxlan_switch(host: str, community: str = "public"):
    session = Session(
        hostname=host,
        community=community,
        version=2,
        timeout=3,
        retries=1,
        set_max_repeaters_to_num=25,
        print_enums_numerically=True,
    )

    try:
        print(f"[*] Auditing EVPN-VXLAN fabric state on {host}...")

        # 1. Audit BGP EVPN Control-Plane Peers
        peer_states = session.bulk_walk(OID_BGP_PEER_STATE)
        peer_admins = session.bulk_walk(OID_BGP_PEER_ADMIN_STATUS)
        peer_remote_as = session.bulk_walk(OID_BGP_PEER_REMOTE_AS)

        admin_dict = {v.index: v.value for v in peer_admins}
        as_dict = {v.index: v.value for v in peer_remote_as}

        established_peers = 0
        degraded_peers = []

        for var in peer_states:
            peer_ip = var.index
            state_code = var.value
            admin_code = admin_dict.get(peer_ip, "2")
            rem_as = as_dict.get(peer_ip, "UNKNOWN")

            state_name = BGP_STATE_MAP.get(state_code, f"CODE_{state_code}")

            if state_code == "6":
                established_peers += 1
            elif admin_code == "2":  # Admin Start but not Established
                degraded_peers.append((peer_ip, rem_as, state_name))

        print(f"[+] Established BGP EVPN Peers: {established_peers}")
        if degraded_peers:
            print(f"[!] Warning: {len(degraded_peers)} degraded BGP peers:")
            for p_ip, r_as, state in degraded_peers:
                print(f"    - Peer {p_ip} (AS {r_as}): State = {state}")

        # 2. Audit VXLAN Tunnel Interface (NVE / Vxlan1)
        if_descrs = session.bulk_walk(OID_IF_DESCR)
        if_opers = session.bulk_walk(OID_IF_OPER_STATUS)

        oper_dict = {v.index: v.value for v in if_opers}

        vxlan_interfaces_found = 0
        for var in if_descrs:
            name = var.value.lower()
            if "vxlan" in name or "nve" in name:
                vxlan_interfaces_found += 1
                oper_code = oper_dict.get(var.index, "4")
                oper_name = OPER_STATUS_MAP.get(oper_code, f"CODE_{oper_code}")
                print(
                    f"[+] VXLAN Interface '{var.value}' "
                    f"(Index {var.index}): Status = {oper_name}"
                )

        if vxlan_interfaces_found == 0:
            print("[!] No active VXLAN/NVE interfaces found on device.")

    except GenericError as err:
        print(f"[-] SNMP telemetry query failed: {err}")


if __name__ == "__main__":
    audit_evpn_vxlan_switch("127.0.0.1")
