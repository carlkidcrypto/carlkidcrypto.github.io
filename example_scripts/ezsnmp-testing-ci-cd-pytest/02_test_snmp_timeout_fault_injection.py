#!/usr/bin/env python3
"""Example script for: Testing SNMP Automation Pipelines with pytest and ezsnmp
Source: https://carlkidcrypto.github.io/blog/ezsnmp-testing-ci-cd-pytest.html
"""

import pytest
from ezsnmp import Session
from ezsnmp.exceptions import TimeoutError

def test_snmp_get_scalar(snmp_daemon):
    """Verify successful retrieval of scalar system metadata."""
    session = Session(
        hostname=f"127.0.0.1:{snmp_daemon['port']}",
        community=snmp_daemon["community"],
        version=2,
        timeout=1,
        retries=1
    )

    sys_location = session.get("sysLocation.0")[0]
    assert sys_location.value == "TestLab-Rack42"
    assert sys_location.type == "STRING"

def test_snmp_batch_get(snmp_daemon):
    """Verify multi-OID batch queries execute cleanly."""
    session = Session(
        hostname=f"127.0.0.1:{snmp_daemon['port']}",
        community=snmp_daemon["community"],
        version=2
    )

    results = session.get(["sysLocation.0", "sysContact.0", "sysName.0"])
    # Strip potential MIB module qualifiers (e.g. SNMPv2-MIB::sysLocation)
    val_map = {v.oid.split("::")[-1]: v.value for v in results}

    assert val_map["sysLocation"] == "TestLab-Rack42"
    assert val_map["sysContact"] == "ci-runner@example.internal"
    assert val_map["sysName"] == "switch-test-01"

def test_snmp_timeout_fault_injection():
    """Verify client raises TimeoutError on silent drops."""
    # Query an unreachable blackhole address
    session = Session(
        hostname="192.0.2.1:161",  # RFC 5737 TEST-NET address
        community="public",
        version=2,
        timeout=1,
        retries=1
    )

    with pytest.raises(TimeoutError):
        session.get("sysDescr.0")
