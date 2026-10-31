.. meta::
   :description: Developing network automation software—such as custom telemetry daemons, exporters, and configuration crawlers—presents a fundamental testing challenge:
   :keywords: Python, Snmp, Pytest, Testing, Ci-Cd, Ezsnmp, Test-Automation, Python, ezsnmp, Networking, DevOps
   :author: Carlos Santos (@carlkidcrypto)
   :property=og:title: Testing SNMP Automation Pipelines with pytest and ezsnmp
   :property=og:description: Developing network automation software—such as custom telemetry daemons, exporters, and configuration crawlers—presents a fundamental testing challenge:
   :property=og:type: article
   :property=og:url: https://carlkidcrypto.github.io/blog/ezsnmp-testing-ci-cd-pytest.html
   :property=og:image: https://carlkidcrypto.github.io/_static/logo.png
   :name=twitter:card: summary
   :name=twitter:title: Testing SNMP Automation Pipelines with pytest and ezsnmp
   :name=twitter:description: Developing network automation software—such as custom telemetry daemons, exporters, and configuration crawlers—presents a fundamental testing challenge:
   :name=twitter:image: https://carlkidcrypto.github.io/_static/logo.png

============================================================
Testing SNMP Automation Pipelines with pytest and ezsnmp
============================================================

.. note::

   * **Published:** October 30, 2026
   * **Authors:** Written by Gemini 3.8 Flash, Co-Authored & Reviewed by `Carlos Santos (@carlkidcrypto) <https://github.com/carlkidcrypto>`_
   * **Estimated Reading Time:** 5 minutes
   * **Tags:** `Python` • `Snmp` • `Pytest` • `Testing` • `Ci-Cd` • `Ezsnmp` • `Test-Automation`

The Dilemma of Testing Network Management Code
==============================================

Developing network automation software—such as custom telemetry daemons,
exporters, and configuration crawlers—presents a fundamental testing challenge:

**How do you unit and integration test SNMP code in ephemeral CI/CD pipelines
without physical network switches and routers?**

Traditionally, developers resort to two extremes:

1. **Heavy Mocking (``unittest.mock``)**: Mocking Python session methods tests
   only application logic while completely bypassing Net-SNMP C bindings, MIB
   resolution, ASN.1 type conversion, and network socket behavior.
2. **Dedicated Lab Hardware**: Running tests against real switches in physical
   staging racks introduces hardware dependencies, flakiness, and concurrency
   bottlenecks across CI runner queues.

The modern solution is **hermetic integration testing**: combining pytest
fixtures with local Net-SNMP daemon instances (``snmpd``) or lightweight
simulators.

`ezsnmp <https://github.com/carlkidcrypto/ezsnmp>`_ provides sub-millisecond
execution and thread-safe session lifecycles, enabling test suites to run
hundreds of real UDP queries against local test daemons in seconds.


Hermetic Architecture: Sandboxed Local Daemons
==============================================

Rather than mocking network calls, a hermetic test suite spins up a sandboxed
``snmpd`` process bound to a non-privileged UDP port on ``127.0.0.1``.

Key advantages:

* **Real C-Binding Execution**: Validates actual Net-SNMP C library behavior,
  including MIB parsing, type translation, and PDU serialization.
* **Deterministic Fixtures**: Provides predictable OID trees that run
  identically on local developer laptops and cloud CI runners (GitHub Actions).
* **Fault Injection**: Allows intentional simulation of packet drops, timeouts,
  bad community strings, and malformed ASN.1 structures.


Practical Implementation: Pytest Fixture & Test Suite
=====================================================

1. The Daemon Pytest Fixture (conftest.py)
------------------------------------------

The following fixture creates a temporary, self-contained ``snmpd.conf``,
starts an unprivileged local Net-SNMP daemon on port ``11161``, and tears it
down after the test session:

.. code-block:: python

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

2. Testing Client Operations (test_telemetry.py)
------------------------------------------------

With the daemon fixture running, write clean, deterministic tests verifying
scalar queries, walks, and error handling:

