#!/usr/bin/env python3
"""Example script for: Mastering SNMPv3 with ezsnmp: USM, AuthPriv, and EngineID Tips
Source: https://carlkidcrypto.github.io/blog/ezsnmp-snmpv3-deep-dive.html
"""

from ezsnmp import Session

# Initialize a secure SNMPv3 authPriv session
with Session(
    hostname='10.20.30.1',
    version=3,
    security_level='authPriv',
    security_username='netadmin',
    auth_protocol='SHA',
    auth_passphrase='AuthSecretPassphrase2026',
    privacy_protocol='AES',
    privacy_passphrase='PrivEncryptionKey2026',
    timeout=2,
    retries=2,
) as session:
    # session.get() returns a tuple of Result objects
    (system_descr,) = session.get('sysDescr.0')
    print(f"Device Description: {system_descr.value}")
