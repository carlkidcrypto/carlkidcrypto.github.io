.. meta::
   :description: Modern NetDevOps workflows center on a digital Source of Truth (SoT) such as **NetBox** or **Nautobot**. These platforms define the intended state of device...
   :keywords: Python, Snmp, Netbox, Nautobot, Netdevops, Ezsnmp, Inventory, Python, ezsnmp, Networking, DevOps
   :author: Carlos Santos (@carlkidcrypto)
   :property=og:title: Dynamic Inventory Sync: Populating NetBox & Nautobot via ezsnmp
   :property=og:description: Modern NetDevOps workflows center on a digital Source of Truth (SoT) such as **NetBox** or **Nautobot**. These platforms define the intended state of device...
   :property=og:type: article
   :property=og:url: https://carlkidcrypto.github.io/blog/ezsnmp-dynamic-inventory-sync-netbox.html
   :property=og:image: https://carlkidcrypto.github.io/_static/logo.png
   :name=twitter:card: summary
   :name=twitter:title: Dynamic Inventory Sync: Populating NetBox & Nautobot via ezsnmp
   :name=twitter:description: Modern NetDevOps workflows center on a digital Source of Truth (SoT) such as **NetBox** or **Nautobot**. These platforms define the intended state of device...
   :name=twitter:image: https://carlkidcrypto.github.io/_static/logo.png

===============================================================
Dynamic Inventory Sync: Populating NetBox & Nautobot via ezsnmp
===============================================================

.. note::

   * **Published:** October 31, 2026
   * **Authors:** Written by Gemini 3.8 Flash, Co-Authored & Reviewed by `Carlos Santos (@carlkidcrypto) <https://github.com/carlkidcrypto>`_
   * **Estimated Reading Time:** 5 minutes
   * **Tags:** `Python` • `Snmp` • `Netbox` • `Nautobot` • `Netdevops` • `Ezsnmp` • `Inventory`

The Challenge of Operational Drift in Source of Truth
=====================================================

Modern NetDevOps workflows center on a digital Source of Truth (SoT) such as
**NetBox** or **Nautobot**. These platforms define the intended state of
device hardware, interface configurations, IP allocations, and serial numbers.

However, operational reality frequently drifts from documented intent:

* **Hardware RMAs**: Failed switches or linecards replaced during outages
  without updated serial numbers in the inventory database.
* **Transceiver Moves**: SFP+ and QSFP modules swapped between ports, altering
  interface speeds and optical capabilities.
* **Firmware Maintenance**: Operating systems patched during maintenance
  windows without synchronizing version records.

Auditing this operational state via SSH screen-scraping (Netmiko/Scrapli) or
heavy vendor REST APIs across thousands of switches requires privileged
credentials, strains switch control-plane CPUs, and takes hours to complete.

`ezsnmp <https://github.com/carlkidcrypto/ezsnmp>`_ provides an ultra-fast,
read-only discovery engine. By querying standard MIBs over SNMP, automation
pipelines can extract serial numbers, interface MACs, and firmware versions
across an entire data center in minutes, reconciling SoT drift with zero CLI
overhead.


The Hardware Discovery MIB Architecture
=======================================

Two standard IETF MIBs provide complete hardware and operational inventory:

1. ENTITY-MIB (RFC 6933)
-------------------------
The ``entPhysicalTable`` (OID ``.1.3.6.1.2.1.47.1.1.1``) catalogs physical
components within a device chassis:

* **``entPhysicalClass``**: Component category: ``chassis(3)``, ``module(9)``,
  ``port(10)``, ``powerSupply(6)``, or ``fan(7)``.
* **``entPhysicalName``**: Component label (e.g. ``Chassis`` or ``Slot 1``).
* **``entPhysicalModelName``**: Exact vendor hardware part number.
* **``entPhysicalSerialNum``**: Factory hardware serial number.
* **``entPhysicalSoftwareRev``**: Installed operating system or firmware.

2. IF-MIB (RFC 2863)
--------------------
The ``ifXTable`` tracks physical interface parameters:

* **``ifName``**: Canonical port name (e.g. ``HundredGigE1/0/1``).
* **``ifPhysAddress``**: Hardware MAC address (binary octet string).
* **``ifHighSpeed``**: Interface speed in Megabits per second (Mbps).
* **``ifMtu``**: Configured Maximum Transmission Unit size.


Practical Implementation: NetBox Reconciliation Script
======================================================

