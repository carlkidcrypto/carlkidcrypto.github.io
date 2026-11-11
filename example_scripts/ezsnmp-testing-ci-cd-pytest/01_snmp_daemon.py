#!/usr/bin/env python3
"""Example script for: Testing SNMP Automation Pipelines with pytest and ezsnmp
Source: https://carlkidcrypto.github.io/blog/ezsnmp-testing-ci-cd-pytest.html
"""

import os
import subprocess
import tempfile
import time
import pytest
from ezsnmp import Session

TEST_PORT = 11161
COMMUNITY = "test_community"

@pytest.fixture(scope="session")
def snmp_daemon():
    """Launch a sandboxed local snmpd daemon for integration testing."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        conf_path = os.path.join(tmp_dir, "snmpd.conf")
        pid_path = os.path.join(tmp_dir, "snmpd.pid")

        # Minimal test configuration with custom system metadata
        with open(conf_path, "w") as f:
            f.write(f"""
            rocommunity {COMMUNITY} 127.0.0.1
            sysLocation TestLab-Rack42
            sysContact ci-runner@example.internal
            sysName switch-test-01
            """)

        # Start local snmpd as an unprivileged process
        cmd = [
            "snmpd",
            "-f",                        # Foreground
            "-r",                        # Do not require root
            "-C",                        # Read only specified config
            "-c", conf_path,
            "-p", pid_path,
            f"udp:127.0.0.1:{TEST_PORT}"
        ]
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        time.sleep(0.5)  # Allow socket initialization

        yield {"port": TEST_PORT, "community": COMMUNITY}

        proc.terminate()
        proc.wait()
