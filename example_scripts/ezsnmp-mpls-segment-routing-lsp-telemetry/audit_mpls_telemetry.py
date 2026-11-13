#!/usr/bin/env python3
"""Example script for: MPLS & Segment Routing LSP Telemetry: Label Switched Path Auditing with ezsnmp
Source: https://carlkidcrypto.github.io/blog/ezsnmp-mpls-segment-routing-lsp-telemetry.html
"""

from ezsnmp import Session
from ezsnmp.exceptions import GenericError

# Standard RFC 3811 / RFC 3812 MIB OIDs
OID_MPLS_XC_OPER_STATUS = "1.3.6.1.2.1.10.166.2.1.10.1.10"
OID_MPLS_XC_ADMIN_STATUS = "1.3.6.1.2.1.10.166.2.1.10.1.9"
OID_MPLS_TUNNEL_NAME = "1.3.6.1.2.1.10.166.3.2.2.1.35"
OID_MPLS_TUNNEL_OPER_STATUS = "1.3.6.1.2.1.10.166.3.2.2.1.5"

XC_STATUS_MAP = {
    "1": "UP",
    "2": "DOWN",
    "3": "TESTING",
    "4": "UNKNOWN",
    "5": "DORMANT",
    "6": "NOT_PRESENT",
    "7": "LOWER_LAYER_DOWN",
}

TUNNEL_STATUS_MAP = {
    "1": "UP",
    "2": "DOWN",
    "3": "TESTING",
    "4": "UNKNOWN",
    "5": "DORMANT",
    "6": "NOT_PRESENT",
    "7": "LOWER_LAYER_DOWN",
}

def audit_mpls_telemetry(host: str, community: str = "public"):
    session = Session(
        hostname=host,
        community=community,
        version=2,
        timeout=3,
        retries=1,
        set_max_repeaters_to_num=25,
    )

    try:
        print(f"[*] Auditing MPLS and SR-TE state on {host}...")

        # 1. Audit MPLS Cross-Connect Forwarding Plane
        xc_oper_vars = session.bulk_walk(OID_MPLS_XC_OPER_STATUS)
        xc_admin_vars = session.bulk_walk(OID_MPLS_XC_ADMIN_STATUS)

        admin_status_dict = {
            var.index: var.value for var in xc_admin_vars
        }

        active_xc_count = 0
        degraded_xc_list = []

        for var in xc_oper_vars:
            index = var.index
            oper_code = var.value
            admin_code = admin_status_dict.get(index, "1")

            oper_desc = XC_STATUS_MAP.get(oper_code, f"CODE_{oper_code}")

            if oper_code == "1":
                active_xc_count += 1
            elif admin_code == "1":  # Admin UP but Oper DOWN
                degraded_xc_list.append((index, oper_desc))

        print(f"[+] Total Active Cross-Connects: {active_xc_count}")
        if degraded_xc_list:
            print(f"[!] Warning: {len(degraded_xc_list)} degraded XCs:")
            for idx, status in degraded_xc_list:
                print(f"    - XC Index {idx}: Operational Status {status}")

        # 2. Audit Traffic Engineering & Segment Routing Tunnels
        tunnel_names = session.bulk_walk(OID_MPLS_TUNNEL_NAME)
        tunnel_status = session.bulk_walk(OID_MPLS_TUNNEL_OPER_STATUS)

        status_dict = {
            var.index: var.value for var in tunnel_status
        }

        print(f"[+] Discovered {len(tunnel_names)} MPLS/SR Tunnels:")
        for var in tunnel_names:
            idx = var.index
            name = var.value
            t_oper = status_dict.get(idx, "4")
            t_desc = TUNNEL_STATUS_MAP.get(t_oper, f"CODE_{t_oper}")
            print(f"    - Tunnel: {name:<24} State: {t_desc}")

    except GenericError as err:
        print(f"[-] SNMP telemetry query failed: {err}")
