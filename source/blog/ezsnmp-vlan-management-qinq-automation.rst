.. meta::
   :description: In enterprise campus environments, data center fabrics, and carrier Ethernet networks, Virtual Local Area Networks (VLANs, IEEE 802.1Q) partition physical...
   :keywords: Python, Snmp, Vlan, Q-In-Q, Q-Bridge-Mib, Ezsnmp, Network-Automation, Python, ezsnmp, Networking, DevOps
   :author: Carlos Santos (@carlkidcrypto)
   :property=og:title: Automating VLAN Management & Q-in-Q Tagging with ezsnmp
   :property=og:description: In enterprise campus environments, data center fabrics, and carrier Ethernet networks, Virtual Local Area Networks (VLANs, IEEE 802.1Q) partition physical...
   :property=og:type: article
   :property=og:url: https://carlkidcrypto.github.io/blog/ezsnmp-vlan-management-qinq-automation.html
   :property=og:image: https://carlkidcrypto.github.io/_static/logo.png
   :name=twitter:card: summary
   :name=twitter:title: Automating VLAN Management & Q-in-Q Tagging with ezsnmp
   :name=twitter:description: In enterprise campus environments, data center fabrics, and carrier Ethernet networks, Virtual Local Area Networks (VLANs, IEEE 802.1Q) partition physical...
   :name=twitter:image: https://carlkidcrypto.github.io/_static/logo.png

============================================================
Automating VLAN Management & Q-in-Q Tagging with ezsnmp
============================================================

.. note::

   * **Published:** October 26, 2026
   * **Authors:** Written by Gemini 3.8 Flash, Co-Authored & Reviewed by `Carlos Santos (@carlkidcrypto) <https://github.com/carlkidcrypto>`_
   * **Estimated Reading Time:** 5 minutes
   * **Tags:** `Python` • `Snmp` • `Vlan` • `Q-In-Q` • `Q-Bridge-Mib` • `Ezsnmp` • `Network-Automation`

The Complexity of Multi-Tenant Layer-2 Networks
===============================================

In enterprise campus environments, data center fabrics, and carrier Ethernet
networks, Virtual Local Area Networks (VLANs, IEEE 802.1Q) partition physical
switch infrastructure into isolated broadcast domains.

In service provider and multi-tenant scenarios, this architecture extends to
**Q-in-Q VLAN stacking (IEEE 802.1ad)**, where customer VLAN tags (C-VLANs) are
encapsulated within provider service tags (S-VLANs) to traverse transit trunks
without tag collisions.

Auditing and validating VLAN deployments across hundreds of switches presents
formidable operational hurdles:

* **Trunk Port Misconfigurations**: Forgetting to add newly provisioned VLANs
  to uplink trunk egress lists.
* **Native VLAN Mismatches**: Desynchronized Port Default VLAN IDs (PVIDs)
  causing spanning-tree loops and traffic leakage.
* **Bitmask Complexity**: Standard SNMP MIBs encode switch port allocations as
  binary octet bitmasks rather than plain integers or strings.

`ezsnmp <https://github.com/carlkidcrypto/ezsnmp>`_ provides native Net-SNMP C
bindings to query IEEE standard MIBs, parse raw binary bitmasks, and audit
complex Layer-2 configurations in fractions of a second.


Understanding the Q-BRIDGE-MIB & PortLists
==========================================

The standard ``Q-BRIDGE-MIB`` (RFC 4363) defines two primary tables for
VLAN inspection:

1. ``dot1qPortVlanTable`` (OID ``.1.3.6.1.2.1.17.7.1.4.5``)
-----------------------------------------------------------
Maintains per-port ingress parameters:

* **``dot1qPvid``**: The Port Default VLAN ID. Incoming untagged or priority-
  tagged frames are assigned this VLAN ID.
* **``dot1qPortAcceptableFrameTypes``**: Determines whether a port admits all
  frames (access/hybrid) or strictly tagged frames (trunk).

2. ``dot1qVlanCurrentTable`` (OID ``.1.3.6.1.2.1.17.7.1.4.2``)
--------------------------------------------------------------
Maintains active VLAN membership using binary ``PortList`` octet strings:

* **``dot1qVlanCurrentEgressPorts``**: Binary bitmask indicating which switch
  ports are authorized to transmit frames for the given VLAN.
* **``dot1qVlanCurrentUntaggedPorts``**: Binary bitmask indicating ports where
  egressing frames strip their 802.1Q tag (access ports).

Decoding a PortList Bitmask
---------------------------
In a ``PortList``, each bit represents a bridge port number. The most
significant bit (bit 7) of the first byte represents Port 1; bit 6 represents
Port 2, continuing sequentially through all switch ports.


Practical Implementation: VLAN Auditor & Decoder
================================================

Below is a complete script demonstrating how to query ``Q-BRIDGE-MIB`` via
ezsnmp, decode binary port bitmasks, and construct a comprehensive VLAN
allocation report:

