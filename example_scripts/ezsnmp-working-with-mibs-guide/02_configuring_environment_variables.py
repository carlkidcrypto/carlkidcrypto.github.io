#!/usr/bin/env python3
"""Example script for: Working with MIBs in ezsnmp: OID Translation & Enterprise MIBs
Source: https://carlkidcrypto.github.io/blog/ezsnmp-working-with-mibs-guide.html
"""

import os
from ezsnmp import Session

# Add custom directory to MIB search path
custom_mibs = os.path.expanduser("~/.snmp/mibs")
os.environ["MIBDIRS"] = f"+{custom_mibs}"
os.environ["MIBS"] = "ALL"

session = Session(
    hostname='core-sw01.internal',
    community='secret',
    version=2
)

# Query custom vendor metric by symbol name
cpu_usage = session.get('cpmCPUTotal5minRev.1')[0]
print(f"CPU Utilization (5m): {cpu_usage.value}%")
