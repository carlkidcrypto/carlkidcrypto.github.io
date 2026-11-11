.. meta::
   :description: Interior Gateway Protocols (IGPs)—principally **OSPF (v2/v3, RFC 2328 / RFC 5340)** and **IS-IS (RFC 1195)**—form the dynamic routing core of enterprise...
   :keywords: Python, Snmp, Ospf, Is-Is, Link-State, Routing, Ezsnmp, Python, ezsnmp, Networking, DevOps
   :author: Carlos Santos (@carlkidcrypto)
   :property=og:title: OSPF & IS-IS Link-State Telemetry: Neighbor Auditing in ezsnmp
   :property=og:description: Interior Gateway Protocols (IGPs)—principally **OSPF (v2/v3, RFC 2328 / RFC 5340)** and **IS-IS (RFC 1195)**—form the dynamic routing core of enterprise...
   :property=og:type: article
   :property=og:url: https://carlkidcrypto.github.io/blog/ezsnmp-ospf-isis-link-state-telemetry.html
   :property=og:image: https://carlkidcrypto.github.io/_static/logo.png
   :name=twitter:card: summary
   :name=twitter:title: OSPF & IS-IS Link-State Telemetry: Neighbor Auditing in ezsnmp
   :name=twitter:description: Interior Gateway Protocols (IGPs)—principally **OSPF (v2/v3, RFC 2328 / RFC 5340)** and **IS-IS (RFC 1195)**—form the dynamic routing core of enterprise...
   :name=twitter:image: https://carlkidcrypto.github.io/_static/logo.png

==============================================================
OSPF & IS-IS Link-State Telemetry: Neighbor Auditing in ezsnmp
==============================================================

.. note::

   * **Published:** November 01, 2026
   * **Authors:** Written by Gemini 3.8 Flash, Co-Authored & Reviewed by `Carlos Santos (@carlkidcrypto) <https://github.com/carlkidcrypto>`_
   * **Estimated Reading Time:** 5 minutes
   * **Tags:** `Python` • `Snmp` • `Ospf` • `Is-Is` • `Link-State` • `Routing` • `Ezsnmp`

Why Link-State Protocol Telemetry Is Critical
=============================================

Interior Gateway Protocols (IGPs)—principally **OSPF (v2/v3, RFC 2328 / RFC
5340)** and **IS-IS (RFC 1195)**—form the dynamic routing core of enterprise
campuses, data center underlays, and service provider backbones.

Because link-state protocols construct a synchronized map of the entire
autonomous system using Link State Advertisements (LSAs), localized adjacency
failures can trigger rapid, cascading network disruption:

* **Stuck Adjacencies**: Sessions trapped in intermediate states (such as
  ``ExStart`` or ``Exchange``) due to interface MTU mismatches, blocking
  database synchronization.
* **Adjacency Flapping**: Loss of OSPF Hello packets across lossy transit links
  causing cyclic Shortest Path First (SPF) recalculations and high CPU spikes.
* **LSA Retransmission Storms**: Unacknowledged LSAs accumulating in
  retransmission queues during packet drop events.
* **DR/BDR Election Churn**: Unstable broadcast segments repeatedly re-electing
  Designated Routers, resetting neighbor adjacencies.

While streaming telemetry (gNMI) is deployed on modern whitebox switches,
enterprise routers, firewalls, and campus core appliances ubiquitously expose
standard link-state telemetry through SNMP.

`ezsnmp <https://github.com/carlkidcrypto/ezsnmp>`_ provides native Net-SNMP C
bindings to query OSPF and IS-IS neighbor tables via ``bulkwalk``, auditing link
adjacencies and queue health in fractions of a second.


The Architecture of OSPF-MIB (RFC 4750)
=======================================

The IETF standard ``OSPF-MIB`` organizes link-state telemetry into neighbor
and interface state tables:

1. Neighbor State Machine (ospfNbrTable)
----------------------------------------
Under ``ospfNbrTable`` (OID ``.1.3.6.1.2.1.14.10.1``):

* **``ospfNbrState``**: The Finite State Machine (FSM) integer:
  - ``down(1)``: No recent information received from neighbor.
  - ``attempt(2)``: Probing neighbor on NBMA networks.
  - ``init(3)``: Hello received, but bidirectional communication unconfirmed.
  - ``twoWay(4)``: Bidirectional communication verified (access segment state).
  - ``exchangeStart(5)``: Negotiating master/slave roles and DD sequence.
  - ``exchange(6)``: Actively exchanging Database Description (DD) packets.
  - ``loading(7)``: Requesting and receiving Link State Request (LSR) packets.
  - ``full(8)``: Fully synchronized; operational routing adjacency.
