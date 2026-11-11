#!/usr/bin/env python3
"""Example script for: Mastering SNMPv3 with ezsnmp: USM, AuthPriv, and EngineID Tips
Source: https://carlkidcrypto.github.io/blog/ezsnmp-snmpv3-deep-dive.html
"""

from ezsnmp import Session

# Hexadecimal authoritative engine identifier
ENGINE_ID = '0x80001f8880e64c398905b6306500000000'

with Session(
    hostname='pdu-remote.lab.net',
    version=3,
    security_level='authPriv',
    security_username='pdu_operator',
    auth_protocol='SHA',
    auth_passphrase='OperatorAuthToken!',
    privacy_protocol='AES',
    privacy_passphrase='OperatorPrivToken!',
    security_engine_id=ENGINE_ID,
) as session:
    (contact,) = session.get('sysContact.0')
    print(f"Contact Info: {contact.value}")
