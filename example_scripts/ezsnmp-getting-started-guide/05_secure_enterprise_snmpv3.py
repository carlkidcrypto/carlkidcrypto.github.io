#!/usr/bin/env python3
"""Example script for: Modern SNMP in Python with ezsnmp: Practical Guide & Migration
Source: https://carlkidcrypto.github.io/blog/ezsnmp-getting-started-guide.html
"""

from ezsnmp import Session

v3_session = Session(
    hostname='secure-switch.corp.internal',
    version=3,
    security_level='authPriv',
    security_username='snmp_admin',
    auth_protocol='SHA',
    auth_passphrase='StrongAuthPassphrase123',
    privacy_protocol='AES',
    privacy_passphrase='StrongPrivPassphrase456'
)

results = v3_session.get('sysUpTime.0')
if results:
    print(f"Secure Uptime: {results[0].value}")
