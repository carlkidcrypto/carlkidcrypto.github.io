.. meta::
   :description: Even in modern routed-access campuses, Layer 2 switching loops and Topology Change Notification (TCN) storms remain among the most disruptive failure modes...
   :keywords: Ezsnmp, Python, Snmp, Stp, Rstp, Bridge-Mib, Networking, Telemetry, Python, ezsnmp, Networking, DevOps
   :author: Carlos Santos (@carlkidcrypto)
   :property=og:title: Auditing Spanning Tree (STP/RSTP) Stability with ezsnmp
   :property=og:description: Even in modern routed-access campuses, Layer 2 switching loops and Topology Change Notification (TCN) storms remain among the most disruptive failure modes...
   :property=og:type: article
   :property=og:url: https://carlkidcrypto.github.io/blog/ezsnmp-stp-rstp-topology-auditing.html
   :property=og:image: https://carlkidcrypto.github.io/_static/logo.png
   :name=twitter:card: summary
   :name=twitter:title: Auditing Spanning Tree (STP/RSTP) Stability with ezsnmp
   :name=twitter:description: Even in modern routed-access campuses, Layer 2 switching loops and Topology Change Notification (TCN) storms remain among the most disruptive failure modes...
   :name=twitter:image: https://carlkidcrypto.github.io/_static/logo.png

============================================================
Auditing Spanning Tree (STP/RSTP) Stability with ezsnmp
============================================================

.. note::

   * **Published:** November 25, 2026
   * **Authors:** Written by Gemini 3.8 Flash, Co-Authored & Reviewed by `Carlos Santos (@carlkidcrypto) <https://github.com/carlkidcrypto>`_
   * **Estimated Reading Time:** 7 minutes
   * **Tags:** `Ezsnmp` • `Python` • `Snmp` • `Stp` • `Rstp` • `Bridge-Mib` • `Networking` • `Telemetry`

Even in modern routed-access campuses, Layer 2 switching loops and Topology
Change Notification (TCN) storms remain among the most disruptive failure modes
in enterprise networks. When an unauthorized switch is plugged into an edge
jack, or an uplink flaps repeatedly, Rapid Spanning Tree Protocol (RSTP /
IEEE 802.1w) recalculates forwarding paths and flushes MAC address tables.

Left undetected, a rogue root bridge election forces traffic through
low-bandwidth access closets, while continuous TCN storms cause unicast flooding
across entire VLANs. Relying on manual ``show spanning-tree`` CLI checks across
dozens of wiring-closet switches does not scale.

Using `ezsnmp <https://github.com/carlkidcrypto/ezsnmp>`_, network engineers
can poll standardized ``BRIDGE-MIB`` (RFC 4188) scalars and port tables across
every switch in parallel, detecting root bridge drift, abnormal TCN rates, and
port role transitions within seconds.

In this tutorial, we will inspect the ``BRIDGE-MIB`` spanning tree object
model, decode 8-byte Bridge Identifiers cleanly, map bridge ports to ``IF-MIB``
interfaces, and build a process-isolated STP auditor using modern ``ezsnmp``
APIs.

Understanding BRIDGE-MIB (RFC 4188) Objects
===========================================

`BRIDGE-MIB <https://mibs.observium.org/mib/BRIDGE-MIB/>`_ exposes both
switch-wide spanning tree state and per-port forwarding metrics:

Bridge-Level Scalars
--------------------

Batch these five scalar objects in a single ``session.get([...])`` call:

- ``dot1dStpTimeSinceTopologyChange.0`` (``.1.3.6.1.2.1.17.2.3.0``):
  TimeTicks (in hundredths of a second) since the last TCN event was detected.
- ``dot1dStpTopChanges.0`` (``.1.3.6.1.2.1.17.2.4.0``):
  Cumulative ``Counter32`` of topology changes since the bridge initialized.
- ``dot1dStpDesignatedRoot.0`` (``.1.3.6.1.2.1.17.2.5.0``):
  8-octet Bridge Identifier of the current root bridge (2-byte priority +
  6-byte system MAC address).
- ``dot1dStpRootCost.0`` (``.1.3.6.1.2.1.17.2.6.0``):
  Cumulative path cost from this switch to the root bridge.
- ``dot1dStpRootPort.0`` (``.1.3.6.1.2.1.17.2.7.0``):
  Bridge port number pointing toward the root (``0`` if this switch *is* the
  root bridge).

Per-Port STP State & Bridge-to-IF Mapping
-----------------------------------------

Note that ``dot1dStpPortTable`` indexes ports by **bridge port number**, which
does not always match the ``IF-MIB`` ``ifIndex``. Always map bridge ports to
physical interface names via ``dot1dBasePortIfIndex`` and ``ifDescr``:

