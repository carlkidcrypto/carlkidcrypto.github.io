.. meta::
   :description: High-speed datacenter spine uplinks and metro fiber rings depend on pluggable optical transceivers—such as SFP+, SFP28, QSFP28, and QSFP-DD modules. Before...
   :keywords: Ezsnmp, Python, Snmp, Optics, Dom, Ddm, Networking, Telemetry, Python, ezsnmp, Networking, DevOps
   :author: Carlos Santos (@carlkidcrypto)
   :property=og:title: Monitoring Hardware Transceiver Optical Power (DOM/DDM) with ezsnmp
   :property=og:description: High-speed datacenter spine uplinks and metro fiber rings depend on pluggable optical transceivers—such as SFP+, SFP28, QSFP28, and QSFP-DD modules. Before...
   :property=og:type: article
   :property=og:url: https://carlkidcrypto.github.io/blog/ezsnmp-transceiver-optical-power-dom-telemetry.html
   :property=og:image: https://carlkidcrypto.github.io/_static/logo.png
   :name=twitter:card: summary
   :name=twitter:title: Monitoring Hardware Transceiver Optical Power (DOM/DDM) with ezsnmp
   :name=twitter:description: High-speed datacenter spine uplinks and metro fiber rings depend on pluggable optical transceivers—such as SFP+, SFP28, QSFP28, and QSFP-DD modules. Before...
   :name=twitter:image: https://carlkidcrypto.github.io/_static/logo.png

===================================================================
Monitoring Hardware Transceiver Optical Power (DOM/DDM) with ezsnmp
===================================================================

.. note::

   * **Published:** November 19, 2026
   * **Authors:** Written by Gemini 3.8 Flash, Co-Authored & Reviewed by `Carlos Santos (@carlkidcrypto) <https://github.com/carlkidcrypto>`_
   * **Estimated Reading Time:** 5 minutes
   * **Tags:** `Ezsnmp` • `Python` • `Snmp` • `Optics` • `Dom` • `Ddm` • `Networking` • `Telemetry`

High-speed datacenter spine uplinks and metro fiber rings depend on pluggable
optical transceivers—such as SFP+, SFP28, QSFP28, and QSFP-DD modules. Before
an optical fiber link drops completely, failing lasers, dirty fiber end-faces,
or macro-bending attenuation typically cause gradual signal degradation.

Modern transceivers expose Digital Optical Monitoring (DOM), also known as
Digital Diagnostic Monitoring (DDM), providing real-time measurements of
receive (Rx) optical power, transmit (Tx) optical power, laser bias current,
supply voltage, and module temperature.

By polling standardized `ENTITY-SENSOR-MIB
<https://mibs.observium.org/mib/ENTITY-SENSOR-MIB/>`_ (RFC 3433) and
`ENTITY-MIB <https://mibs.observium.org/mib/ENTITY-MIB/>`_ tables with
`ezsnmp <https://github.com/carlkidcrypto/ezsnmp>`_, network engineers can
continuously audit optical power budgets across hundreds of switch ports and
replace degrading optics during scheduled maintenance windows.

In this tutorial, we will examine how RFC 3433 encodes physical sensor values,
convert raw integer readings into decibels-milliwatt (dBm), and build an
automated transceiver DOM auditor using ``ezsnmp``.

Understanding ENTITY-SENSOR-MIB (RFC 3433)
==========================================

Unlike simple counters, ``entPhySensorValue`` (``.1.3.6.1.2.1.99.1.1.1.4``)
returns a raw signed 32-bit integer. To interpret that integer accurately, RFC
3433 requires reading three companion columns indexed by the same
``entPhysicalIndex``:

- ``entPhysicalName`` (``.1.3.6.1.2.1.47.1.1.1.1.7``): Human-readable
  component name (e.g., ``Ethernet1/1 Rx Power Sensor``).
- ``entPhySensorType`` (``.1.3.6.1.2.1.99.1.1.1.1``): Measurement unit type,
  such as ``watts(6)``, ``celsius(8)``, ``amperes(5)``, or ``voltsDC(4)``.
- ``entPhySensorScale`` (``.1.3.6.1.2.1.99.1.1.1.2``): SI exponent multiplier:
  ``yocto(1)`` through ``yotta(17)``, where ``milli(8)`` represents ``10^-3``,
  ``micro(7)`` represents ``10^-6``, and ``units(9)`` represents ``10^0``.
- ``entPhySensorPrecision`` (``.1.3.6.1.2.1.99.1.1.1.3``): Number of fixed-point
  decimal places to shift the raw integer.

Converting Milliwatts to dBm
----------------------------

Many network operating systems (including Arista EOS and Cisco NX-OS) report
optical Rx/Tx power in **milliwatts** (``entPhySensorType = watts(6)``,
``entPhySensorScale = milli(8)``). For example, if ``entPhySensorValue`` is
``6365`` with ``precision = 4``, the physical power is:

.. code-block:: text

    Power (mW) = 6365 * 10^(-4) = 0.6365 mW
    Power (dBm) = 10 * log10(0.6365) = -1.96 dBm

Building the Optical Power Auditor with ezsnmp
==============================================

Using ``ezsnmp.Session`` with ``set_max_repeaters_to_num=25``, we can bulk-walk
the entity name and sensor tables sequentially in tuned PDU batches, normalize
the readings, and flag any transceiver falling below a low-Rx warning threshold
(e.g., ``-12.0 dBm``):

.. code-block:: python

    import math
    from ezsnmp import Session
    from ezsnmp.exceptions import GenericError

    # RFC 4133 & RFC 3433 OIDs
    OID_ENT_PHYSICAL_NAME = "1.3.6.1.2.1.47.1.1.1.1.7"
    OID_SENSOR_TYPE = "1.3.6.1.2.1.99.1.1.1.1"
    OID_SENSOR_SCALE = "1.3.6.1.2.1.99.1.1.1.2"
    OID_SENSOR_PRECISION = "1.3.6.1.2.1.99.1.1.1.3"
    OID_SENSOR_VALUE = "1.3.6.1.2.1.99.1.1.1.4"

    # SI Scale exponents per RFC 3433 EntitySensorDataScale
    SCALE_EXPONENT = {
        "7": -6,   # micro
        "8": -3,   # milli
        "9": 0,    # units
    }

    def audit_optical_dom(
        host: str,
        community: str = "public",
        rx_warn_dbm: float = -12.0,
    ):
        session = Session(
            hostname=host,
            community=community,
            version=2,
            timeout=3,
            retries=1,
            set_max_repeaters_to_num=25,
        )

        try:
            print(f"[*] Auditing transceiver DOM/DDM power on {host}...")

            names = {
                v.index: v.value
                for v in session.bulk_walk(OID_ENT_PHYSICAL_NAME)
            }
            types = {
                v.index: v.value
                for v in session.bulk_walk(OID_SENSOR_TYPE)
            }
            scales = {
                v.index: v.value
                for v in session.bulk_walk(OID_SENSOR_SCALE)
            }
            precisions = {
                v.index: int(v.value)
                for v in session.bulk_walk(OID_SENSOR_PRECISION)
            }
            values = session.bulk_walk(OID_SENSOR_VALUE)

            for var in values:
                idx = var.index
                name = names.get(idx, f"Entity-{idx}")

                # Filter for optical power sensors (type 6 = watts)
                if types.get(idx) != "6":
                    continue

                raw_val = int(var.value)
                precision = precisions.get(idx, 0)
                exp = SCALE_EXPONENT.get(scales.get(idx, "9"), 0)

                # Convert to watts, then to milliwatts, then to dBm
                watts = raw_val * (10 ** (-precision)) * (10 ** exp)
                mw = watts * 1000.0

                if mw <= 0:
                    dbm_str = "-inf dBm (LOS)"
                    is_low = True
                else:
                    dbm = 10.0 * math.log10(mw)
                    dbm_str = f"{dbm:.2f} dBm"
                    is_low = ("rx" in name.lower()) and (dbm < rx_warn_dbm)

                prefix = "[!]" if is_low else "[+]"
                print(f"{prefix} {name:<36}: {dbm_str}")

        except GenericError as err:
            print(f"[-] SNMP optical audit failed: {err}")

📥 `Download this script: audit_optical_dom.py <https://raw.githubusercontent.com/carlkidcrypto/carlkidcrypto.github.io/main/example_scripts/ezsnmp-transceiver-optical-power-dom-telemetry/audit_optical_dom.py>`_

Best Practices for Optical Link Budgets
=======================================

1. **Track Baseline Attenuation Over Time**: Store Rx dBm readings in a
   time-series database. A sudden 3 dB drop after a patch-panel move indicates a
   pinched fiber or contaminated ferrule before link flaps occur.
2. **Correlate Tx and Rx Across Link Peers**: Compare the local Tx power
   against the remote peer's Rx power to isolate whether attenuation stems from
   the transmitting laser or the fiber plant.
3. **Monitor Module Temperature**: High ambient rack temperatures accelerate
   laser aging. Combine ``watts(6)`` polling with ``celsius(8)`` checks on the
   same ``entPhysicalTable`` pass.

Summary & What's Next
=====================

Auditing ``ENTITY-SENSOR-MIB`` with `ezsnmp
<https://github.com/carlkidcrypto/ezsnmp>`_ gives network teams deterministic,
vendor-neutral visibility into optical transceiver health across datacenter
uplinks without parsing fragile CLI output.

In our next blog post, we will rotate to `purpleair_api
<https://github.com/carlkidcrypto/purpleair_api>`_, exploring automated sensor
health auditing to detect dual-channel optical drift and hardware degradation.

----

.. warning::

   AI-generated content may contain misinformation or mistakes. A human does review this, but we are only human.

