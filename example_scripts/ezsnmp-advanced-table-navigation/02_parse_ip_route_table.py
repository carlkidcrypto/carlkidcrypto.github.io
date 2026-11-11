#!/usr/bin/env python3
"""Example script for: Navigating Complex SNMP Tables with ezsnmp: Advanced Patterns
Source: https://carlkidcrypto.github.io/blog/ezsnmp-advanced-table-navigation.html
"""

import ipaddress
from ezsnmp import Session

def parse_ip_route_table(hostname: str, community: str):
    session = Session(hostname=hostname, community=community, version=2)

    # Walk ipRouteMask from RFC1213-MIB
    routes = session.bulk_walk("ipRouteMask")
    route_table = []

    for item in routes:
        # oid_index contains the destination IPv4 address
        dest_ip = item.index
        netmask = item.value
        try:
            cidr = f"{dest_ip}/{netmask}"
            network = ipaddress.IPv4Network(cidr, strict=False)
            route_table.append(str(network))
        except ValueError:
            continue

    return route_table
