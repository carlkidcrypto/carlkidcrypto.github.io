#!/usr/bin/env python3
"""Example script for: Modern SNMP in Python with ezsnmp: Practical Guide & Migration
Source: https://carlkidcrypto.github.io/blog/ezsnmp-getting-started-guide.html
"""

from ezsnmp import Session
from ezsnmp.exceptions import (
    ConnectionError,
    TimeoutError,
    NoSuchObjectError,
    GenericError
)

session = Session(
    hostname='10.0.0.15',
    community='public',
    version=2,
    timeout=1,
    retries=1
)

try:
    data = session.get('sysDescr.0')
except TimeoutError:
    print("Device timed out. Verify network reachability and latency.")
except ConnectionError:
    print("Failed to establish SNMP connection or resolve socket address.")
except NoSuchObjectError:
    print("The requested OID does not exist on this agent.")
except GenericError as exc:
    print(f"General SNMP error encountered: {exc}")
