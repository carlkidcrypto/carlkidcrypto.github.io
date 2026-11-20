.. meta::
   :description: Audit BGP EVPN control-plane sessions, VNI state, and VXLAN tunnel endpoints (VTEPs) across leaf-spine data center fabrics using ezsnmp and Net-SNMP.
   :keywords: ezsnmp, Python, SNMP, BGP, EVPN, VXLAN, Networking, Telemetry, Data Center
   :author: Carlos Santos (@carlkidcrypto)
   :property=og:title: Auditing BGP EVPN and VXLAN Overlay Fabric Health with ezsnmp
   :property=og:description: Audit BGP EVPN control-plane sessions, VNI state, and VXLAN tunnel endpoints (VTEPs) across leaf-spine data center fabrics using ezsnmp and Net-SNMP.
   :property=og:type: article
   :property=og:url: https://carlkidcrypto.github.io/blog/ezsnmp-bgp-evpn-vxlan-fabric-telemetry.html
   :property=og:image: https://carlkidcrypto.github.io/_static/logo.png
   :name=twitter:card: summary
   :name=twitter:title: Auditing BGP EVPN and VXLAN Overlay Fabric Health with ezsnmp
   :name=twitter:description: Audit BGP EVPN control-plane sessions, VNI state, and VXLAN tunnel endpoints (VTEPs) across leaf-spine data center fabrics using ezsnmp and Net-SNMP.
   :name=twitter:image: https://carlkidcrypto.github.io/_static/logo.png

=============================================================
Auditing BGP EVPN and VXLAN Overlay Fabric Health with ezsnmp
=============================================================

.. note::

   * **Published:** November 11, 2026
   * **Authors:** Written by Gemini 3.8 Flash, Co-Authored & Reviewed by `Carlos Santos (@carlkidcrypto) <https://github.com/carlkidcrypto>`_
   * **Estimated Reading Time:** 5 minutes
   * **Tags:** `ezsnmp` • `Python` • `SNMP` • `BGP` • `EVPN` • `VXLAN` • `Networking` • `Telemetry`

Modern cloud datacenters and high-performance enterprise networks rely on
Virtual Extensible LAN (VXLAN) overlays coupled with a BGP Ethernet Virtual
Private Network (EVPN) control plane. This leaf-spine architecture replaces
legacy spanning-tree protocols, enabling multi-tenant Layer 2/Layer 3 network
virtualization with full Equal-Cost Multi-Path (ECMP) underlay utilization.

In an EVPN-VXLAN fabric, physical leaf switches act as VXLAN Tunnel Endpoints
(VTEPs). They encapsulate tenant Ethernet frames inside UDP datagrams tagged
with 24-bit Virtual Network Identifiers (VNIs). Instead of relying on data-plane
flood-and-learn discovery, leaf switches exchange BGP EVPN routes
(AFI=25, SAFI=70) to distribute MAC address reachability (Type 2), multicast
flood lists (Type 3), and IP prefixes (Type 5).

When control-plane peering degrades or VNI state falls out of sync, packets
experience silent blackholing, split-brain forwarding, or asymmetrical routing.
Automating proactive telemetry across fabric switches is essential for zero-loss
operations.

The `ezsnmp <https://github.com/carlkidcrypto/ezsnmp>`_ library provides native
C/C++17 bindings directly to Net-SNMP, enabling network automation engineers to
audit BGP sessions, VTEP reachability, and VNI health across dozens of fabric
switches simultaneously.

In this tutorial, we will examine the EVPN-VXLAN MIB telemetry model, inspect
BGP peering and interface states, and build a high-performance fabric auditing
tool using ``ezsnmp``.

The Telemetry Architecture of an EVPN-VXLAN Fabric
==================================================

A robust telemetry auditor must monitor three correlated layers across every
leaf and spine switch:

1. **Underlay Routing & IP Reachability**: Ensures loopback VTEP addresses
   (typically ``Loopback0``) and point-to-point links between leaves and spines
   pass underlay traffic with zero packet drops.
2. **Control-Plane Peering (BGP EVPN)**: Monitors Multi-Protocol BGP (MP-BGP)
   peering states between leaf VTEPs and spine route reflectors. BGP sessions
   must remain in the ``established(6)`` state.
