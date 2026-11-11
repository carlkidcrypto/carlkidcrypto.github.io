#!/usr/bin/env python3
"""Example script for: Mastering SNMPv3 with ezsnmp: USM, AuthPriv, and EngineID Tips
Source: https://carlkidcrypto.github.io/blog/ezsnmp-snmpv3-deep-dive.html
"""

from ezsnmp import Session

# Target the 'CUSTOMER-VRF' routing context
with Session(
    hostname='border-gw.company.net',
    version=3,
    security_level='authPriv',
    security_username='noc_user',
    auth_protocol='SHA',
    auth_passphrase='NocAuthPassphrase!',
    privacy_protocol='AES',
    privacy_passphrase='NocPrivPassphrase!',
    context='CUSTOMER-VRF',
) as vrf_session:
    # Retrieve routes with high-performance GETBULK acceleration
    vrf_routes = vrf_session.bulk_walk('ipRouteDest')
    for route in vrf_routes:
        print(f"VRF Route: {route.oid}.{route.index} = {route.value}")
