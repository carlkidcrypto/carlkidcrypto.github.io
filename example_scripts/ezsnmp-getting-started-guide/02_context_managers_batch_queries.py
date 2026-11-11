#!/usr/bin/env python3
"""Example script for: Modern SNMP in Python with ezsnmp: Practical Guide & Migration
Source: https://carlkidcrypto.github.io/blog/ezsnmp-getting-started-guide.html
"""

from ezsnmp import Session

with Session(hostname='192.168.1.1', community='public', version=2) as session:
    # Request multiple OIDs in a single network round-trip
    oids = ['sysDescr.0', 'sysUpTime.0', 'sysContact.0']
    results = session.get(oids)

    for item in results:
        print(f"{item.oid}.{item.index} ({item.type}) = {item.value}")