3. **Data-Plane Virtualization (VXLAN & VNIs)**: Audits the operational state
   of Network Virtualization Edge (NVE) interfaces, active VNI memberships, and
   encapsulation/decapsulation counters.

Key MIB Objects & OIDs
----------------------

Standard IETF and enterprise MIBs provide direct visibility into fabric health:

- **BGP4-MIB (RFC 4273)**:

  - ``bgpPeerState`` (``.1.3.6.1.2.1.15.3.1.2``): State of each BGP peer:
    ``idle(1)``, ``connect(2)``, ``active(3)``, ``opensent(4)``,
    ``openconfirm(5)``, or ``established(6)``.
  - ``bgpPeerAdminStatus`` (``.1.3.6.1.2.1.15.3.1.3``): Configured state
    (``stop(1)`` or ``start(2)``).
  - ``bgpPeerRemoteAs`` (``.1.3.6.1.2.1.15.3.1.9``): Remote autonomous system.
  - ``bgpPeerInUpdates`` / ``bgpPeerOutUpdates``: Route update message counters.

- **IF-MIB (RFC 2863)**:

  - ``ifDescr`` (``.1.3.6.1.2.1.2.2.1.2``): Interface name (e.g. ``Vxlan1`` or
    ``nve1``).
  - ``ifOperStatus`` (``.1.3.6.1.2.1.2.2.1.8``): Current operational state
    (``up(1)``, ``down(2)``, ``lowerLayerDown(7)``).
  - ``ifInErrors`` / ``ifOutErrors``: Interface packet error counters.

- **Enterprise VXLAN MIBs (e.g. ARISTA-VXLAN-MIB / CISCO-VXLAN-MIB)**:

  - ``aristaVxlanVniCountersTable`` (``.1.3.6.1.4.1.30065.3.28.1.2.1``):
    Tracks per-VNI encapsulation and decapsulation packet volumes.
  - ``aristaVxlanVtepCountersTable`` (``.1.3.6.1.4.1.30065.3.28.1.1.1``):
    Monitors tunnel health toward remote peer VTEPs.

Building the Fabric Auditor with ezsnmp
=======================================

Using ``ezsnmp.Session``, we can poll BGP sessions and VXLAN interface health
concurrently. By leveraging ``session.bulk_walk()`` with
``set_max_repeaters_to_num=25`` configured on the ``Session``, the script
executes table walks in bulk multi-OID PDU batches, avoiding serial latency:

.. code-block:: python

    from ezsnmp import Session
    from ezsnmp.exceptions import GenericError

    # Standard RFC MIB OIDs
    OID_BGP_PEER_STATE = "1.3.6.1.2.1.15.3.1.2"
    OID_BGP_PEER_ADMIN_STATUS = "1.3.6.1.2.1.15.3.1.3"
    OID_BGP_PEER_REMOTE_AS = "1.3.6.1.2.1.15.3.1.9"

    OID_IF_DESCR = "1.3.6.1.2.1.2.2.1.2"
    OID_IF_OPER_STATUS = "1.3.6.1.2.1.2.2.1.8"

    BGP_STATE_MAP = {
        "1": "IDLE",
        "2": "CONNECT",
        "3": "ACTIVE",
        "4": "OPENSENT",
        "5": "OPENCONFIRM",
        "6": "ESTABLISHED",
    }

    OPER_STATUS_MAP = {
        "1": "UP",
        "2": "DOWN",
        "3": "TESTING",
        "4": "UNKNOWN",
        "5": "DORMANT",
        "6": "NOT_PRESENT",
        "7": "LOWER_LAYER_DOWN",
    }


    def audit_evpn_vxlan_switch(host: str, community: str = "public"):
        session = Session(
            hostname=host,
            community=community,
            version=2,
            timeout=3,
            retries=1,
            set_max_repeaters_to_num=25,
            print_enums_numerically=True,
        )

        try:
            print(f"[*] Auditing EVPN-VXLAN fabric state on {host}...")

            # 1. Audit BGP EVPN Control-Plane Peers
            peer_states = session.bulk_walk(OID_BGP_PEER_STATE)
            peer_admins = session.bulk_walk(OID_BGP_PEER_ADMIN_STATUS)
            peer_remote_as = session.bulk_walk(OID_BGP_PEER_REMOTE_AS)

            admin_dict = {v.index: v.value for v in peer_admins}
            as_dict = {v.index: v.value for v in peer_remote_as}

            established_peers = 0
            degraded_peers = []

            for var in peer_states:
                peer_ip = var.index
                state_code = var.value
                admin_code = admin_dict.get(peer_ip, "2")
                rem_as = as_dict.get(peer_ip, "UNKNOWN")

                state_name = BGP_STATE_MAP.get(state_code, f"CODE_{state_code}")

                if state_code == "6":
                    established_peers += 1
                elif admin_code == "2":  # Admin Start but not Established
                    degraded_peers.append((peer_ip, rem_as, state_name))

            print(f"[+] Established BGP EVPN Peers: {established_peers}")
            if degraded_peers:
                print(f"[!] Warning: {len(degraded_peers)} degraded BGP peers:")
                for p_ip, r_as, state in degraded_peers:
                    print(f"    - Peer {p_ip} (AS {r_as}): State = {state}")

            # 2. Audit VXLAN Tunnel Interface (NVE / Vxlan1)
            if_descrs = session.bulk_walk(OID_IF_DESCR)
            if_opers = session.bulk_walk(OID_IF_OPER_STATUS)

            oper_dict = {v.index: v.value for v in if_opers}

            vxlan_interfaces_found = 0
            for var in if_descrs:
                name = var.value.lower()
                if "vxlan" in name or "nve" in name:
                    vxlan_interfaces_found += 1
                    oper_code = oper_dict.get(var.index, "4")
                    oper_name = OPER_STATUS_MAP.get(oper_code, f"CODE_{oper_code}")
                    print(
                        f"[+] VXLAN Interface '{var.value}' "
                        f"(Index {var.index}): Status = {oper_name}"
                    )

            if vxlan_interfaces_found == 0:
                print("[!] No active VXLAN/NVE interfaces found on device.")

        except GenericError as err:
            print(f"[-] SNMP telemetry query failed: {err}")


    if __name__ == "__main__":
        audit_evpn_vxlan_switch("127.0.0.1")

📥 `Download this script: audit_evpn_vxlan_switch.py <https://raw.githubusercontent.com/carlkidcrypto/carlkidcrypto.github.io/main/example_scripts/ezsnmp-bgp-evpn-vxlan-fabric-telemetry/audit_evpn_vxlan_switch.py>`_

Common Production EVPN-VXLAN Anomalies
======================================

When operating leaf-spine fabrics, telemetry alerts generally pinpoint three
frequent operational faults:

1. **BGP Stuck in ACTIVE or CONNECT**: The leaf switch cannot establish TCP port
   179 transport with the spine route reflector. Verify underlay routing
   reachability and MTU consistency on transit links.
2. **NVE Interface in LOWER_LAYER_DOWN**: The VXLAN virtual interface depends
   on its source loopback interface (e.g., Loopback0). If the underlay IGP drops
   the loopback route, the NVE interface transitions to down.
3. **VNI Asymmetric Packet Counters**: Inconsistent encapsulation versus
   decapsulation counters across paired leaf switches indicates asymmetric
   routing or an unadvertised Type 2 MAC-IP route.

Summary & What's Next
=====================

By auditing standard BGP-4 and interface MIBs with `ezsnmp
<https://github.com/carlkidcrypto/ezsnmp>`_, network engineering teams gain
real-time verification of EVPN-VXLAN datacenter fabrics, detecting control-plane
isolation and tunnel failures before tenant services are impacted.

In our next blog post, we will rotate to `purpleair_api
<https://github.com/carlkidcrypto/purpleair_api>`_, examining how to use the
Matter Device Converter submodule to transform PurpleAir telemetry into Matter
1.5.1 cluster schemas for export to smart home bridges.

----

.. warning::

   AI-generated content may contain misinformation or mistakes. A human does review this, but we are only human.