.. code-block:: python

    from ezsnmp import Session
    from ezsnmp.exceptions import GenericError

    def decode_port_bitmask(raw_bytes: bytes) -> list[int]:
        """Decode an SNMP PortList octet string into active port numbers."""
        active_ports = []
        for byte_idx, byte_val in enumerate(raw_bytes):
            for bit_idx in range(8):
                # Check bits from MSB (0x80) to LSB (0x01)
                if byte_val & (0x80 >> bit_idx):
                    port_num = (byte_idx * 8) + bit_idx + 1
                    active_ports.append(port_num)
        return active_ports

    def audit_switch_vlans(hostname: str, community: str = "public"):
        session = Session(
            hostname=hostname,
            community=community,
            version=2,
            timeout=2,
            retries=1
        )

        try:
            # 1. Collect Port Default VLAN IDs (Native VLANs)
            pvid_vars = session.bulk_walk("dot1qPvid", max_repetitions=25)
            pvids = {v.index: v.value for v in pvid_vars}

            # 2. Bulk-walk VLAN Egress and Untagged bitmasks
            egress_vars = session.bulk_walk(
                "dot1qVlanCurrentEgressPorts", max_repetitions=25
            )
            untagged_vars = session.bulk_walk(
                "dot1qVlanCurrentUntaggedPorts", max_repetitions=25
            )

            untagged_map = {
                v.index: set(decode_port_bitmask(v.value.encode("latin1")))
                for v in untagged_vars
            }

            vlan_report = []

            for var in egress_vars:
                # OID format: [time_filter].[vlan_id]
                vlan_id = var.index.split(".")[-1]
                raw_bytes = var.value.encode("latin1")
                egress_ports = decode_port_bitmask(raw_bytes)
                untagged_ports = untagged_map.get(var.index, set())

                tagged_ports = [
                    p for p in egress_ports if p not in untagged_ports
                ]

                vlan_report.append({
                    "vlan_id": vlan_id,
                    "tagged_ports": tagged_ports,
                    "untagged_ports": list(untagged_ports),
                })

            return pvids, vlan_report

        except GenericError as err:
            print(f"[{hostname}] VLAN audit failed: {err}")
            return {}, []

    if __name__ == "__main__":
        pvids, vlans = audit_switch_vlans("dist-sw01.internal")

        print("--- Port Native VLANs (PVID) ---")
        for port, pvid in sorted(pvids.items(), key=lambda x: int(x[0])):
            print(f"  Port {port:>2}: Native VLAN {pvid}")

        print("\n--- VLAN Membership Matrix ---")
        for v in vlans:
            tagged = ",".join(map(str, v["tagged_ports"])) or "None"
            untagged = ",".join(map(str, v["untagged_ports"])) or "None"
            print(
                f"  VLAN {v['vlan_id']:>4} | "
                f"Tagged: [{tagged}] | Untagged: [{untagged}]"
            )


Inspecting Q-in-Q (VLAN Stacking) Configurations
================================================

In provider edge (PE) and carrier Ethernet switches, ports configured for
Q-in-Q tunneling encapsulate all incoming customer traffic inside a service
tag (S-VLAN).

1. Tunnel Port Verification
---------------------------
Verify that the customer-facing port has ``dot1qPortAcceptableFrameTypes`` set
to ``admitAll`` (admitting untagged and single-tagged frames).

2. S-VLAN Egress Validation
---------------------------
Ensure uplink trunk interfaces belong to the S-VLAN's
``dot1qVlanCurrentEgressPorts`` mask in tagged mode, guaranteeing the outer
provider tag is preserved across core hops.


Production Best Practices
=========================

* **Safe Binary Handling with latin1**: Because SNMP ``PortList`` bitmasks
  can contain arbitrary null bytes (``\x00``), always handle raw values with
  binary-safe encoding (like ``latin1``) to prevent null-byte truncation.
* **Correlate with ifDescr**: Use ``dot1dBasePortIfIndex`` to map internal
  bridge port numbers back to physical interface names (e.g.
  ``TenGigabitEthernet1/0/1``).
* **Automate Misconfiguration Audits**: Flag trunk ports where PVIDs do not
  match between peer endpoints to catch spanning-tree desynchronizations.


Migration Notes: Easy SNMP vs ezsnmp
====================================

Legacy ``easysnmp`` had serious bugs with binary OCTET STRING decoding in
Python 3:

* **Null-Byte Truncation**: When a ``PortList`` bitmask contained null bytes
  (common when early ports on a linecard are inactive), legacy C code treated
  ``\x00`` as an ASCII string terminator, corrupting the bitmask.
* **Binary Integrity in ezsnmp**: ``ezsnmp``'s modernized C++17 layer preserves
  raw binary payload lengths explicitly, ensuring complete 512-bit port
  bitmasks are transferred into Python with 100% fidelity.


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