* **``ospfNbrRtrId``**: The remote neighbor's Router ID (RID).
* **``ospfNbrEvents``**: Counter tracking total FSM state transitions. Spikes
  in this counter identify chronic link flapping.
* **``ospfNbrLsRetransQLen``**: Number of LSAs currently awaiting
  retransmission. Values greater than zero indicate packet loss or remote agent
  congestion. Note that transient non-zero values can occur during routine flooding;
  persistent queues across consecutive polling cycles indicate MTU mismatch or packet loss.

2. Interface & Role States (ospfIfTable)
----------------------------------------
Under ``ospfIfTable`` (OID ``.1.3.6.1.2.1.14.7.1``):

* **``ospfIfDesignatedRouter``**: IP address of the elected Designated Router.
* **``ospfIfBackupDesignatedRouter``**: IP address of the elected Backup DR.


Practical Implementation: OSPF Neighbor Health Auditor
======================================================

Below is a complete script demonstrating how to audit OSPF neighbor
adjacencies, detect stuck sessions, and flag LSA retransmission bottlenecks via
ezsnmp:

.. code-block:: python

    from ezsnmp import Session
    from ezsnmp.exceptions import GenericError

    OSPF_STATE_MAP = {
        1: "DOWN",
        2: "ATTEMPT",
        3: "INIT",
        4: "2-WAY",
        5: "EXSTART",
        6: "EXCHANGE",
        7: "LOADING",
        8: "FULL",
    }

    def parse_numeric(val, default=0):
        digits = "".join(c for c in str(val) if c.isdigit())
        return int(digits) if digits else default

    def extract_composite_index(var) -> str:
        """Extract the complete table row index suffix ([neighbor_ip].[address_less_index])."""
        oid_parts = [p for p in str(var.oid).split(".") if p.strip()]
        idx_parts = [p for p in str(var.index).split(".") if p.strip()]
        if len(idx_parts) >= 5:
            return ".".join(idx_parts[:5])
        combined = oid_parts + idx_parts
        numeric = [p for p in combined if p.isdigit()]
        if len(numeric) >= 5:
            return ".".join(numeric[-5:])
        return var.index or "0"

    def extract_nbr_ip_from_key(key: str) -> str:
        parts = [p for p in key.split(".") if p.isdigit()]
        if len(parts) >= 4:
            return ".".join(parts[:4])
        return key

    def audit_ospf_neighbors(hostname: str, community: str = "public"):
        """Audit OSPF neighbor states, flap events, and LSA queue depth."""
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
            # 1. Bulk-walk OSPF neighbor table columns
            state_vars = session.bulk_walk("ospfNbrState")
            rtr_vars = session.bulk_walk("ospfNbrRtrId")
            event_vars = session.bulk_walk("ospfNbrEvents")
            retrans_vars = session.bulk_walk("ospfNbrLsRetransQLen")

            # Map by composite 5-part index to avoid collisions on address-less indices
            rtr_map = {extract_composite_index(v): v.value for v in rtr_vars}
            event_map = {extract_composite_index(v): parse_numeric(v.value) for v in event_vars}
            retrans_map = {extract_composite_index(v): parse_numeric(v.value) for v in retrans_vars}

            neighbors = []

            for var in state_vars:
                idx = extract_composite_index(var)
                nbr_ip_str = extract_nbr_ip_from_key(idx)

                raw_state = str(var.value).strip()
                if raw_state.isdigit():
                    state_code = int(raw_state)
                    state_name = OSPF_STATE_MAP.get(
                        state_code, f"CODE_{state_code}"
                    )
                else:
                    state_name = raw_state.upper()
                    state_code = {v: k for k, v in OSPF_STATE_MAP.items()}.get(state_name, 0)

                rtr_id = rtr_map.get(idx, "Unknown")
                events = event_map.get(idx, 0)
                retrans_len = retrans_map.get(idx, 0)

                # Evaluate operational state vs abnormal/unidirectional or transitional conditions
                is_down = state_code == 1
                is_init_or_attempt = state_code in (2, 3)
                is_transitional = state_code in (5, 6, 7)
                is_2way = state_code == 4
                is_full = state_code == 8
                has_retrans = retrans_len > 0

                status = "OPERATIONAL"
                alert = False
                if is_down:
                    status = "DOWN"
                    alert = True
                elif is_init_or_attempt:
                    status = "INIT_UNIDIRECTIONAL_OR_ATTEMPT"
                    alert = True
                elif is_transitional:
                    # Single snapshots may capture normal transitions; qualify as transitional/stuck
                    status = "TRANSITIONAL_OR_STUCK"
                    alert = True
                elif has_retrans:
                    # Retransmission backlog: persistent queues indicate MTU mismatch or packet loss
                    status = "RETRANS_QUEUE_BACKLOG"
                    alert = True
                elif is_2way:
                    status = "2-WAY_DROTHER"
                    alert = False
                elif is_full:
                    status = "FULL"
                    alert = False

                neighbors.append({
                    "neighbor_ip": nbr_ip_str,
                    "router_id": rtr_id,
                    "state": state_name,
                    "flaps": events,
                    "retrans_queue": retrans_len,
                    "status": status,
                    "alert": alert
                })

            return neighbors

        except GenericError as exc:
            print(f"[{hostname}] OSPF audit failed: {exc}")
            return []

    if __name__ == "__main__":
        results = audit_ospf_neighbors("core-rtr01.internal")
        print("--- OSPF Neighbor Telemetry Report ---")
        for n in results:
            flag = f" [{n['status']}]" if n["alert"] else ""
            print(
                f"  Neighbor {n['neighbor_ip']:<15} "
                f"(RID: {n['router_id']:<15}) | "
                f"State: {n['state']:<8} | Flaps: {n['flaps']:>3} | "
                f"RetransQ: {n['retrans_queue']:>2}{flag}"
            )

