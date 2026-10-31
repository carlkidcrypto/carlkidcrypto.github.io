.. meta::
   :description: Power over Ethernet (PoE) has evolved far beyond powering standard desk VoIP phones. In modern enterprise campus networks and smart facilities, edge...
   :keywords: Python, Snmp, Poe, Power-Over-Ethernet, Power-Ethernet-Mib, Ezsnmp, Python, ezsnmp, Networking, DevOps
   :author: Carlos Santos (@carlkidcrypto)
   :property=og:title: Auditing Enterprise PoE Budgets & Power Delivery with ezsnmp
   :property=og:description: Power over Ethernet (PoE) has evolved far beyond powering standard desk VoIP phones. In modern enterprise campus networks and smart facilities, edge...
   :property=og:type: article
   :property=og:url: https://carlkidcrypto.github.io/blog/ezsnmp-enterprise-poe-power-auditing.html
   :property=og:image: https://carlkidcrypto.github.io/_static/logo.png
   :name=twitter:card: summary
   :name=twitter:title: Auditing Enterprise PoE Budgets & Power Delivery with ezsnmp
   :name=twitter:description: Power over Ethernet (PoE) has evolved far beyond powering standard desk VoIP phones. In modern enterprise campus networks and smart facilities, edge...
   :name=twitter:image: https://carlkidcrypto.github.io/_static/logo.png

============================================================
Auditing Enterprise PoE Budgets & Power Delivery with ezsnmp
============================================================

.. note::

   * **Published:** November 2, 2026
   * **Authors:** Written by Gemini 3.8 Flash, Co-Authored & Reviewed by `Carlos Santos (@carlkidcrypto) <https://github.com/carlkidcrypto>`_
   * **Estimated Reading Time:** 5 minutes
   * **Tags:** `Python` • `Snmp` • `Poe` • `Power-Over-Ethernet` • `Power-Ethernet-Mib` • `Ezsnmp`

Why PoE Budget Auditing Is Critical
===================================

Power over Ethernet (PoE) has evolved far beyond powering standard desk VoIP
phones. In modern enterprise campus networks and smart facilities, edge
switches deliver DC power to high-wattage endpoints:

* **Wi-Fi 6E & Wi-Fi 7 Access Points**: Demanding 802.3at (PoE+, 30W) or
  802.3bt (PoE++, up to 60W or 90W) to power multi-gigabit radios.
* **Pan-Tilt-Zoom (PTZ) IP Cameras**: Drawing continuous heating and motor
  power in outdoor enclosures.
* **Smart Building IoT**: Powering smart LED fixtures, access control badge
  readers, and environmental sensors.

However, switch power supply units (PSUs) have finite wattage budgets (e.g.,
370W, 740W, or 1440W per chassis). When total connected demand exceeds the
budget:

* **Unscheduled Port Shedding**: Switches automatically cut power to ports,
  rebooting access points or security cameras.
* **Allocation vs Consumption Inefficiencies**: Switches often reserve
  maximum class budgets (30W for Class 4) even when endpoints consume only 8W,
  artificially blocking additional hardware from powering on.

`ezsnmp <https://github.com/carlkidcrypto/ezsnmp>`_ provides native Net-SNMP C
speed to query standard power MIBs, audit chassis PSU capacity, and inspect
per-port milliwatt consumption across hundreds of access switches in seconds.


The Anatomy of POWER-ETHERNET-MIB (RFC 3621)
============================================

The standard ``POWER-ETHERNET-MIB`` structures power management into chassis
controllers and port-level delivery tables:

1. Chassis Power Budget (pethMainPseTable)
------------------------------------------
Under ``pethMainPseTable`` (OID ``.1.3.6.1.2.1.105.1.3.1``):

* **``pethMainPsePower``**: Total nominal power supply capacity in Watts (e.g.
  ``740``).
* **``pethMainPseConsumptionPower``**: Real-time aggregate power measured in
  Watts currently drawn by all connected devices.
* **``pethMainPseOperStatus``**: PSU operational state: ``on(1)``, ``off(2)``,
  or ``faulty(3)``.
* **``pethMainPseUsageThreshold``**: User-defined warning threshold percentage
  (typically 80%).

2. Port-Level Power Delivery (pethPsePortTable)
-----------------------------------------------
Under ``pethPsePortTable`` (OID ``.1.3.6.1.2.1.105.1.1.1``):

* **``pethPsePortAdminEnable``**: Administrative state: ``true(1)`` or
  ``false(2)``.
* **``pethPsePortDetectionStatus``**: Operational port power state:

  - ``disabled(1)``: PoE administratively disabled.
  - ``searching(2)``: Port probing for valid IEEE 802.3 signature resistance.
  - ``deliveringPower(3)``: Device validated; DC power actively delivered.
  - ``fault(4)``: Short-circuit, overload, or hardware fault detected.

* **``pethPsePortPowerPriority``**: Shedding precedence: ``critical(1)``,
  ``high(2)``, or ``low(3)``.

