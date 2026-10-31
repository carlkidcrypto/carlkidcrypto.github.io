.. meta::
   :description: In modern high-speed data center fabrics and long-haul links (10G, 25G, 100G, and 400G), optical transceivers (SFP+, QSFP28, QSFP-DD) represent one of the...
   :keywords: Python, Snmp, Optical, Dom, Ddm, Hardware-Monitoring, Ezsnmp, Python, ezsnmp, Networking, DevOps
   :author: Carlos Santos (@carlkidcrypto)
   :property=og:title: Hardware Health & Optical Power Monitoring (DOM/DDM) in ezsnmp
   :property=og:description: In modern high-speed data center fabrics and long-haul links (10G, 25G, 100G, and 400G), optical transceivers (SFP+, QSFP28, QSFP-DD) represent one of the...
   :property=og:type: article
   :property=og:url: https://carlkidcrypto.github.io/blog/ezsnmp-hardware-optical-dom-monitoring.html
   :property=og:image: https://carlkidcrypto.github.io/_static/logo.png
   :name=twitter:card: summary
   :name=twitter:title: Hardware Health & Optical Power Monitoring (DOM/DDM) in ezsnmp
   :name=twitter:description: In modern high-speed data center fabrics and long-haul links (10G, 25G, 100G, and 400G), optical transceivers (SFP+, QSFP28, QSFP-DD) represent one of the...
   :name=twitter:image: https://carlkidcrypto.github.io/_static/logo.png

==============================================================
Hardware Health & Optical Power Monitoring (DOM/DDM) in ezsnmp
==============================================================

.. note::

   * **Published:** October 29, 2026
   * **Authors:** Written by Gemini 3.8 Flash, Co-Authored & Reviewed by `Carlos Santos (@carlkidcrypto) <https://github.com/carlkidcrypto>`_
   * **Estimated Reading Time:** 5 minutes
   * **Tags:** `Python` • `Snmp` • `Optical` • `Dom` • `Ddm` • `Hardware-Monitoring` • `Ezsnmp`

Why Optical Telemetry Matters Before Link Failure
=================================================

In modern high-speed data center fabrics and long-haul links (10G, 25G, 100G,
and 400G), optical transceivers (SFP+, QSFP28, QSFP-DD) represent one of the
most frequent sources of physical-layer degradation.

Long before an optical link officially reports an administrative down state,
fiber-optic paths exhibit measurable physical warning signs:

* **Dirty or Scratched Fiber Endfaces**: Attenuating receive (Rx) light levels.
* **Laser Diode Degradation**: Gradual decay in transmit (Tx) bias current.
* **Thermal Stress**: Overheating transceivers in dense switch chassis leading
  to bit-error rate (BER) spikes and Cyclic Redundancy Check (CRC) errors.

Digital Optical Monitoring (DOM), also standardized as Digital Diagnostic
Monitoring (DDM, SFF-8472), provides real-time internal diagnostic metrics
probed directly from the transceiver's internal microcontroller over I2C/MDIO.

`ezsnmp <https://github.com/carlkidcrypto/ezsnmp>`_ provides native Net-SNMP C
bindings to query standard hardware sensor MIBs, allowing engineers to audit
optical health across thousands of interfaces before packet loss occurs.


The ENTITY-SENSOR-MIB Architecture
==================================

The vendor-neutral standard for hardware telemetry is ``ENTITY-SENSOR-MIB``
(RFC 3433), which pairs with ``ENTITY-MIB`` (RFC 6933) to identify physical
components and their operational sensor values.

1. Mapping Physical Components (ENTITY-MIB)
-------------------------------------------
Under ``entPhysicalTable`` (OID ``.1.3.6.1.2.1.47.1.1.1``):

* **``entPhysicalName``**: Human-readable component name (e.g.,
  ``Ethernet1/1 Rx Power Sensor``).
* **``entPhysicalDescr``**: Detailed hardware description.

2. Sensor Telemetry (ENTITY-SENSOR-MIB)
---------------------------------------
Under ``entSensorValueTable`` (OID ``.1.3.6.1.2.1.99.1.1``):

* **``entSensorType``**: The physical measurement unit:
  - ``celsius(7)``: Temperature.
  - ``watts(6)``: Optical power in microWatts or milliWatts.
  - ``dBm(14)``: Optical decibels relative to one milliwatt.
* **``entSensorScale``**: Exponent scaling factor (e.g. ``milli(8)``,
  ``micro(7)``, ``units(9)``).
* **``entSensorPrecision``**: Number of decimal places in the raw value.
* **``entSensorValue``**: The raw signed integer sensor measurement.
* **``entSensorStatus``**: Operational state: ``ok(1)``, ``unavailable(2)``,
  ``nonoperational(3)``.


Calculating Real-World Sensor Values
====================================

