#!/usr/bin/env python3
"""Example script for: SNMP Set Operations & Device Configuration with ezsnmp
Source: https://carlkidcrypto.github.io/blog/ezsnmp-set-operations-device-configuration.html
"""

from ezsnmp import Session
from ezsnmp.exceptions import GenericError

# Note: Use SNMPv3 in production for encrypted write operations
session = Session(
    hostname='switch-core01.local',
    community='private_write',  # Read-write community or SNMPv3 credentials
    version=2,
    timeout=2,
    retries=1
)

try:
    # Update system location using octet string type ('s')
    new_location = "Building-A:Datacenter:Rack-04"
    session.set(['sysLocation.0', 's', new_location])
    print(f"Location updated successfully to: {new_location}")

    # Verify the update via immediate GET
    verified_val = session.get('sysLocation.0')[0].value
    print(f"Verified on device: {verified_val}")

except GenericError as exc:
    print(f"SNMP SET failed: {exc}")
