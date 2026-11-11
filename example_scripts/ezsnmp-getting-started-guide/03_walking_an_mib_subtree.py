#!/usr/bin/env python3
"""Example script for: Modern SNMP in Python with ezsnmp: Practical Guide & Migration
Source: https://carlkidcrypto.github.io/blog/ezsnmp-getting-started-guide.html
"""

from ezsnmp import Session

with Session(hostname='switch-01.local', community='public', version=2) as session:
    # Walk interface descriptions
    interfaces = session.walk('ifDescr')
    for iface in interfaces:
        print(f"Interface {iface.index}: {iface.value}")
