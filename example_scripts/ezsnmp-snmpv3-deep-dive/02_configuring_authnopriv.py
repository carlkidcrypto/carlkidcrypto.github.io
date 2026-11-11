#!/usr/bin/env python3
"""Example script for: Mastering SNMPv3 with ezsnmp: USM, AuthPriv, and EngineID Tips
Source: https://carlkidcrypto.github.io/blog/ezsnmp-snmpv3-deep-dive.html
"""

from ezsnmp import Session

with Session(
    hostname='10.20.30.2',
    version=3,
    security_level='authNoPriv',
    security_username='monitor_agent',
    auth_protocol='SHA',
    auth_passphrase='StrongIntegrityToken789',
) as session:
    (uptime,) = session.get('sysUpTime.0')
    print(f"System Uptime: {uptime.value}")
