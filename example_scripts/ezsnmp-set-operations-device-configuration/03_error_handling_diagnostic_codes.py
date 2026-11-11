#!/usr/bin/env python3
"""Example script for: SNMP Set Operations & Device Configuration with ezsnmp
Source: https://carlkidcrypto.github.io/blog/ezsnmp-set-operations-device-configuration.html
"""

from ezsnmp.exceptions import PacketError

try:
    session.set(['sysContact.0', 's', 'netops@example.com'])
except PacketError as exc:
    print(f"SET rejected by agent: {exc}")
