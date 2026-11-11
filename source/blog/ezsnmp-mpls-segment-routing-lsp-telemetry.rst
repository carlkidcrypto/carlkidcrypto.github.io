.. meta::
   :description: Modern enterprise campus backbones, wide-area networks (WAN), and service provider backbones rely on Multiprotocol Label Switching (MPLS) and Segment...
   :keywords: Ezsnmp, Python, Snmp, Mpls, Segment-Routing, Networking, Telemetry, Python, ezsnmp, Networking, DevOps
   :author: Carlos Santos (@carlkidcrypto)
   :property=og:title: MPLS & Segment Routing LSP Telemetry: Label Switched Path Auditing with ezsnmp
   :property=og:description: Modern enterprise campus backbones, wide-area networks (WAN), and service provider backbones rely on Multiprotocol Label Switching (MPLS) and Segment...
   :property=og:type: article
   :property=og:url: https://carlkidcrypto.github.io/blog/ezsnmp-mpls-segment-routing-lsp-telemetry.html
   :property=og:image: https://carlkidcrypto.github.io/_static/logo.png
   :name=twitter:card: summary
   :name=twitter:title: MPLS & Segment Routing LSP Telemetry: Label Switched Path Auditing with ezsnmp
   :name=twitter:description: Modern enterprise campus backbones, wide-area networks (WAN), and service provider backbones rely on Multiprotocol Label Switching (MPLS) and Segment...
   :name=twitter:image: https://carlkidcrypto.github.io/_static/logo.png

==============================================================================
MPLS & Segment Routing LSP Telemetry: Label Switched Path Auditing with ezsnmp
==============================================================================

.. note::

   * **Published:** November 7, 2026
   * **Authors:** Written by Gemini 3.8 Flash, Co-Authored & Reviewed by `Carlos Santos (@carlkidcrypto) <https://github.com/carlkidcrypto>`_
   * **Estimated Reading Time:** 5 minutes
   * **Tags:** `Ezsnmp` • `Python` • `Snmp` • `Mpls` • `Segment-Routing` • `Networking` • `Telemetry`

Modern enterprise campus backbones, wide-area networks (WAN), and service
provider backbones rely on Multiprotocol Label Switching (MPLS) and Segment
Routing over MPLS (SR-MPLS) to engineer traffic, provide deterministic Quality
of Service (QoS), and isolate tenant overlays via VPNs.

In a label-switched network, forwarding decisions do not inspect packet IP
headers hop-by-hop. Instead, packets travel along pre-established Label Switched
Paths (LSPs). At each Label Switching Router (LSR), the incoming label index is
swapped, pushed, or popped using the hardware Label Forwarding Information Base
(LFIB).

When an LSP breaks—whether due to an interior gateway protocol (IGP) metric
shift, hardware interface failure, or RSVP-TE signaling timeout—traffic can
silently drop or fail over to suboptimal non-engineered paths. Continuous
operational telemetry of LSP cross-connects and tunnel interfaces is critical.

The `ezsnmp <https://github.com/carlkidcrypto/ezsnmp>`_ library provides native
C/C++17 bindings directly to Net-SNMP, enabling network automation engineers to
audit hundreds of active LSPs across core routers in milliseconds.

In this tutorial, we will explore the standard MIB architecture for MPLS and
Segment Routing, inspect the LFIB cross-connect tables, and build a high-speed
LSP telemetry auditor using ``ezsnmp``.

The MIB Architecture for MPLS & Segment Routing
===============================================

The IETF standardized MPLS telemetry across several foundational MIBs:

- **MPLS-LSR-STD-MIB (RFC 3811 / RFC 3813)**: Models the Label Switching
  Router's internal LFIB, tracking incoming label segments, outgoing label
  segments, and cross-connect relationships.
- **MPLS-TE-STD-MIB (RFC 3812)**: Models signaled and static traffic
  engineering tunnels, tracking tunnel ingress, egress, administrative state,
  operational status, and forwarding metrics.

