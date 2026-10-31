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
  - ``active(3)``: TCP handshake established, awaiting BGP Open message.
  - ``opensent(4)``: Open message sent, awaiting peer response.
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

    def audit_bgp_peers(hostname: str, community: str = "public"):
        session = Session(
            hostname=hostname,
            community=community,
            version=2,
            timeout=2,
            retries=1
        )

        try:
            # 1. Bulk-walk BGP peer table columns
            state_vars = session.bulk_walk("bgpPeerState", max_repetitions=25)
            as_vars = session.bulk_walk("bgpPeerRemoteAs", max_repetitions=25)
            uptime_vars = session.bulk_walk(
                "bgpPeerFsmEstablishedTime", max_repetitions=25
            )

            as_map = {v.index: v.value for v in as_vars}
            uptime_map = {v.index: int(v.value) for v in uptime_vars}

            # 2. Collect accepted prefix counts (CISCO-BGP4-MIB)
            prefix_vars = session.bulk_walk(
                "cbgpPeerAcceptedPrefixes", max_repetitions=25
            )
            # Index format: [peer_ip].[afi].[safi]
            prefix_map = {}
            for v in prefix_vars:
                peer_ip = ".".join(v.index.split(".")[:4])
                prefix_map[peer_ip] = int(v.value)

            peer_report = []

            for var in state_vars:
                peer_ip = var.index
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
* **Tune max_repetitions for Peering Scale**: Edge routers peering with
  hundreds of full-table downstream clients contain extensive MIB tables.
  Setting ``max_repetitions=25`` retrieves the entire peering state in one or
  two round-trips.
* **Correlate Prefix Counts**: Sudden drops in ``cbgpPeerAcceptedPrefixes``
  (e.g., dropping from 900,000 global routes to zero) indicate upstream
  route filtering errors.


Migration Notes: Easy SNMP vs ezsnmp
====================================

Legacy ``easysnmp`` suffered from socket exhaustion and thread contention when
querying high-density BGP tables across multiple border routers in parallel:

* **Clean Thread Isolation in ezsnmp**: ``ezsnmp``'s modernized C++17
  session locking eliminates global lock contention, enabling parallel worker
  threads to poll dozens of border routers simultaneously.
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
