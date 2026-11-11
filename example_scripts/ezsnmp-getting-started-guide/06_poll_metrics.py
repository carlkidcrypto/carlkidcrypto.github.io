#!/usr/bin/env python3
"""Example script for: Modern SNMP in Python with ezsnmp: Practical Guide & Migration
Source: https://carlkidcrypto.github.io/blog/ezsnmp-getting-started-guide.html
"""

# Recommended: Instantiate once and reuse across polling loops
session = Session(
    hostname='pdu-01.local',
    community='public',
    version=2
)

def poll_metrics():
    return session.get(['sysUpTime.0', 'sysDescr.0'])
