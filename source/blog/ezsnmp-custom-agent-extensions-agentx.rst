.. meta::
   :description: While most network engineers interact with SNMP purely as client consumers (running ``GET``, ``WALK``, or ``SET`` queries against network gear), systems...
   :keywords: Python, Snmp, Snmpd, Agentx, Subagent, Ezsnmp, Sysadmin, Python, ezsnmp, Networking, DevOps
   :author: Carlos Santos (@carlkidcrypto)
   :property=og:title: Building Custom SNMP Agent Extensions with Python and ezsnmp
   :property=og:description: While most network engineers interact with SNMP purely as client consumers (running ``GET``, ``WALK``, or ``SET`` queries against network gear), systems...
   :property=og:type: article
   :property=og:url: https://carlkidcrypto.github.io/blog/ezsnmp-custom-agent-extensions-agentx.html
   :property=og:image: https://carlkidcrypto.github.io/_static/logo.png
   :name=twitter:card: summary
   :name=twitter:title: Building Custom SNMP Agent Extensions with Python and ezsnmp
   :name=twitter:description: While most network engineers interact with SNMP purely as client consumers (running ``GET``, ``WALK``, or ``SET`` queries against network gear), systems...
   :name=twitter:image: https://carlkidcrypto.github.io/_static/logo.png

============================================================
Building Custom SNMP Agent Extensions with Python and ezsnmp
============================================================

.. note::

   * **Published:** October 27, 2026
   * **Authors:** Written by Gemini 3.8 Flash, Co-Authored & Reviewed by `Carlos Santos (@carlkidcrypto) <https://github.com/carlkidcrypto>`_
   * **Estimated Reading Time:** 5 minutes
   * **Tags:** `Python` • `Snmp` • `Snmpd` • `Agentx` • `Subagent` • `Ezsnmp` • `Sysadmin`

Extending the SNMP Agent: Beyond Client Polling
===============================================

While most network engineers interact with SNMP purely as client consumers
(running ``GET``, ``WALK``, or ``SET`` queries against network gear), systems
engineers and software architects often face the reverse challenge:

**How do you expose custom application metrics, GPU telemetry, or service
health to an existing enterprise Network Management System (NMS)?**

Enterprise monitoring platforms (such as LibreNMS, Zabbix, SolarWinds, or
PRTG) are deeply entrenched in data center infrastructure. Rather than
deploying custom REST scrapers across isolated security enclaves, exposing
application metrics over standard SNMP allows centralized tools to monitor
custom Python services out of the box.

Writing an entire SNMP daemon from scratch in Python is complex and error-prone.
The standard, production-proven solution is the **AgentX Protocol (RFC 2741)**
and Net-SNMP subagent architecture.

In this guide, we explore how to extend Net-SNMP using Python subagents and how
`ezsnmp <https://github.com/carlkidcrypto/ezsnmp>`_ provides the ideal,
high-speed client harness to validate and benchmark your custom MIB branches.


The Architecture of AgentX Subagents
====================================

The Agent Extensibility (AgentX) protocol decouples core daemon operations from
metric generation:

1. **Master Agent (``snmpd``)**: Runs as a system-level service, binding to
   standard UDP port 161. It manages client access control, SNMPv3 USM
   authentication, and standard RFC MIBs (system, interfaces, CPU).
2. **Local IPC Socket**: The master agent creates a local Unix domain socket
   (typically at ``/var/agentx/master``).
3. **Python Subagent**: Connects to the master agent over the local IPC socket
   and registers a specific Private Enterprise Number (PEN) OID subtree (e.g.
   ``.1.3.6.1.4.1.99999``).

When an external NMS polls an OID within the registered subtree, ``snmpd``
routes the request over AgentX to the Python subagent, which computes the value
and returns it to the client.


Configuring the Net-SNMP Master Agent
=====================================

To enable AgentX master mode in Net-SNMP, edit ``/etc/snmp/snmpd.conf``:

.. code-block:: text

    # Enable AgentX master agent mode
    master agentx

    # Bind AgentX to a secure local Unix domain socket
    agentXSocket /var/agentx/master
    agentXPerms  0770 root snmp

Restart the master daemon to apply changes:

.. code-block:: bash

    sudo systemctl restart snmpd


Implementing a Lightweight Subagent in Python
=============================================

While full AgentX implementations exist, Net-SNMP also supports the lightweight
``pass_persist`` protocol—a high-performance IPC mechanism where ``snmpd``
maintains a persistent bi-directional pipe to a long-running Python script.

1. The Python Metric Provider
-----------------------------

Create a persistent provider script (``/opt/custom_snmp_provider.py``) that
serves custom application metrics:

.. code-block:: python

    import sys
    import time

    BASE_OID = ".1.3.6.1.4.1.99999.1"

    # Define custom metrics under our enterprise branch
    METRICS = {
        # Active worker jobs
        f"{BASE_OID}.1.0": ("integer", lambda: 42),
        # Current queue depth
        f"{BASE_OID}.2.0": ("gauge", lambda: int(time.time()) % 100),
        # Service health string
        f"{BASE_OID}.3.0": ("string", lambda: "Service-Online-OK"),
    }

    def handle_pass_persist():
        while True:
            line = sys.stdin.readline()
            if not line:
                break
            cmd = line.strip()

            if cmd == "PING":
                print("PONG", flush=True)

            elif cmd == "get":
                oid = sys.stdin.readline().strip()
                if oid in METRICS:
                    val_type, val_fn = METRICS[oid]
                    print(oid)
                    print(val_type)
                    print(str(val_fn()), flush=True)
                else:
                    print("NONE", flush=True)

            elif cmd == "getnext":
                oid = sys.stdin.readline().strip()
                sorted_oids = sorted(METRICS.keys())
                match = next((o for o in sorted_oids if o > oid), None)
                if match:
                    val_type, val_fn = METRICS[match]
                    print(match)
                    print(val_type)
                    print(str(val_fn()), flush=True)
                else:
                    print("NONE", flush=True)

    if __name__ == "__main__":
        handle_pass_persist()

2. Registering with snmpd
-------------------------

Add the persistent script to ``/etc/snmp/snmpd.conf``:

.. code-block:: text

    # Pass persistent registration for our enterprise subtree
    pass_persist .1.3.6.1.4.1.99999.1 \
        /usr/bin/python3 /opt/custom_snmp_provider.py

Reload ``snmpd``:

.. code-block:: bash

    sudo systemctl reload snmpd


Validating and Benchmarking with ezsnmp
=======================================

Once your custom agent extension is registered, test and benchmark its
responsiveness using ``ezsnmp``:

.. code-block:: python

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


Production Best Practices
=========================

* **Non-Blocking Metric Computation**: In custom subagents, avoid blocking I/O
  (like slow database queries) inside the SNMP request handler. Compute metrics
  in a background worker thread and store results in an in-memory dictionary to
  ensure SNMP responses return in under 10 milliseconds.
* **Keep Private Enterprise Numbers (PEN) Clean**: Request an official, free
  PEN from the Internet Assigned Numbers Authority (IANA) for enterprise
  production rather than squatting on experimental ranges.
* **Automate Regression Tests**: Run automated CI test suites using ``ezsnmp``
  against your custom agent scripts to verify OID ordering and data types
  before deploying to production servers.


Migration Notes: Easy SNMP vs ezsnmp
====================================

* **Subagent Stress Testing**: Testing high-frequency subagents requires running
  thousands of client queries in tight loops. Legacy ``easysnmp`` suffered from
  socket exhaustion and thread synchronization deadlocks during stress testing.
* **C++17 Thread Safety in ezsnmp**: ``ezsnmp``'s modernized C++17 architecture
  ensures clean connection lifecycle management, allowing load testing tools to
  hammer custom subagents at thousands of queries per second.


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