3. Real-Time Milliwatt Draw (CISCO-POWER-ETHERNET-EXT-MIB)
----------------------------------------------------------
Vendor extensions like Cisco's ``cpeExtPsePortTable`` track precise wattage:

* **``cpeExtPsePortPwrAllocated``**: Power reserved by the switch in milliwatts.
* **``cpeExtPsePortPwrConsumed``**: Real-time power measured in milliwatts.


Practical Implementation: Enterprise PoE Auditor
================================================

Below is a complete script demonstrating how to audit chassis PSU headroom,
inspect port power delivery, and detect overloaded budgets via ezsnmp:

.. code-block:: python

    from ezsnmp import Session
    from ezsnmp.exceptions import EasySNMPError

    DETECTION_MAP = {
        1: "DISABLED",
        2: "SEARCHING",
        3: "DELIVERING_POWER",
        4: "FAULT",
        5: "TEST",
        6: "OTHER_FAULT",
    }

    PRIORITY_MAP = {1: "CRITICAL", 2: "HIGH", 3: "LOW"}

    def audit_switch_poe(hostname: str, community: str = "public"):
        session = Session(
            hostname=hostname,
            community=community,
            version=2,
            timeout=2,
            retries=1
        )

        try:
            # 1. Query Chassis Total Capacity and Current Consumption (Watts)
            total_power_vars = session.bulkwalk("pethMainPsePower")
            used_power_vars = session.bulkwalk("pethMainPseConsumptionPower")

            total_watts = sum(int(v.value) for v in total_power_vars)
            used_watts = sum(int(v.value) for v in used_power_vars)
            util_pct = (used_watts / total_watts * 100) if total_watts else 0

            # 2. Collect per-port PoE detection states and priorities
            status_vars = session.bulkwalk(
                "pethPsePortDetectionStatus", max_repetitions=25
            )
            prio_vars = session.bulkwalk(
                "pethPsePortPowerPriority", max_repetitions=25
            )
            draw_vars = session.bulkwalk(
                "cpeExtPsePortPwrConsumed", max_repetitions=25
            )

            prio_map = {v.oid_index: int(v.value) for v in prio_vars}
            draw_map = {v.oid_index: int(v.value) for v in draw_vars}

            active_ports = []
            for v in status_vars:
                idx = v.oid_index
                status_code = int(v.value)
                if status_code == 3:  # deliveringPower
                    draw_mw = draw_map.get(idx, 0)
                    draw_watts = draw_mw / 1000.0
                    prio_code = prio_map.get(idx, 3)

                    active_ports.append({
                        "port_index": idx,
                        "status": DETECTION_MAP.get(status_code, "UNKNOWN"),
                        "priority": PRIORITY_MAP.get(prio_code, "LOW"),
                        "watts": draw_watts,
                    })

            return {
                "total_watts": total_watts,
                "used_watts": used_watts,
                "util_pct": util_pct,
                "active_ports": active_ports,
            }

        except EasySNMPError as exc:
            print(f"[{hostname}] PoE audit failed: {exc}")
            return None

    if __name__ == "__main__":
        report = audit_switch_poe("access-sw01.internal")
        if report:
            used_w = report['used_watts']
            pct = report['util_pct']
            print("--- PoE Chassis Power Budget ---")
            print(f"  Total Capacity : {report['total_watts']} W")
            print(f"  Current Draw   : {used_w} W ({pct:.1f}%)")
            print(f"  Active PoE Ports: {len(report['active_ports'])}\n")

            print("--- Delivering Power Ports (Top Consumers) ---")
            top_ports = sorted(
                report["active_ports"],
                key=lambda x: x["watts"],
                reverse=True
            )[:5]
            for p in top_ports:
                print(
                    f"  Port {p['port_index']:<8} | "
                    f"Priority: {p['priority']:<8} | "
                    f"Draw: {p['watts']:>5.2f} W"
                )


Production Best Practices
=========================

* **Monitor Real-Time Consumption vs Allocation**: Reserve-based allocation
  can make a switch appear 95% full when actual draw is under 40%. Compare
  ``cpeExtPsePortPwrAllocated`` against ``cpeExtPsePortPwrConsumed`` before
  purchasing secondary power supplies.
* **Assign Power Priorities Explicitly**: Ensure mission-critical endpoints
  (badge readers, security cameras) are tagged as ``critical(1)``. In the event
  of an auxiliary PSU failure, the switch will shed ``low(3)`` priority desk
  phones first.
* **Automate Budget Exhaustion Alerts**: Configure threshold alerts when
  aggregate consumption exceeds 80% of nominal PSU capacity to account for
  AP boot-up inrush current.


Migration Notes: Easy SNMP vs ezsnmp
====================================

Legacy ``easysnmp`` struggled when querying high-density 48-port switch stacks:

* **Clean Thread Isolation in ezsnmp**: ``ezsnmp``'s C++17 session mutexes
  allow multi-threaded crawlers to audit hundreds of campus access switches
  concurrently without lock contention.
* **Robust Numeric Conversions**: Direct C-to-Python integer handling prevents
  milliwatt truncation when converting 32-bit unsigned power integers.


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