Key LFIB Managed Objects
------------------------

Under the ``MPLS-LSR-STD-MIB`` (OID ``.1.3.6.1.2.1.10.166.2``), three tables
reconcile label forwarding:

1. ``mplsInSegmentTable`` (``.1.3.6.1.2.1.10.166.2.1.4``):
   Maintains incoming label segments at an LSR, including
   ``mplsInSegmentLabel``, ``mplsInSegmentAdminStatus``, and
   ``mplsInSegmentOperStatus``.
2. ``mplsOutSegmentTable`` (``.1.3.6.1.2.1.10.166.2.1.7``):
   Maintains outgoing label segments, including next-hop interface, push/swap
   labels, and operational forwarding health.
3. ``mplsXCTable`` (``.1.3.6.1.2.1.10.166.2.1.10``):
   The Cross-Connect (XC) table. It binds an ``in-segment`` to one or more
   ``out-segments``, defining the true switching path across the router plane.
   The primary health indicator is ``mplsXCOperStatus``:
   - ``up(1)``: Cross-connect is fully active and passing packets.
   - ``down(2)``: Path is administratively up but operationally halted.
   - ``testing(3)``: Segment undergoing loopback or OAM verification.
   - ``unknown(4)``: Forwarding status indeterminate.
   - ``dormant(5)``: Standby secondary or fast-reroute path.
   - ``lowerLayerDown(7)``: Outgoing physical interface or transport link down.

Traffic Engineering & Segment Routing Tunnels
---------------------------------------------

Under ``MPLS-TE-STD-MIB`` (OID ``.1.3.6.1.2.1.10.166.3``), the
``mplsTunnelTable`` (``.1.3.6.1.2.1.10.166.3.2.2``) represents the end-to-end
LSP perspective:

- ``mplsTunnelName``: Configured textual identifier (e.g. ``tun-sea-ord-te01``).
- ``mplsTunnelIngressLSRId`` / ``mplsTunnelEgressLSRId``: 32-bit router IDs
  defining tunnel endpoints.
- ``mplsTunnelAdminStatus`` / ``mplsTunnelOperStatus``: Operational state of the
  tunnel interface.
- ``mplsTunnelOctets`` / ``mplsTunnelPackets``: Counter metrics tracking volume
  transported across the path.

In Segment Routing (SR-MPLS), tunnels operate as source-routed paths composed of
Prefix-SIDs (node segments) and Adjacency-SIDs. Modern network operating systems
(such as Cisco IOS-XR, Arista EOS, and Juniper Junos) expose SR-TE policies and
SR-MPLS paths directly through standard ``mplsTunnelTable`` and ``mplsXCTable``
hierarchies.

Building the LSP Telemetry Auditor
==================================

When querying routing tables with thousands of label entries, issuing serial
``snmpget`` queries introduces severe latency. With ``ezsnmp``, we utilize
``session.bulkwalk()`` to retrieve dense table columns in multi-OID PDU
batches:

.. code-block:: python

    from ezsnmp import Session
    from ezsnmp.exceptions import GenericError

    # Standard RFC 3811 / RFC 3812 MIB OIDs
    OID_MPLS_XC_OPER_STATUS = "1.3.6.1.2.1.10.166.2.1.10.1.7"
    OID_MPLS_XC_ADMIN_STATUS = "1.3.6.1.2.1.10.166.2.1.10.1.6"
    OID_MPLS_TUNNEL_NAME = "1.3.6.1.2.1.10.166.3.2.2.1.6"
    OID_MPLS_TUNNEL_OPER_STATUS = "1.3.6.1.2.1.10.166.3.2.2.1.5"

    XC_STATUS_MAP = {
        "1": "UP",
        "2": "DOWN",
        "3": "TESTING",
        "4": "UNKNOWN",
        "5": "DORMANT",
        "6": "NOT_PRESENT",
        "7": "LOWER_LAYER_DOWN",
    }

    TUNNEL_STATUS_MAP = {
        "1": "UP",
        "2": "DOWN",
        "3": "TESTING",
        "4": "UNKNOWN",
        "5": "DORMANT",
        "6": "NOT_PRESENT",
        "7": "LOWER_LAYER_DOWN",
    }

    def audit_mpls_telemetry(host: str, community: str = "public"):
        session = Session(
            hostname=host,
            community=community,
            version=2,
            timeout=3,
            retries=1
        )

        try:
            print(f"[*] Auditing MPLS and SR-TE state on {host}...")

            # 1. Audit MPLS Cross-Connect Forwarding Plane
            xc_oper_vars = session.bulk_walk(
                OID_MPLS_XC_OPER_STATUS,
                max_repetitions=25
            )
            xc_admin_vars = session.bulk_walk(
                OID_MPLS_XC_ADMIN_STATUS,
                max_repetitions=25
            )

            admin_status_dict = {
                var.index: var.value for var in xc_admin_vars
            }

            active_xc_count = 0
            degraded_xc_list = []

            for var in xc_oper_vars:
                index = var.index
                oper_code = var.value
                admin_code = admin_status_dict.get(index, "1")

                oper_desc = XC_STATUS_MAP.get(oper_code, f"CODE_{oper_code}")

                if oper_code == "1":
                    active_xc_count += 1
                elif admin_code == "1":  # Admin UP but Oper DOWN
                    degraded_xc_list.append((index, oper_desc))

            print(f"[+] Total Active Cross-Connects: {active_xc_count}")
            if degraded_xc_list:
                print(f"[!] Warning: {len(degraded_xc_list)} degraded XCs:")
                for idx, status in degraded_xc_list:
                    print(f"    - XC Index {idx}: Operational Status {status}")

            # 2. Audit Traffic Engineering & Segment Routing Tunnels
            tunnel_names = session.bulk_walk(
                OID_MPLS_TUNNEL_NAME,
                max_repetitions=25
            )
            tunnel_status = session.bulk_walk(
                OID_MPLS_TUNNEL_OPER_STATUS,
                max_repetitions=25
            )

            status_dict = {
                var.index: var.value for var in tunnel_status
            }

            print(f"[+] Discovered {len(tunnel_names)} MPLS/SR Tunnels:")
            for var in tunnel_names:
                idx = var.index
                name = var.value
                t_oper = status_dict.get(idx, "4")
                t_desc = TUNNEL_STATUS_MAP.get(t_oper, f"CODE_{t_oper}")
                print(f"    - Tunnel: {name:<24} State: {t_desc}")

        except GenericError as err:
            print(f"[-] SNMP telemetry query failed: {err}")

Automating Fast-Reroute (FRR) Verification
==========================================

In mission-critical backbones, LSPs are provisioned with Fast-Reroute (FRR)
backup paths. Under normal operating conditions, the primary cross-connect is
``UP(1)`` while the backup path reports as ``DORMANT(5)``.

If an auditor observes that a backup cross-connect transitions to ``UP(1)``
without administrative reconfiguration, it indicates that local link protection
has engaged due to an underlying optical fiber cut or interface flap. Capturing
this transition in your monitoring stack allows engineering teams to repair
underlying physical paths before second-order failures exhaust backup capacity.

Summary & What's Next
=====================

By auditing standard ``MPLS-LSR-STD-MIB`` and ``MPLS-TE-STD-MIB`` objects with
`ezsnmp <https://github.com/carlkidcrypto/ezsnmp>`_, network operations teams
gain deterministic visibility into label switching fabric health, detecting
silent path drops and routing anomalies before user traffic is disrupted.

In our next blog post, we will rotate back to `purpleair_api
<https://github.com/carlkidcrypto/purpleair_api>`_, exploring how to conduct
historical sensor data extraction and bounding-box queries for regional air
quality studies.

----

.. warning::

   AI-generated content may contain misinformation or mistakes. A human does review this, but we are only human.