Below is a complete script demonstrating how to collect hardware identity via
ezsnmp, query NetBox via ``pynetbox``, and detect configuration drift:

.. code-block:: python

    import pynetbox
    from ezsnmp import Session
    from ezsnmp.exceptions import GenericError

    NETBOX_URL = "https://netbox.internal.net"
    NETBOX_TOKEN = "0123456789abcdef0123456789abcdef01234567"

    def discover_device_inventory(
        hostname: str, community: str = "public"
    ) -> dict:
        """Extract chassis serial and interfaces via ezsnmp."""
        session = Session(
            hostname=hostname,
            community=community,
            version=2,
            timeout=2,
            retries=1
        )

        try:
            # 1. Query system metadata
            sys_name = session.get("sysName.0").value
            sys_descr = session.get("sysDescr.0").value

            # 2. Extract Chassis Serial from ENTITY-MIB
            class_vars = session.bulk_walk(
                "entPhysicalClass", max_repetitions=25
            )
            serial_vars = session.bulk_walk(
                "entPhysicalSerialNum", max_repetitions=25
            )
            name_vars = session.bulk_walk("entPhysicalName", max_repetitions=25)

            serials = {v.index: v.value for v in serial_vars}
            names = {v.index: v.value for v in name_vars}

            chassis_serial = "UNKNOWN"
            for var in class_vars:
                # Class 3 = chassis
                if var.value == "3":
                    chassis_serial = serials.get(var.index, "UNKNOWN")
                    break

            # 3. Collect interface MAC addresses from IF-MIB
            if_names = session.bulk_walk("ifName", max_repetitions=25)
            if_macs = session.bulk_walk("ifPhysAddress", max_repetitions=25)
            mac_map = {
                v.index: ":".join(
                    f"{b:02x}" for b in v.value.encode("latin1")
                )
                for v in if_macs if len(v.value) == 6
            }

            interfaces = {
                v.value: mac_map.get(v.index, "")
                for v in if_names if v.index in mac_map
            }

            return {
                "hostname": sys_name,
                "serial": chassis_serial,
                "description": sys_descr,
                "interfaces": interfaces
            }

        except GenericError as exc:
            print(f"[{hostname}] Discovery failed: {exc}")
            return {}

    def reconcile_with_netbox(discovered: dict):
        """Compare operational reality against NetBox Source of Truth."""
        nb = pynetbox.api(NETBOX_URL, token=NETBOX_TOKEN)
        device = nb.dcim.devices.get(name=discovered["hostname"])

        if not device:
            print(f"Device {discovered['hostname']} not found in NetBox!")
            return

        print(f"\n--- Audit Report: {device.name} ---")

        # Serial number drift detection
        if device.serial != discovered["serial"]:
            print(
                f"  [DRIFT DETECTED] Serial mismatch!\n"
                f"    NetBox Intent : {device.serial}\n"
                f"    Actual Switch : {discovered['serial']}"
            )
            # Reconcile serial if authorized
            # device.serial = discovered["serial"]
            # device.save()
        else:
            print(f"  [OK] Serial number matches: {device.serial}")

    if __name__ == "__main__":
        inv = discover_device_inventory("edge-leaf01.internal")
        if inv:
            reconcile_with_netbox(inv)


Production Best Practices
=========================

* **Dry-Run Audit Before Writing**: Never blindly overwrite Source of Truth
  records during discovery. Always generate a structured diff and route changes
  through an approval workflow or review gate.
* **Filter Chassis from Components**: Switches report dozens of physical
  serials (power supplies, fan trays, transceivers). Always check that
  ``entPhysicalClass == 3`` to identify the root chassis serial.
* **Binary Safe MAC Parsing**: Physical interface MAC addresses in
  ``ifPhysAddress`` are returned as raw 6-byte octet strings. Encode with
  ``latin1`` and format with ``f"{b:02x}"`` to construct standardized colon-
  separated MAC strings.


Migration Notes: Easy SNMP vs ezsnmp
====================================

* **Thread-Safe Multi-Device Crawling**: Discovery pipelines poll hundreds
  of switches in parallel. Legacy ``easysnmp`` crashed with mutex deadlocks
  under heavy Python multi-threading. ``ezsnmp``'s C++17 session locking
  guarantees clean, concurrent execution across thread pools.
* **Binary Octet String Preservation**: Correctly handles raw binary
  strings in ``ifPhysAddress`` without truncation or encoding faults.


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
