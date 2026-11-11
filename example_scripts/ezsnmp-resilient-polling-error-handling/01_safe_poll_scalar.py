#!/usr/bin/env python3
"""Example script for: Resilient SNMP Polling with ezsnmp: Timeouts, Retries & Errors
Source: https://carlkidcrypto.github.io/blog/ezsnmp-resilient-polling-error-handling.html
"""

from ezsnmp import Session
from ezsnmp.exceptions import (
    ConnectionError,
    TimeoutError,
    NoSuchInstanceError,
    GenericError,
)

def safe_poll_scalar(host: str, community: str, oid: str):
    session = Session(
        hostname=host,
        community=community,
        version=2,
        timeout=1,
        retries=1
    )

    try:
        results = session.get(oid)
        if not results:
            return None
        var = results[0]
        if var.type in ("NOSUCHOBJECT", "NOSUCHINSTANCE"):
            print(f"[{host}] Metric {oid} is not instantiated on this device.")
            return None
        return var.value

    except TimeoutError:
        # Host did not respond within (timeout * (retries + 1))
        print(f"[{host}] Timeout: Check packet routing and UDP port 161.")
        return None

    except ConnectionError as err:
        # Socket initialization or EngineID handshake failed
        print(f"[{host}] Connection error: {err}")
        return None

    except NoSuchInstanceError:
        # OID is recognized, but specific table index is absent
        print(f"[{host}] Metric {oid} is not instantiated on this device.")
        return None

    except GenericError as err:
        # General SNMP protocol or ASN.1 parsing error
        print(f"[{host}] Unexpected SNMP protocol failure: {err}")
        return None
