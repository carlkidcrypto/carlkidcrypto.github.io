#!/usr/bin/env python3
"""Example script for: Modernizing SNMP Security: SNMPv3 over TLS and DTLS with ezsnmp
Source: https://carlkidcrypto.github.io/blog/ezsnmp-snmpv3-tls-dtls-security.html
"""

from ezsnmp import Session
from ezsnmp.exceptions import GenericError

def poll_secure_switch_tls(hostname: str):
    """Query metrics over TLS (TCP port 10161) using X.509 mTLS."""
    # Target URI specifies the tlstcp transport domain
    target_endpoint = f"tlstcp:{hostname}:10161"

    session = Session(
        hostname=target_endpoint,
        version=3,
        security_level="authPriv",
        security_username="noc_automation",
        timeout=3,
        retries=1
    )

    try:
        # Poll system metrics over encrypted TCP stream
        sys_descr = session.get("sysDescr.0")[0]
        uptime = session.get("sysUpTime.0")[0]
        print(f"[{hostname}] TLS Connection Established!")
        print(f"  Description: {sys_descr.value}")
        print(f"  Uptime     : {uptime.value}")

    except GenericError as exc:
        print(f"[{hostname}] TLS Polling Failed: {exc}")

def poll_secure_switch_dtls(hostname: str):
    """Query metrics over DTLS (UDP port 10161) for low latency."""
    target_endpoint = f"dtlsudp:{hostname}:10161"

    session = Session(
        hostname=target_endpoint,
        version=3,
        security_level="authPriv",
        security_username="noc_automation",
        timeout=2,
        retries=2,
        set_max_repeaters_to_num=25
    )

    try:
        results = session.bulk_walk("ifDescr")
        print(
            f"[{hostname}] DTLS Walk Retrieved {len(results)} Interfaces."
        )
    except GenericError as exc:
        print(f"[{hostname}] DTLS Polling Failed: {exc}")

if __name__ == "__main__":
    poll_secure_switch_tls("core-sw01.internal")
    poll_secure_switch_dtls("core-sw01.internal")