- ``dot1dBasePortIfIndex`` (``.1.3.6.1.2.1.17.1.4.1.2``): Maps ``dot1dBasePort``
  to ``ifIndex``.
- ``dot1dStpPortState`` (``.1.3.6.1.2.1.17.2.15.1.3``): Current port state:
  ``disabled(1)``, ``blocking(2)``, ``listening(3)``, ``learning(4)``,
  ``forwarding(5)``, or ``broken(6)``.
- ``dot1dStpPortForwardTransitions`` (``.1.3.6.1.2.1.17.2.15.1.10``): Count of
  times the port transitioned from learning to forwarding.

Building the STP/RSTP Fleet Auditor with ezsnmp
===============================================

Because Net-SNMP maintains process-global C state protected by internal
mutexes, auditing a large switch fleet should use
``concurrent.futures.ProcessPoolExecutor`` with an isolated ``ezsnmp.Session``
inside each worker process.

Remember these modern ``ezsnmp`` conventions:

1. Set ``set_max_repeaters_to_num=25`` and ``print_enums_numerically=True`` on
   ``Session(...)``—never pass ``max_repetitions`` to ``bulk_walk()``.
2. Access ``.index`` and ``.type`` on ``Result`` objects (never legacy
   ``.oid_index`` or ``.snmp_type``) and guard against ``NOSUCHOBJECT`` or
   ``NOSUCHINSTANCE``.
3. Decode ``Hex-STRING`` values via ``bytes.fromhex(val.replace(" ", ""))``
   rather than calling ``.encode("latin1")``.

Here is the complete STP/RSTP auditor:

.. code-block:: python

    from concurrent.futures import ProcessPoolExecutor, as_completed
    from typing import Any, Dict, List

    from ezsnmp import Session
    from ezsnmp.exceptions import ConnectionError, GenericError, TimeoutError

    OID_TIME_SINCE_TC = "1.3.6.1.2.1.17.2.3.0"
    OID_TOP_CHANGES = "1.3.6.1.2.1.17.2.4.0"
    OID_DESIGNATED_ROOT = "1.3.6.1.2.1.17.2.5.0"
    OID_ROOT_COST = "1.3.6.1.2.1.17.2.6.0"
    OID_ROOT_PORT = "1.3.6.1.2.1.17.2.7.0"

    OID_BASE_PORT_IFINDEX = "1.3.6.1.2.1.17.1.4.1.2"
    OID_STP_PORT_STATE = "1.3.6.1.2.1.17.2.15.1.3"
    OID_STP_FWD_TRANS = "1.3.6.1.2.1.17.2.15.1.10"
    OID_IF_DESCR = "1.3.6.1.2.1.2.2.1.2"

    STP_STATES = {
        1: "disabled",
        2: "blocking",
        3: "listening",
        4: "learning",
        5: "forwarding",
        6: "broken",
    }

    def safe_int(val: Any, default: int = 0) -> int:
        digits = "".join(c for c in str(val) if c.isdigit() or c == "-")
        return int(digits) if digits and digits != "-" else default

    def decode_bridge_id(raw_val: str) -> str:
        cleaned = raw_val.replace("Hex-STRING:", "").replace(":", " ").strip()
        hex_str = cleaned.replace(" ", "")
        if len(hex_str) == 16:
            raw_bytes = bytes.fromhex(hex_str)
            priority = int.from_bytes(raw_bytes[:2], "big")
            mac = ":".join(f"{b:02x}" for b in raw_bytes[2:])
            return f"{priority}/{mac}"
        return raw_val.strip()

    def audit_switch_stp(
        host: str, expected_root_mac: str, community: str = "public"
    ) -> Dict[str, Any]:
        session = Session(
            hostname=host,
            community=community,
            version=2,
            timeout=2,
            retries=1,
            set_max_repeaters_to_num=25,
            print_enums_numerically=True,
        )

        report: Dict[str, Any] = {"host": host, "alerts": []}

        try:
            # 1. Batch scalar STP lookups in one get() call
            scalars = session.get([
                OID_TIME_SINCE_TC,
                OID_TOP_CHANGES,
                OID_DESIGNATED_ROOT,
                OID_ROOT_COST,
                OID_ROOT_PORT,
            ])

            time_since_tc_cs = safe_int(scalars[0].value)
            top_changes = safe_int(scalars[1].value)
            root_id = decode_bridge_id(scalars[2].value)
            root_cost = safe_int(scalars[3].value)
            root_port = safe_int(scalars[4].value)

            report["root_id"] = root_id
            report["root_cost"] = root_cost
            report["root_port"] = root_port
            report["top_changes"] = top_changes

            if expected_root_mac.lower() not in root_id.lower():
                report["alerts"].append(
                    f"Unexpected STP Root Bridge: {root_id}"
                )

            if time_since_tc_cs < 30000:  # < 300 seconds
                secs = time_since_tc_cs / 100.0
                report["alerts"].append(
                    f"Recent topology change {secs:.1f}s ago "
                    f"(total={top_changes})"
                )

            # 2. Map bridge ports to IF-MIB interface names
            if_descrs = {
                v.index: v.value
                for v in session.bulk_walk(OID_IF_DESCR)
                if v.type not in ("NOSUCHOBJECT", "NOSUCHINSTANCE")
            }
            port_to_if = {
                v.index: str(safe_int(v.value))
                for v in session.bulk_walk(OID_BASE_PORT_IFINDEX)
                if v.type not in ("NOSUCHOBJECT", "NOSUCHINSTANCE")
            }

            # 3. Audit per-port states and forward transitions
            port_states = session.bulk_walk(OID_STP_PORT_STATE)
            fwd_trans = {
                v.index: safe_int(v.value)
                for v in session.bulk_walk(OID_STP_FWD_TRANS)
            }

            blocked_ports: List[str] = []
            for var in port_states:
                if var.type in ("NOSUCHOBJECT", "NOSUCHINSTANCE"):
                    continue
                bport = var.index
                state_code = safe_int(var.value)
                state_name = STP_STATES.get(state_code, f"state-{state_code}")
                if_idx = port_to_if.get(bport, bport)
                if_name = if_descrs.get(if_idx, f"port-{bport}")
                transitions = fwd_trans.get(bport, 0)

                if state_code == 6:  # broken
                    report["alerts"].append(f"{if_name} STP state BROKEN")
                elif state_code == 2:
                    blocked_ports.append(f"{if_name} (trans={transitions})")

            report["blocked_ports"] = blocked_ports

        except (TimeoutError, ConnectionError, GenericError) as err:
            report["alerts"].append(f"SNMP error: {err}")

        return report

    def audit_campus_fleet(
        hosts: List[str], expected_root_mac: str
    ) -> None:
        with ProcessPoolExecutor(max_workers=4) as pool:
            futures = {
                pool.submit(audit_switch_stp, h, expected_root_mac): h
                for h in hosts
            }
            for fut in as_completed(futures):
                res = fut.result()
                print(
                    f"[{res['host']}] Root={res.get('root_id')} "
                    f"TCs={res.get('top_changes')}"
                )
                for alert in res["alerts"]:
                    print(f"    [!] {alert}")

