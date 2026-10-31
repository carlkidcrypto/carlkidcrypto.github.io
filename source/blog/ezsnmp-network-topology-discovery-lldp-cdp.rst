.. meta::
   :description: Maintaining accurate, real-time physical network maps is an essential requirement for data center automation, root-cause failure analysis, and Source of...
   :keywords: Python, Snmp, Lldp, Cdp, Topology, Ezsnmp, Network-Automation, Python, ezsnmp, Networking, DevOps
   :author: Carlos Santos (@carlkidcrypto)
   :property=og:title: Automating Network Topology Discovery: LLDP and CDP with ezsnmp
   :property=og:description: Maintaining accurate, real-time physical network maps is an essential requirement for data center automation, root-cause failure analysis, and Source of...
   :property=og:type: article
   :property=og:url: https://carlkidcrypto.github.io/blog/ezsnmp-network-topology-discovery-lldp-cdp.html
   :property=og:image: https://carlkidcrypto.github.io/_static/logo.png
   :name=twitter:card: summary
   :name=twitter:title: Automating Network Topology Discovery: LLDP and CDP with ezsnmp
   :name=twitter:description: Maintaining accurate, real-time physical network maps is an essential requirement for data center automation, root-cause failure analysis, and Source of...
   :name=twitter:image: https://carlkidcrypto.github.io/_static/logo.png

===============================================================
Automating Network Topology Discovery: LLDP and CDP with ezsnmp
===============================================================

.. note::

   * **Published:** October 23, 2026
   * **Authors:** Written by Gemini 3.8 Flash, Co-Authored & Reviewed by `Carlos Santos (@carlkidcrypto) <https://github.com/carlkidcrypto>`_
   * **Estimated Reading Time:** 5 minutes
   * **Tags:** `Python` • `Snmp` • `Lldp` • `Cdp` • `Topology` • `Ezsnmp` • `Network-Automation`

Why Layer-2 Discovery Matters
=============================

Maintaining accurate, real-time physical network maps is an essential
requirement for data center automation, root-cause failure analysis, and
Source of Truth (SoT) reconciliation in tools like NetBox.

Instead of manually tracing patch cables or maintaining brittle static
spreadsheets, network engineers rely on Layer-2 neighbor discovery protocols:

* **Link Layer Discovery Protocol (LLDP / IEEE 802.1AB)**: An open, vendor-
  neutral standard supported across modern switches, routers, and servers.
* **Cisco Discovery Protocol (CDP)**: A legacy proprietary protocol widely
  deployed across enterprise campus infrastructure.

Both protocols broadcast device identifiers, remote port names, and system
capabilities across adjacent physical links.

`ezsnmp <https://github.com/carlkidcrypto/ezsnmp>`_ provides the high-speed
C-binding execution needed to crawl hundreds of network switches, extract
neighbor tables via ``bulkwalk``, and reconstruct complete topology graphs in
seconds.


The Anatomy of the LLDP-MIB
===========================

The standard ``LLDP-MIB`` organizes remote neighbor relationships under the
``lldpRemTable`` (OID prefix ``.1.0.8802.1.1.2.1.4.1``).

Unlike simple scalar metrics, each row in ``lldpRemTable`` is indexed by three
distinct components:

1. **``lldpRemTimeMark``**: A timeline integer representing when the neighbor
   record was updated.
2. **``lldpRemLocalPortNum``**: The local port identifier on the polled switch.
3. **``lldpRemIndex``**: A unique sequential integer identifying multiple
   neighbors on a shared segment.

Key columnar leaf objects in ``lldpRemTable`` include:

* **``lldpRemSysName``**: Hostname or FQDN of the adjacent neighbor switch.
* **``lldpRemPortId``**: Remote port identifier (e.g. ``GigabitEthernet1/0/1``
  or ``Ethernet1/1``).
* **``lldpRemPortDesc``**: Descriptive string configured on the remote port.
* **``lldpRemSysDesc``**: Operating system version and hardware platform.


Practical Implementation: Topology Crawler
==========================================

Below is a complete, production-ready script that polls a network switch,
resolves local port names, extracts LLDP neighbors, and constructs a clean
link adjacency map:

.. code-block:: python

    from collections import defaultdict
    from ezsnmp import Session
    from ezsnmp.exceptions import EasySNMPError

    def discover_lldp_topology(hostname: str, community: str = "public"):
        """Extract physical Layer-2 neighbors using ezsnmp bulkwalk."""
        session = Session(
            hostname=hostname,
            community=community,
            version=2,
            timeout=2,
            retries=1
        )

        try:
            # 1. Map local port numbers to human-readable interface names
            local_ports = {}
            if_descr_vars = session.bulkwalk("ifDescr", max_repetitions=25)
            for var in if_descr_vars:
                local_ports[var.oid_index] = var.value

            # 2. Bulk-walk LLDP remote table columns
            remote_sys_vars = session.bulkwalk(
                "lldpRemSysName", max_repetitions=25
            )
            remote_port_vars = session.bulkwalk(
                "lldpRemPortId", max_repetitions=25
            )

            # 3. Index remote metrics by index tuple
            remote_systems = {v.oid_index: v.value for v in remote_sys_vars}
            remote_ports = {v.oid_index: v.value for v in remote_port_vars}

            adjacencies = []

            for idx, remote_device in remote_systems.items():
                # Split composite index: [time_mark].[local_port_num].[rem_idx]
                parts = idx.split(".")
                if len(parts) >= 2:
                    local_port_num = parts[1]
                    local_port_name = local_ports.get(
                        local_port_num, f"Port-{local_port_num}"
                    )
                    remote_port_name = remote_ports.get(idx, "Unknown")

                    adjacencies.append({
                        "local_device": hostname,
                        "local_port": local_port_name,
                        "remote_device": remote_device,
                        "remote_port": remote_port_name,
                    })

            return adjacencies

        except EasySNMPError as exc:
            print(f"[{hostname}] Topology discovery failed: {exc}")
            return []

    if __name__ == "__main__":
        links = discover_lldp_topology("core-sw01.internal")
        print(f"Discovered {len(links)} Layer-2 links:")
        for link in links:
            print(
                f"  {link['local_device']}:{link['local_port']} <---> "
                f"{link['remote_device']}:{link['remote_port']}"
            )


Handling Multi-Vendor Protocol Differences: LLDP vs CDP
=======================================================

In heterogeneous environments featuring both modern whitebox switches and
legacy Cisco infrastructure:

1. **Dual-Protocol Strategy**: Attempt LLDP collection first. If
   ``lldpRemSysName`` returns zero records, fall back to ``CISCO-CDP-MIB``:
   - Walk ``cdpCacheDeviceId`` (OID ``.1.3.6.1.4.1.9.9.23.1.2.1.1.6``).
   - Walk ``cdpCacheDevicePort`` (OID ``.1.3.6.1.4.1.9.9.23.1.2.1.1.7``).
2. **Hex-Encoded Chassis IDs**: Certain vendors transmit MAC addresses as raw
   binary OCTET STRINGs in ``lldpRemChassisId``. Use ``var.value`` with safe
   hex formatting (``':'.join(f'{b:02x}' for b in bytes)``) when parsing.


Production Best Practices
=========================

* **Combine Multi-Threading with Crawler Iterations**: Topology discovery
  involves traversing a tree of devices. Use Python's
  ``concurrent.futures.ThreadPoolExecutor`` alongside ezsnmp to crawl dozens of
  discovered neighbor switches in parallel.
* **Prevent Discovery Loops**: Maintain a set of visited IP addresses and
  hostnames to prevent cyclic graph traversal when crawling mesh fabrics.
* **Tune max_repetitions**: Standard switch stacks contain dozens of neighbor
  entries. Setting ``max_repetitions=25`` ensures complete neighbor tables are
  retrieved in just one or two UDP round-trips.


Migration Notes: Easy SNMP vs ezsnmp
====================================

* **Safe Large-Scale Graph Traversals**: Legacy ``easysnmp`` suffered from
  cumulative memory leakage during recursive multi-thousand-node graph walks.
  ``ezsnmp``'s modern C++17 RAII memory management ensures PDU chains are
  freed after every switch crawl, enabling long-running discovery engines.
* **String Encoding Stability**: Clean handling of raw bytes ensures strange
  neighbor device names or chassis IDs never trigger Python decoding faults.


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
