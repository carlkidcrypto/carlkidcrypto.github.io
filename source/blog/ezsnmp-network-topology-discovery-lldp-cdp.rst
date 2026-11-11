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
    from ezsnmp.exceptions import GenericError

    def extract_composite_index(oid: str, index: str) -> str:
        """Extract composite LLDP suffix (time_mark.local_port.rem_idx) from Result."""
        combined = f"{oid}.{index}" if index else oid
        parts = combined.split(".")
        # LLDP remote table indices consist of 3 sub-identifiers: [time_mark].[local_port].[rem_idx]
        return ".".join(parts[-3:]) if len(parts) >= 3 else index

    def discover_lldp_topology(hostname: str, community: str = "public"):
        """Extract physical Layer-2 neighbors using ezsnmp bulk_walk."""
        session = Session(
            hostname=hostname,
            community=community,
            version=2,
            timeout=2,
            retries=1,
            set_max_repeaters_to_num=25
        )

        try:
            # 1. Map local port numbers to human-readable interface names using LLDP-MIB
            # lldpLocPortDesc uses the exact local port numbering space as lldpRemTable
            local_ports = {}
            loc_port_vars = session.bulk_walk("lldpLocPortDesc")
            for var in loc_port_vars:
                local_ports[var.index] = var.value

            # 2. Bulk-walk LLDP remote table columns
            remote_sys_vars = session.bulk_walk("lldpRemSysName")
            remote_port_vars = session.bulk_walk("lldpRemPortId")

            # 3. Index remote metrics by full composite index
            remote_systems = {
                extract_composite_index(v.oid, v.index): v.value
                for v in remote_sys_vars
            }
            remote_ports = {
                extract_composite_index(v.oid, v.index): v.value
                for v in remote_port_vars
            }

            adjacencies = []

            for comp_idx, remote_device in remote_systems.items():
                parts = comp_idx.split(".")
                # [time_mark].[local_port_num].[rem_idx]
                local_port_num = parts[1] if len(parts) >= 3 else parts[0]
                local_port_name = local_ports.get(
                    local_port_num, f"Port-{local_port_num}"
                )
                remote_port_name = remote_ports.get(comp_idx, "Unknown")

                adjacencies.append({
                    "local_device": hostname,
                    "local_port": local_port_name,
                    "remote_device": remote_device,
                    "remote_port": remote_port_name,
                })

            return adjacencies

        except GenericError as exc:
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

📥 `Download this script: 01_discover_lldp_topology.py <https://raw.githubusercontent.com/carlkidcrypto/carlkidcrypto.github.io/main/example_scripts/ezsnmp-network-topology-discovery-lldp-cdp/01_discover_lldp_topology.py>`_

Handling Multi-Vendor Protocol Differences: LLDP vs CDP
=======================================================

In heterogeneous environments featuring both modern whitebox switches and
legacy Cisco infrastructure:

1. **Multi-Protocol Collection & Deduplication**: Rather than falling back to
   CDP only when the LLDP table is completely empty (which misses CDP-only links
   on mixed-vendor trunks), query both LLDP and ``CISCO-CDP-MIB`` where supported.
   Merge the neighbor records and deduplicate links by normalized local and remote
   endpoints:

   * Walk ``lldpRemSysName`` and ``lldpRemPortId`` for IEEE standard neighbors.
   * Walk ``cdpCacheDeviceId`` (OID ``.1.3.6.1.4.1.9.9.23.1.2.1.1.6``) and
     ``cdpCacheDevicePort`` (OID ``.1.3.6.1.4.1.9.9.23.1.2.1.1.7``) for Cisco devices.
   * Deduplicate using a unique key ``(local_port, remote_device)``.

2. **Hex-Encoded Chassis IDs & MAC Addresses**: Certain vendors transmit
   chassis identifiers (such as MAC addresses) as formatted hexadecimal strings
   in ``lldpRemChassisId`` when ``lldpRemChassisIdSubtype`` indicates a MAC
   address (subtype 4). Because ezsnmp provides formatted text in ``var.value``,
   parse hexadecimal sequences before normalizing:

.. code-block:: python

    def format_chassis_mac(raw_hex: str) -> str:
        """Normalize hex-formatted chassis MAC string to colon-separated notation."""
        clean_hex = raw_hex.replace(" ", "").replace(":", "").replace("-", "")
        if len(clean_hex) == 12:
            return ":".join(clean_hex[i:i + 2].lower() for i in range(0, 12, 2))
        return raw_hex

📥 `Download this script: 02_format_chassis_mac.py <https://raw.githubusercontent.com/carlkidcrypto/carlkidcrypto.github.io/main/example_scripts/ezsnmp-network-topology-discovery-lldp-cdp/02_format_chassis_mac.py>`_

Production Best Practices
=========================

* **Process Isolation for High-Concurrency Crawlers**: Topology discovery
  involves traversing hundreds of switches in a network fabric. Because Net-SNMP
  retains process-global C state, crawl switches concurrently using Python's
  ``concurrent.futures.ProcessPoolExecutor`` (creating an isolated ``Session``
  inside each worker process) rather than unconstrained thread pools.
* **Prevent Discovery Loops**: Maintain a set of visited IP addresses and
  hostnames to prevent cyclic graph traversal when crawling mesh fabrics.
* **Tune Repetition Bounds via Session Constructor**: Standard switch stacks
  contain dozens of neighbor entries. Setting ``set_max_repeaters_to_num=25..50``
  in the ``Session`` constructor configures GETBULK batch sizing, reducing UDP
  round-trips across multi-port chassis.


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

----

.. warning::

   AI-generated content may contain misinformation or mistakes. A human does review this, but we are only human.