📥 `Download this script: audit_ospf_neighbors.py <https://raw.githubusercontent.com/carlkidcrypto/carlkidcrypto.github.io/main/example_scripts/ezsnmp-ospf-isis-link-state-telemetry/audit_ospf_neighbors.py>`_

Diagnosing Root Causes from Telemetry Signatures
================================================

1. Stuck in ExStart (State 5) -> MTU Mismatch
---------------------------------------------
When an OSPF adjacency is trapped in ``ExStart`` or ``Exchange``, the neighbors
agree on master/slave roles but fail to complete Database Description (DD)
packet transmission. In 95% of cases, this indicates that the interface MTU on
one end is smaller than the neighbor's MTU, causing large DD packets to drop.

2. LSA Retransmission Spikes (ospfNbrLsRetransQLen > 0)
-------------------------------------------------------
If ``ospfNbrLsRetransQLen`` remains elevated, link-state update datagrams are
dropping across the transit path. Check for optical signal degradation (DOM/DDM)
or microburst queue discards on the transit switch ports.


Production Best Practices
=========================

* **Separate P2P from Broadcast Adjacencies**: On point-to-point links (e.g.
  ``/30`` or ``/31`` subnets), ensure interfaces are configured as
  ``ip ospf network point-to-point`` to bypass unnecessary DR/BDR elections.
* **Poll Retransmission Queues Proactively**: Polling ``ospfNbrLsRetransQLen``
  every 30 seconds detects packet drop conditions minutes before dead timers
  expire and tear down routing sessions.
* **Correlate with IS-IS MIB**: For dual-stack backbones running IS-IS, query
  ``isisISAdjTable`` (OID ``.1.3.6.1.2.1.138.1.6.1``) to audit Layer-2 IS-IS
  adjacencies using identical C-binding patterns. Note that transient state changes
  during initial handshake should be confirmed with consecutive polling samples
  before alarming on MTU mismatch or packet loss.


Migration Notes: Easy SNMP vs ezsnmp
====================================

Legacy ``easysnmp`` suffered from thread safety bugs and socket exhaustion when
querying high-density core routers with dozens of OSPF areas and hundreds of
neighbors:

* **Process-Isolated Concurrency**: While ``ezsnmp``'s C++17 architecture
  ensures deterministic RAII cleanup for variable binding chains, Net-SNMP
  itself maintains process-global C state and output formatting locks. For
  high-density link-state table crawls across large routing backbones, use
  ``concurrent.futures.ProcessPoolExecutor`` to eliminate global lock
  contention.
* **Memory Safety**: Rapid cyclic polling of OSPF tables cleanly frees all
  Net-SNMP variable bindings via modern C++17 RAII wrappers, preventing the
  memory bloat common in legacy tools.


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

