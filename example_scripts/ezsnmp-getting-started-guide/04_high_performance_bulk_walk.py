#!/usr/bin/env python3
"""Example script for: Modern SNMP in Python with ezsnmp: Practical Guide & Migration
Source: https://carlkidcrypto.github.io/blog/ezsnmp-getting-started-guide.html
"""

from ezsnmp import Session

with Session(hostname='core-router.local', community='public', version=2) as session:
    # bulk_walk retrieves multiple OID chunks per datagram for high throughput
    route_entries = session.bulk_walk('ipRouteDest')
    for route in route_entries:
        print(f"Route: {route.value}")