.. code-block:: python

    import pytest
    from ezsnmp import Session
    from ezsnmp.exceptions import EasySNMPTimeoutError

    def test_snmp_get_scalar(snmp_daemon):
        """Verify successful retrieval of scalar system metadata."""
        session = Session(
            hostname=f"127.0.0.1:{snmp_daemon['port']}",
            community=snmp_daemon["community"],
            version=2,
            timeout=1,
            retries=1
        )

        sys_location = session.get("sysLocation.0")
        assert sys_location.value == "TestLab-Rack42"
        assert sys_location.snmp_type == "OCTETSTR"

    def test_snmp_batch_get(snmp_daemon):
        """Verify multi-OID batch queries execute cleanly."""
        session = Session(
            hostname=f"127.0.0.1:{snmp_daemon['port']}",
            community=snmp_daemon["community"],
            version=2
        )

        results = session.get(["sysLocation.0", "sysContact.0", "sysName.0"])
        val_map = {v.oid: v.value for v in results}

        assert val_map["sysLocation"] == "TestLab-Rack42"
        assert val_map["sysContact"] == "ci-runner@example.internal"
        assert val_map["sysName"] == "switch-test-01"

    def test_snmp_timeout_fault_injection():
        """Verify client raises EasySNMPTimeoutError on silent drops."""
        # Query an unreachable blackhole address
        session = Session(
            hostname="192.0.2.1:161",  # RFC 5737 TEST-NET address
            community="public",
            version=2,
            timeout=1,
            retries=1
        )

        with pytest.raises(EasySNMPTimeoutError):
            session.get("sysDescr.0")


CI/CD Integration: GitHub Actions Workflow
==========================================

Run your hermetic test suite automatically in GitHub Actions on every pull
request across multiple Python versions:

.. code-block:: yaml

    name: CI Test Suite

    on: [push, pull_request]

    jobs:
      test:
        runs-on: ubuntu-latest
        strategy:
          matrix:
            python-version: ["3.10", "3.11", "3.12", "3.13"]

        steps:
          - uses: actions/checkout@v4

          - name: Install Net-SNMP Tools & Headers
            run: |
              sudo apt-get update
              sudo apt-get install -y snmp snmpd libsnmp-dev

          - name: Set up Python ${{ matrix.python-version }}
            uses: actions/setup-python@v5
            with:
              python-version: ${{ matrix.python-version }}

          - name: Install Dependencies
            run: |
              pip install --upgrade pip
              pip install pytest pytest-timeout ezsnmp

          - name: Execute Pytest Suite
            run: pytest --timeout=30


Production Best Practices
=========================

* **Enforce Test Timeouts (pytest-timeout)**: Because UDP is connectionless,
  dropped packets in misconfigured CI environments can stall runners. Always
  include ``pytest --timeout=30`` to fail fast.
* **Avoid Root Privileges**: Net-SNMP's ``snmpd -r`` flag permits running the
  daemon as an unprivileged local user, ensuring safe execution in locked-down
  containerized CI agents.
* **Matrix Test SNMPv3 Credentials**: Include dedicated test cases validating
  USM security levels (``authNoPriv`` and ``authPriv``) against test users
  defined in the sandboxed ``snmpd.conf``.


Migration Notes: Easy SNMP vs ezsnmp
====================================

* **Socket & Memory Cleanup in Loops**: Test suites instantiate hundreds of
  ephemeral ``Session`` objects. Legacy ``easysnmp`` leaked C file descriptors
  and memory during repeated session cycles, causing test runners to crash on
  ``EMFILE: Too many open files``.
* **RAII Cleanliness in ezsnmp**: Modern C++17 RAII wrappers ensure Net-SNMP
  sockets and session memory are reclaimed immediately when Python session
  objects go out of scope, guaranteeing robust, leak-free CI test runs.


Useful Links & Community
========================

* **Source Repository**: `carlkidcrypto/ezsnmp on GitHub
  <https://github.com/carlkidcrypto/ezsnmp>`_
* **PyPI Distribution**: `ezsnmp Package on PyPI
  <https://pypi.org/project/ezsnmp/>`_
* **Documentation**: `ezsnmp Online Documentation
  <https://carlkidcrypto.github.io/ezsnmp/>`_
* **Blog & Updates**: `Carlos Santos Blog Updates`_

.. _Carlos Santos Blog Updates:
 https://github.com/carlkidcrypto/carlkidcrypto.github.io/tree/feature/updates
