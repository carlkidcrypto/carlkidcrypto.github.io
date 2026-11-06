.. meta::
   :description: The Border Gateway Protocol (BGP-4) serves as the routing foundation for the global internet, cloud direct connects, and modern data center spine-leaf Clos...
   :keywords: Python, Snmp, Bgp, Bgp4-Mib, Routing, Ezsnmp, Network-Monitoring, Python, ezsnmp, Networking, DevOps
   :author: Carlos Santos (@carlkidcrypto)
   :property=og:title: BGP Routing Telemetry: Peering States & Prefix Counts in ezsnmp
   :property=og:description: The Border Gateway Protocol (BGP-4) serves as the routing foundation for the global internet, cloud direct connects, and modern data center spine-leaf Clos...
   :property=og:type: article
   :property=og:url: https://carlkidcrypto.github.io/blog/ezsnmp-bgp-routing-telemetry.html
   :property=og:image: https://carlkidcrypto.github.io/_static/logo.png
   :name=twitter:card: summary
   :name=twitter:title: BGP Routing Telemetry: Peering States & Prefix Counts in ezsnmp
   :name=twitter:description: The Border Gateway Protocol (BGP-4) serves as the routing foundation for the global internet, cloud direct connects, and modern data center spine-leaf Clos...
   :name=twitter:image: https://carlkidcrypto.github.io/_static/logo.png

===============================================================
BGP Routing Telemetry: Peering States & Prefix Counts in ezsnmp
===============================================================

.. note::

   * **Published:** November 1, 2026
   * **Authors:** Written by Gemini 3.8 Flash, Co-Authored & Reviewed by `Carlos Santos (@carlkidcrypto) <https://github.com/carlkidcrypto>`_
   * **Estimated Reading Time:** 5 minutes
   * **Tags:** `Python` • `Snmp` • `Bgp` • `Bgp4-Mib` • `Routing` • `Ezsnmp` • `Network-Monitoring`

Why Real-Time BGP Telemetry Is Critical
=======================================

The Border Gateway Protocol (BGP-4) serves as the routing foundation for the
global internet, cloud direct connects, and modern data center spine-leaf
Clos fabrics (BGP EVPN / VXLAN).

Because BGP establishes dynamic path reachability across autonomous systems,
peering failures trigger immediate, widespread outages:

* **Session Flapping**: BGP Finite State Machine (FSM) cycling between
  ``Established``, ``Active``, and ``Idle`` due to MTU mismatches or packet
  loss on transit links.
* **Prefix Drops & Route Leaks**: Transit providers dropping prefix
  advertisements or advertising improper routing filters.
* **Maximum Prefix Saturation**: An upstream peer transmitting more routes
  than the configured threshold, triggering automatic session teardown.

While streaming telemetry (gRPC/gNMI) is gaining traction, legacy enterprise
routers and carrier edge devices ubiquitously support standard BGP MIBs.

`ezsnmp <https://github.com/carlkidcrypto/ezsnmp>`_ provides native Net-SNMP C
bindings to query BGP state tables via ``bulkwalk``, auditing hundreds of
external peering sessions in milliseconds.


The Anatomy of BGP4-MIB & Vendor Extensions
===========================================

Standard BGP monitoring centers on ``BGP4-MIB`` (RFC 4273), supplemented by
vendor extensions (e.g., ``CISCO-BGP4-MIB``) for prefix accounting.

1. Peer Operational States (BGP4-MIB)
-------------------------------------
Under ``bgpPeerTable`` (OID ``.1.3.6.1.2.1.15.3``):

* **``bgpPeerState``**: FSM state integer:
  - ``idle(1)``: Session closed or administratively stopped.
  - ``connect(2)``: Waiting for TCP 3-way handshake.
  - ``active(3)``: Actively attempting to establish TCP connection with peer.
  - ``opensent(4)``: TCP established, Open message sent, awaiting peer response.
  - ``openconfirm(5)``: Awaiting Keepalive or Notification.
  - ``established(6)``: Operational; routes actively exchanged.
* **``bgpPeerRemoteAs``**: Autonomous System Number (ASN) of the peer.
* **``bgpPeerFsmEstablishedTime``**: Total seconds the session has remained
  continuously in the ``established`` state.
* **``bgpPeerInUpdates`` / **``bgpPeerOutUpdates``**: Counter of received and
  transmitted BGP Update routing messages.

2. Prefix Counts (CISCO-BGP4-MIB / Vendor MIBs)
-----------------------------------------------
Under ``cbgpPeerAddrFamilyPrefixTable`` (OID ``.1.3.6.1.4.1.9.9.187.1.2.4.1``):

* **``cbgpPeerAcceptedPrefixes``**: Active routes accepted into the Routing
  Information Base (RIB) from this peer.


Practical Implementation: BGP Peering Health Auditor
====================================================

Below is a complete script using ezsnmp to audit BGP sessions, flag flapping
peers, and verify accepted prefix counts:

