#!/usr/bin/env python3
"""Example script for: Modern SNMP in Python with ezsnmp: Practical Guide & Migration
Source: https://carlkidcrypto.github.io/blog/ezsnmp-getting-started-guide.html
"""

from ezsnmp import Session

# Initialize a v2c session
session = Session(
    hostname='192.168.1.1',
    community='public',
    version=2,
    timeout=2,
    retries=3
)

# Query standard system description (sysDescr.0)
results = session.get('sysDescr.0')
if results:
    sys_descr = results[0]
    print(f"OID: {sys_descr.oid}")
    print(f"Index: {sys_descr.index}")
    print(f"Value: {sys_descr.value}")
    print(f"Type: {sys_descr.type}")
