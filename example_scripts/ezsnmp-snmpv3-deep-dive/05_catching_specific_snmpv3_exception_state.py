#!/usr/bin/env python3
"""Example script for: Mastering SNMPv3 with ezsnmp: USM, AuthPriv, and EngineID Tips
Source: https://carlkidcrypto.github.io/blog/ezsnmp-snmpv3-deep-dive.html
"""

from ezsnmp import Session
from ezsnmp.exceptions import ConnectionError, GenericError, TimeoutError

try:
    with Session(
        hostname='192.168.10.5',
        version=3,
        security_level='authPriv',
        security_username='admin',
        auth_protocol='SHA',
        auth_passphrase='SecretPassword123',
        privacy_protocol='AES',
        privacy_passphrase='SecretPassword123',
        timeout=2,
        retries=1,
    ) as session:
        (res,) = session.get('sysDescr.0')
        print(f"System: {res.value}")
except TimeoutError:
    # Note: SNMPv3 agents silently discard packets with invalid credentials
    # (wrong passphrase or unknown user) per RFC 3414, manifesting as a timeout.
    print("Timeout: Check IP reachability, firewall rules, or verify SNMPv3 passphrases.")
except ConnectionError:
    print("Connection failed: Socket setup or network transport failure.")
except GenericError as exc:
    # Catches syntax issues, unsupported security parameters, or MIB errors
    print(f"SNMPv3 operational error: {exc}")
