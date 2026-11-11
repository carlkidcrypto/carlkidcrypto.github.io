.. meta::
   :description: First-Hop Redundancy Protocols (FHRPs)—principally the vendor-neutral **Virtual Router Redundancy Protocol (VRRPv2/v3, RFC 5798)** and Cisco's proprietary...
   :keywords: Python, Snmp, Vrrp, Hsrp, Fhrp, High-Availability, Ezsnmp, Python, ezsnmp, Networking, DevOps
   :author: Carlos Santos (@carlkidcrypto)
   :property=og:title: First-Hop Redundancy Monitoring: VRRP & HSRP with ezsnmp
   :property=og:description: First-Hop Redundancy Protocols (FHRPs)—principally the vendor-neutral **Virtual Router Redundancy Protocol (VRRPv2/v3, RFC 5798)** and Cisco's proprietary...
   :property=og:type: article
   :property=og:url: https://carlkidcrypto.github.io/blog/ezsnmp-vrrp-hsrp-redundancy-monitoring.html
   :property=og:image: https://carlkidcrypto.github.io/_static/logo.png
   :name=twitter:card: summary
   :name=twitter:title: First-Hop Redundancy Monitoring: VRRP & HSRP with ezsnmp
   :name=twitter:description: First-Hop Redundancy Protocols (FHRPs)—principally the vendor-neutral **Virtual Router Redundancy Protocol (VRRPv2/v3, RFC 5798)** and Cisco's proprietary...
   :name=twitter:image: https://carlkidcrypto.github.io/_static/logo.png

============================================================
First-Hop Redundancy Monitoring: VRRP & HSRP with ezsnmp
============================================================

.. note::

   * **Published:** November 03, 2026
   * **Authors:** Written by Gemini 3.8 Flash, Co-Authored & Reviewed by `Carlos Santos (@carlkidcrypto) <https://github.com/carlkidcrypto>`_
   * **Estimated Reading Time:** 5 minutes
   * **Tags:** `Python` • `Snmp` • `Vrrp` • `Hsrp` • `Fhrp` • `High-Availability` • `Ezsnmp`

Why Gateway Redundancy Telemetry Is Critical
============================================

First-Hop Redundancy Protocols (FHRPs)—principally the vendor-neutral
**Virtual Router Redundancy Protocol (VRRPv2/v3, RFC 5798)** and Cisco's
proprietary **Hot Standby Router Protocol (HSRP, RFC 2281)**—provide default
gateway resiliency for campus subnets, server clusters, and storage fabrics.

By sharing a virtual IP (VIP) and virtual MAC (VMAC) address across redundant
routers, FHRP ensures client traffic fails over seamlessly if the active
gateway experiences hardware or uplink failure.

However, gateway redundancy introduces insidious failure modes:

* **Split-Brain / Dual-Master State**: If transit links drop VRRP multicast
  advertisements (224.0.0.18) or ACLs misfilter UDP/IP protocol 112, both
  routers assume the active role, poisoning client ARP tables and dropping
  traffic.
* **No-Master State**: Mismatched authentication keys or misconfigured virtual
  IPs causing all routers to remain in ``Backup`` or ``Initialize`` state.
* **Preemption Churn**: An unstable upstream link causing a higher-priority
  router to repeatedly seize and surrender the Master role.
* **Priority Tracking Failure**: Uplink tracking scripts failing to decrement
  router priority when external transit links disconnect.

`ezsnmp <https://github.com/carlkidcrypto/ezsnmp>`_ provides native Net-SNMP C
bindings to query standard VRRP and HSRP MIBs, allowing engineers to audit
gateway states and detect split-brain anomalies across hundreds of subnets in
milliseconds.


The Architecture of VRRP-MIB (RFC 2787)
=======================================

The standard ``VRRP-MIB`` structures operational gateway telemetry under the
``vrrpOperTable`` (OID ``.1.3.6.1.2.1.68.1.3.1``):

* **``vrrpOperState``**: The Finite State Machine (FSM) integer:
  - ``initialize(1)``: Waiting for startup event or interface up signal.
  - ``backup(2)``: Monitoring Master advertisements; ready to fail over.
  - ``master(3)``: Actively serving the virtual IP and answering ARP queries.
* **``vrrpOperPriority``**: Priority value (1..254, where 255 indicates the
  IP address owner). Higher priority wins Master elections.
* **``vrrpOperMasterIpAddr``**: The primary physical IP address of the router
  currently recognized as Master.
* **``vrrpOperVirtualMacAddr``**: The active virtual MAC address (e.g.
  ``00:00:5E:00:01:{VRID}``).
* **``vrrpOperAdvertisementInterval``**: Time between multicast heartbeat
  advertisements (seconds or centiseconds).
* **``vrrpOperPreemptMode``**: Indicates whether a higher-priority router
  preempts an existing Master (``true(1)`` or ``false(2)``).

Chassis Error Counters
----------------------
Under ``vrrpRouterChecksumErrors``, ``vrrpRouterVersionErrors``, and
``vrrpRouterVrIdErrors``, switches track packet-level reception faults. Spikes
in these counters pinpoint misconfigured VRID numbers or MTU truncation.


Practical Implementation: Redundancy Health Auditor
===================================================

Below is a complete script demonstrating how to query VRRP states across a pair
of redundant gateways and detect split-brain or missing master conditions:

.. code-block:: python

    from ezsnmp import Session
    from ezsnmp.exceptions import GenericError

    VRRP_STATE_MAP = {
        1: "INITIALIZE",
        2: "BACKUP",
        3: "MASTER",
    }

    def parse_numeric(val, default=0):
        digits = "".join(c for c in str(val) if c.isdigit())
        return int(digits) if digits else default

    def extract_vrid(index_str: str, oid_str: str) -> str:
        parts = [p for p in index_str.split(".") if p.isdigit()]
        if parts:
            return parts[-1]
        oid_parts = [p for p in oid_str.split(".") if p.isdigit()]
        if oid_parts:
            return oid_parts[-1]
        return index_str or "0"

    def collect_vrrp_state(hostname: str, community: str = "public") -> dict:
        """Query VRRP operational parameters on a target router."""
        session = Session(
            hostname=hostname,
            community=community,
            version=2,
            timeout=2,
            retries=1,
            set_max_repeaters_to_num=25,
            print_enums_numerically=True
        )

        try:
            # Bulk-walk VRRP operational columns
            state_vars = session.bulk_walk("vrrpOperState")
            prio_vars = session.bulk_walk("vrrpOperPriority")
            master_vars = session.bulk_walk("vrrpOperMasterIpAddr")

            prio_map = {v.index: parse_numeric(v.value) for v in prio_vars}
            master_map = {v.index: v.value for v in master_vars}

            vrid_data = {}
            for v in state_vars:
                # OID index format: [ifIndex].[vrid]
                idx = v.index
                raw_state = str(v.value).strip()
                if raw_state.isdigit():
                    state_code = int(raw_state)
                    state_name = VRRP_STATE_MAP.get(state_code, "UNKNOWN")
                else:
                    state_name = raw_state.upper()
                    state_code = {val: k for k, val in VRRP_STATE_MAP.items()}.get(state_name, 0)

                vrid = extract_vrid(idx, v.oid)

                vrid_data[vrid] = {
                    "vrid": vrid,
                    "state": state_name,
                    "state_code": state_code,
                    "priority": prio_map.get(idx, 0),
                    "master_ip": master_map.get(idx, "Unknown"),
                }

            return vrid_data

        except GenericError as exc:
            print(f"[{hostname}] VRRP query failed: {exc}")
            return {}

    def reconcile_fhrp_pair(rtr1_host: str, rtr2_host: str):
        """Cross-reconcile VRRP states across an HA router pair."""
        rtr1_vrids = collect_vrrp_state(rtr1_host)
        rtr2_vrids = collect_vrrp_state(rtr2_host)

        all_vrids = set(rtr1_vrids.keys()) | set(rtr2_vrids.keys())

        print(f"--- FHRP Reconciliation: {rtr1_host} vs {rtr2_host} ---")
        for vrid in sorted(all_vrids, key=lambda x: parse_numeric(x)):
            g1 = rtr1_vrids.get(vrid, {})
            g2 = rtr2_vrids.get(vrid, {})

            s1 = g1.get("state", "MISSING")
            s2 = g2.get("state", "MISSING")
            p1 = g1.get("priority", 0)
            p2 = g2.get("priority", 0)

            # Detect split-brain (both master) or no-master (both backup/init)
            alert = False
            status = "HEALTHY"

            if s1 == "MASTER" and s2 == "MASTER":
                status = "CRITICAL_SPLIT_BRAIN_DUAL_MASTER"
                alert = True
            elif s1 != "MASTER" and s2 != "MASTER":
                status = "CRITICAL_NO_ACTIVE_MASTER"
                alert = True

            flag = f" [{status}]" if alert else " [OK]"
            print(
                f"  VRID {vrid:>3} | "
                f"{rtr1_host}: {s1:<6} (Prio {p1:>3}) | "
                f"{rtr2_host}: {s2:<6} (Prio {p2:>3}){flag}"
            )

    if __name__ == "__main__":
        reconcile_fhrp_pair("gw-core01.internal", "gw-core02.internal")

📥 `Download this script: reconcile_fhrp_pair.py <https://raw.githubusercontent.com/carlkidcrypto/carlkidcrypto.github.io/main/example_scripts/ezsnmp-vrrp-hsrp-redundancy-monitoring/reconcile_fhrp_pair.py>`_

Production Best Practices
=========================

* **Cross-Reconcile Gateway Pairs**: Auditing a single router in isolation
  cannot confirm gateway health. Always poll peer routers concurrently to verify
  that exactly one router reports ``MASTER`` and the peer reports ``BACKUP``.
* **Monitor Error Counters**: In high-density fabrics, periodically poll
  ``vrrpRouterChecksumErrors``. A rising counter indicates that multicast
  packets are truncating or VLAN tags are leaking between subnets.
* **Correlate with Cisco HSRP MIB**: For enterprise environments running HSRP,
  query ``cHsrpGrpTable`` (OID ``.1.3.6.1.4.1.9.9.106.1.2.1``) to inspect
  ``cHsrpGrpStandbyState`` (Active=6, Standby=5) using identical patterns.


Migration Notes: Easy SNMP vs ezsnmp
====================================

* **Process-Isolated HA Polling**: Cross-reconciling HA pairs requires
  querying multiple hosts simultaneously. While ``ezsnmp`` encapsulates Net-SNMP
  sessions with C++17 RAII structures, Net-SNMP itself uses process-global C
  variables and format locks. For high-frequency HA audits across large router
  inventories, execute checks via ``concurrent.futures.ProcessPoolExecutor``
  to achieve linear concurrency without global lock serialization.
* **Memory Integrity in Fast Heartbeat Audits**: Polling gateway states every
  10 seconds cleanly reclaims Net-SNMP PDU chains via RAII destructors, ensuring
  zero memory leakage in 24/7 monitoring daemons.


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