Because SNMP transmits integer data types, physical measurements with decimal
precision are scaled. To reconstruct the true floating-point value:

.. code-block:: text

    True Value = (entSensorValue * 10^(entSensorScale - 9))
                 / (10^entSensorPrecision)

For example, a raw ``entSensorValue`` of ``-652`` with ``entSensorType=dBm(14)``
and ``entSensorPrecision=2`` translates to **-6.52 dBm**.


Practical Implementation: Optical Health Auditor
================================================

Below is a complete script using ezsnmp to discover optical transceivers,
query optical receive/transmit power, and evaluate link safety margins:

.. code-block:: python

    from ezsnmp import Session
    from ezsnmp.exceptions import EasySNMPError

    def audit_optical_sensors(hostname: str, community: str = "public"):
        session = Session(
            hostname=hostname,
            community=community,
            version=2,
            timeout=2,
            retries=1
        )

        try:
            # 1. Map physical sensor IDs to human-readable names
            name_vars = session.bulkwalk("entPhysicalName", max_repetitions=25)
            sensor_names = {v.oid_index: v.value for v in name_vars}

            # 2. Bulk-walk sensor telemetry columns
            type_vars = session.bulkwalk("entSensorType", max_repetitions=25)
            scale_vars = session.bulkwalk("entSensorScale", max_repetitions=25)
            prec_vars = session.bulkwalk(
                "entSensorPrecision", max_repetitions=25
            )
            val_vars = session.bulkwalk("entSensorValue", max_repetitions=25)
            status_vars = session.bulkwalk(
                "entSensorStatus", max_repetitions=25
            )

            scales = {v.oid_index: int(v.value) for v in scale_vars}
            precisions = {v.oid_index: int(v.value) for v in prec_vars}
            values = {v.oid_index: int(v.value) for v in val_vars}
            statuses = {v.oid_index: int(v.value) for v in status_vars}

            optical_report = []

            for v in type_vars:
                idx = v.oid_index
                sensor_type = int(v.value)
                name = sensor_names.get(idx, f"Sensor-{idx}")

                # Focus on optical power sensors (dBm = 14) and temperature (7)
                if sensor_type in (7, 14) and statuses.get(idx) == 1:
                    raw_val = values.get(idx, 0)
                    precision = precisions.get(idx, 0)

                    # Compute calibrated floating-point metric
                    calibrated = raw_val / (10 ** precision)
                    unit = "dBm" if sensor_type == 14 else "C"

                    # Flag dangerous optical signal attenuation
                    warning = False
                    is_rx_power = sensor_type == 14 and "Rx" in name
                    if is_rx_power and calibrated < -14.0:
                        warning = True

                    optical_report.append({
                        "sensor": name,
                        "value": calibrated,
                        "unit": unit,
                        "warning": warning
                    })

            return optical_report

        except EasySNMPError as exc:
            print(f"[{hostname}] Optical telemetry audit failed: {exc}")
            return []

    if __name__ == "__main__":
        telemetry = audit_optical_sensors("edge-leaf01.internal")
        print("--- Optical Diagnostic Monitoring Report ---")
        for item in telemetry:
            flag = " [LOW SIGNAL ALERT]" if item["warning"] else ""
            sensor = item["sensor"]
            val = item["value"]
            unit = item["unit"]
            print(f"  {sensor:<28} : {val:>6.2f} {unit}{flag}")


Production Best Practices
=========================

* **Do Not Over-Poll I2C Transceiver Buses**: Optical transceivers update
  internal analog-to-digital converters (ADCs) at slow rates (every 500ms to
  1000ms). Polling DOM sensors faster than every 30 to 60 seconds risks
  contention on the switch's internal I2C bus and can trigger linecard CPU
  spikes.
* **Correlate Rx Power with CRC Error Counters**: When an interface exhibits
  sporadic CRC errors, cross-reference receive optical power (``Rx Power``)
  against manufacturer optical sensitivity thresholds. Low Rx power (< -15 dBm
  on standard 10GBASE-SR) indicates fiber degradation.
* **Bulk Walk Optimization**: Physical sensor tables contain hundreds of
  rows. Utilize ``bulkwalk`` with ``max_repetitions=25`` to retrieve the entire
  sensor table in two round-trips.


Migration Notes: Easy SNMP vs ezsnmp
====================================

* **Signed Integer Preservations**: Receive optical power in dBm is
  inherently negative (e.g. ``-6.52 dBm``). Legacy ``easysnmp`` contained
  integer signedness bugs in Python 3 that occasionally unpacked negative
  values as massive unsigned 32-bit integers (e.g. ``4294966644``).
* **ezsnmp Type Fidelity**: ``ezsnmp``'s modernized C++17 type conversion layer
  correctly maps signed Net-SNMP ASN.1 integers into Python native signed
  integers, ensuring negative optical dBm metrics parse with 100% accuracy.


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