📥 `Download this script: audit_campus_fleet.py <https://raw.githubusercontent.com/carlkidcrypto/carlkidcrypto.github.io/main/example_scripts/ezsnmp-stp-rstp-topology-auditing/audit_campus_fleet.py>`_

Best Practices for Layer 2 Stability Monitoring
===============================================

1. **Correlate ``dot1dStpTopChanges`` Deltas**:

   - A single cumulative count of 500 topology changes means nothing if the
     switch has been up for 400 days. Track the per-minute delta across polls
     and alert immediately when ``delta(dot1dStpTopChanges) > 5`` in 5 minutes.

2. **Watch Edge Ports Without PortFast / Edge-Port**:

   - Access ports connected to workstations or printers that lack
     ``spanning-tree portfast`` (or RSTP ``adminEdge``) trigger a TCN every
     time a laptop sleeps or wakes. Rising ``dot1dStpPortForwardTransitions``
     pinpoints the exact offending edge interface.

3. **Combine ``BRIDGE-MIB`` with ``Q-BRIDGE-MIB`` for Per-VLAN STP**:

   - On platforms running Per-VLAN Spanning Tree (PVST+ / Rapid-PVST+),
     query SNMPv3 contexts (``context_name="vlan-10"``) or ``Q-BRIDGE-MIB``
     (``.1.3.6.1.2.1.17.7``) to audit root placement per VLAN rather than only
     the default native VLAN instance.

Summary & What's Next
=====================

Polling ``BRIDGE-MIB`` with `ezsnmp <https://github.com/carlkidcrypto/ezsnmp>`_
gives campus network teams fast, vendor-neutral visibility into root bridge
elections, TCN storms, and blocked redundancy links across the entire switching
fabric.

In our next blog post, we will rotate to `ezsnmp_data_logger
<https://github.com/carlkidcrypto/ezsnmp_data_logger>`_, exploring
high-throughput SNMP counter ingestion into TimescaleDB hypertables, handling
64-bit counter wraps, and building continuous bandwidth aggregates.

----

.. warning::

   AI-generated content may contain misinformation or mistakes. A human does
   review this, but we are only human.
