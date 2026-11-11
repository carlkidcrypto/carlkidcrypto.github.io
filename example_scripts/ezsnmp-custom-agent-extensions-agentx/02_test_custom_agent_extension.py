#!/usr/bin/env python3
"""Example script for: Building Custom SNMP Agent Extensions with Python and ezsnmp
Source: https://carlkidcrypto.github.io/blog/ezsnmp-custom-agent-extensions-agentx.html
"""

from ezsnmp import Session
from ezsnmp.exceptions import GenericError

def test_custom_agent_extension():
    session = Session(
        hostname="localhost",
        community="public",
        version=2,
        timeout=1,
        retries=1
    )

    try:
        # 1. Query individual scalar metrics
        jobs = session.get(".1.3.6.1.4.1.99999.1.1.0")[0]
        status = session.get(".1.3.6.1.4.1.99999.1.3.0")[0]
        print(f"Active Worker Jobs : {jobs.value} ({jobs.type})")
        print(f"Service Health     : {status.value} ({status.type})")

        # 2. Walk the entire custom enterprise branch
        print("\nWalking custom enterprise subtree:")
        tree_vars = session.walk(".1.3.6.1.4.1.99999.1")
        for var in tree_vars:
            print(f"  {var.oid}.{var.index} = {var.value}")

    except GenericError as exc:
        print(f"SNMP validation query failed: {exc}")

if __name__ == "__main__":
    test_custom_agent_extension()