.. code-block:: python

    from ezsnmp import Session
    from ezsnmp.exceptions import GenericError

    BGP_STATE_MAP = {
        1: "IDLE",
        2: "CONNECT",
        3: "ACTIVE",
        4: "OPENSENT",
        5: "OPENCONFIRM",
        6: "ESTABLISHED",
    }

    def extract_peer_ip(var) -> str:
        """Extract the 4-octet IPv4 peer address from index or full OID."""
        idx_parts = var.index.split(".")
        if len(idx_parts) >= 4:
            return ".".join(idx_parts[:4])
        oid_parts = [p for p in var.oid.split(".") if p.isdigit()]
        if len(oid_parts) >= 4:
            return ".".join(oid_parts[-4:])
        return var.index

    def audit_bgp_peers(hostname: str, community: str = "public"):
        session = Session(
            hostname=hostname,
            community=community,
            version=2,
            timeout=2,
            retries=1,
            print_enums_numerically=True,
            set_max_repeaters_to_num=25
        )

        try:
            # 1. Bulk-walk standard BGP4-MIB peer table columns
            state_vars = session.bulk_walk("bgpPeerState")
            as_vars = session.bulk_walk("bgpPeerRemoteAs")
            uptime_vars = session.bulk_walk("bgpPeerFsmEstablishedTime")

            # Reconstruct 4-octet peer IP suffix
            as_map = {extract_peer_ip(v): v.value for v in as_vars}
            uptime_map = {extract_peer_ip(v): int(v.value) for v in uptime_vars}

            # 2. Collect accepted prefix counts (CISCO-BGP4-MIB / Vendor MIBs)
            # Index format: [peer_ip (4 octets)].[afi].[safi]
            prefix_map = {}
            try:
                prefix_vars = session.bulk_walk("cbgpPeerAcceptedPrefixes")
                for v in prefix_vars:
                    parts = [p for p in v.index.split(".") if p]
                    if len(parts) < 4:
                        parts = [p for p in v.oid.split(".") if p.isdigit()]
                    if len(parts) >= 6:
                        peer_ip = ".".join(parts[-6:-2])
                        afi, safi = parts[-2], parts[-1]
                        family_key = f"{peer_ip}/AFI{afi}-SAFI{safi}"
                        prefix_map[peer_ip] = int(v.value)
                        prefix_map[family_key] = int(v.value)
                    elif len(parts) >= 4:
                        peer_ip = ".".join(parts[-4:])
                        prefix_map[peer_ip] = int(v.value)
            except GenericError:
                # Gracefully handle non-Cisco devices without prefix extension MIB
                pass

            peer_report = []

            for var in state_vars:
                peer_ip = extract_peer_ip(var)
                state_code = int(var.value)
                state_name = BGP_STATE_MAP.get(state_code, "UNKNOWN")
                remote_as = as_map.get(peer_ip, "Unknown")
                established_sec = uptime_map.get(peer_ip, 0)
                accepted_prefixes = prefix_map.get(peer_ip, 0)

                # Flag down or recently flapped sessions (< 5 minutes)
                is_down = state_code != 6
                is_flapping = state_code == 6 and established_sec < 300

                if is_down:
                    reason = "DOWN"
                elif is_flapping:
                    reason = "FLAPPING"
                else:
                    reason = "OK"

                peer_report.append({
                    "peer_ip": peer_ip,
                    "remote_as": remote_as,
                    "state": state_name,
                    "uptime_sec": established_sec,
                    "prefixes": accepted_prefixes,
                    "alert": is_down or is_flapping,
                    "reason": reason
                })

            return peer_report

        except GenericError as exc:
            print(f"[{hostname}] BGP audit failed: {exc}")
            return []

    if __name__ == "__main__":
        peers = audit_bgp_peers("edge-gw01.internal")
        print("--- BGP Peering Telemetry Report ---")
        for p in peers:
            status_flag = f" [{p['reason']}]" if p["alert"] else ""
            print(
                f"  Peer {p['peer_ip']:<15} (AS{p['remote_as']:<5}) | "
                f"State: {p['state']:<11} | Uptime: {p['uptime_sec']:>6}s | "
                f"Prefixes: {p['prefixes']:>5}{status_flag}"
            )


Production Best Practices
=========================

* **Detect Flapping with EstablishedTime**: A session reporting
  ``ESTABLISHED`` may have restarted seconds ago. Always verify
  ``bgpPeerFsmEstablishedTime``; an uptime under 300 seconds on a core transit
  peer indicates route flap dampening risks.
* **Tune Repetitions on Session Constructor**: Edge routers peering with
  hundreds of full-table downstream clients contain extensive MIB tables.
  Setting ``set_max_repeaters_to_num=25..50`` on the ``Session`` constructor
  retrieves the peering state in fewer round-trips.
* **Correlate Prefix Counts**: Sudden drops in ``cbgpPeerAcceptedPrefixes``
  (e.g., dropping from 900,000 global routes to zero) indicate upstream
  route filtering errors.


Migration Notes: Easy SNMP vs ezsnmp
====================================

Legacy ``easysnmp`` suffered from socket exhaustion and thread contention when
querying high-density BGP tables across multiple border routers in parallel:

* **Process-Isolated Concurrency**: While ``ezsnmp``'s C++17 architecture
  ensures deterministic RAII cleanup for variable binding chains, Net-SNMP
  itself maintains process-global C state and output formatting locks. For
  high-density BGP table crawls across dozens of border routers, use
  ``concurrent.futures.ProcessPoolExecutor`` to eliminate global lock
  contention.
* **Memory Leak Elimination**: Net-SNMP variable binding chains generated
  during multi-thousand-row BGP table walks are safely released via C++17 RAII
  destructors.


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

