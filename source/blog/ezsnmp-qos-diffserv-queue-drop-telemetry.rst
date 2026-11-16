.. meta::
   :description: Poll RFC 3289 DIFFSERV-MIB counters and algorithmic tail-drop or WRED queue discards in real time using ezsnmp and Python.
   :keywords: ezsnmp, Python, SNMP, QoS, DiffServ, DIFFSERV-MIB, Networking, Telemetry, Open-Source
   :author: Carlos Santos (@carlkidcrypto)
   :property=og:title: Real-Time QoS Telemetry: Auditing Differentiated Services (DiffServ) & Queue Drops with ezsnmp
   :property=og:description: Poll RFC 3289 DIFFSERV-MIB counters and algorithmic tail-drop or WRED queue discards in real time using ezsnmp and Python.
   :property=og:type: article
   :property=og:url: https://carlkidcrypto.github.io/blog/ezsnmp-qos-diffserv-queue-drop-telemetry.html
   :property=og:image: https://carlkidcrypto.github.io/_static/logo.png
   :name=twitter:card: summary
   :name=twitter:title: Real-Time QoS Telemetry: Auditing Differentiated Services (DiffServ) & Queue Drops with ezsnmp
   :name=twitter:description: Poll RFC 3289 DIFFSERV-MIB counters and algorithmic tail-drop or WRED queue discards in real time using ezsnmp and Python.
   :name=twitter:image: https://carlkidcrypto.github.io/_static/logo.png

==============================================================================================
Real-Time QoS Telemetry: Auditing Differentiated Services (DiffServ) & Queue Drops with ezsnmp
==============================================================================================

.. note::

   * **Published:** November 15, 2026
   * **Authors:** Written by Gemini 3.8 Flash, Co-Authored & Reviewed by `Carlos Santos (@carlkidcrypto) <https://github.com/carlkidcrypto>`_
   * **Estimated Reading Time:** 5 minutes
   * **Tags:** `ezsnmp` • `Python` • `SNMP` • `QoS` • `DiffServ` • `Networking` • `Telemetry` • `Open-Source`

High-throughput enterprise WAN uplinks, voice-over-IP (VoIP) trunks, and
real-time industrial control networks cannot treat every packet equally. During
microbursts or link saturation, best-effort bulk transfers can starve latency-
sensitive traffic unless routers enforce Differentiated Services (DiffServ)
Quality of Service (QoS) policies.

When QoS queues begin dropping packets—whether through tail-drop exhaustion or
Weighted Random Early Detection (WRED)—applications experience jitter,
retransmissions, and degraded throughput long before overall interface
utilization hits 100%. Monitoring aggregate ``ifInErrors`` or ``ifOutDiscards``
on ``IF-MIB`` fails to show *which* traffic class is experiencing congestion.

The `ezsnmp <https://github.com/carlkidcrypto/ezsnmp>`_ library provides native
C/C++17 bindings to Net-SNMP, allowing network automation engineers to poll
standardized ``DIFFSERV-MIB`` (RFC 3289) tables at scale and pinpoint exact
class-level queue drops in real time.

In this tutorial, we will dissect the ``DIFFSERV-MIB`` data-path architecture,
map DSCP classifiers and algorithmic drop counters, and build an automated QoS
auditor using ``ezsnmp``.

Understanding DIFFSERV-MIB (RFC 3289)
=====================================

`RFC 3289 <https://www.hjp.at/(en)/doc/rfc/rfc3289.html>`_ models a router's
QoS pipeline as a chain of functional data-path elements linked via
``RowPointer`` attributes:

1. **Classifiers (``diffServMultiFieldClfrTable``)**: Match incoming packets by
   DSCP value (``diffServMultiFieldClfrDscp``, OID
   ``.1.3.6.1.2.1.97.1.2.6.1.7``), IP prefix, or Layer 4 port ranges.
2. **Meters & Actions (``diffServCountActTable``)**: Track conforming and
   non-conforming traffic volumes using 64-bit counters:

   - ``diffServCountActOctets`` (``.1.3.6.1.2.1.97.1.5.5.1.2``)
   - ``diffServCountActPkts`` (``.1.3.6.1.2.1.97.1.5.5.1.3``)

3. **Algorithmic Droppers (``diffServAlgDropTable``)**: Apply tail-drop,
   head-drop, or random-drop (RED/WRED) algorithms before enqueuing packets.
   Critical drop counters include:

   - ``diffServAlgDropOctets`` (``.1.3.6.1.2.1.97.1.6.2.1.7``)
   - ``diffServAlgDropPkts`` (``.1.3.6.1.2.1.97.1.6.2.1.8``)
   - ``diffServAlgRandomDropOctets`` (``.1.3.6.1.2.1.97.1.6.2.1.9``)

4. **Queues & Schedulers (``diffServQTable``)**: Enforce minimum and maximum
   shaping rates (such as ``diffServQMaxRate``, OID
   ``.1.3.6.1.2.1.97.1.7.2.1.4``) and service strict-priority (EF) or weighted
   fair queues (AF).

Building the DiffServ QoS Auditor with ezsnmp
=============================================

Using ``ezsnmp.Session``, we can execute bulk table walks across
``diffServCountActTable`` and ``diffServAlgDropTable`` to correlate forwarded
packet volumes against algorithmic queue discards:

.. code-block:: python

    from ezsnmp import Session
    from ezsnmp.exceptions import GenericError

    # RFC 3289 DIFFSERV-MIB OIDs
    OID_COUNT_ACT_OCTETS = "1.3.6.1.2.1.97.1.5.5.1.2"
    OID_COUNT_ACT_PKTS = "1.3.6.1.2.1.97.1.5.5.1.3"
    OID_ALG_DROP_OCTETS = "1.3.6.1.2.1.97.1.6.2.1.7"
    OID_ALG_DROP_PKTS = "1.3.6.1.2.1.97.1.6.2.1.8"
    OID_ALG_RANDOM_DROP_OCTETS = "1.3.6.1.2.1.97.1.6.2.1.9"

    def audit_diffserv_qos(host: str, community: str = "public"):
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
            print(f"[*] Auditing DIFFSERV-MIB QoS telemetry on {host}...")

            # 1. Poll Count Action Tables (Forwarded / Classified Traffic)
            count_pkts = session.bulk_walk(OID_COUNT_ACT_PKTS)
            count_octets = session.bulk_walk(OID_COUNT_ACT_OCTETS)

            octets_map = {v.index: int(v.value) for v in count_octets}

            print(f"[+] Discovered {len(count_pkts)} QoS Count Actions:")
            for var in count_pkts:
                idx = var.index
                pkts = int(var.value)
                octets = octets_map.get(idx, 0)
                print(
                    f"    - Action {idx:<6}: {pkts:>12} pkts | "
                    f"{octets:>14} octets"
                )

            # 2. Poll Algorithmic Drop Tables (Tail-Drop & WRED Discards)
            drop_pkts = session.bulk_walk(OID_ALG_DROP_PKTS)
            drop_octets = session.bulk_walk(OID_ALG_DROP_OCTETS)
            random_octets = session.bulk_walk(OID_ALG_RANDOM_DROP_OCTETS)

            drop_oct_map = {v.index: int(v.value) for v in drop_octets}
            rand_oct_map = {v.index: int(v.value) for v in random_octets}

            total_drops = 0
            for var in drop_pkts:
                idx = var.index
                d_pkts = int(var.value)
                d_octs = drop_oct_map.get(idx, 0)
                r_octs = rand_oct_map.get(idx, 0)

                if d_pkts > 0:
                    total_drops += d_pkts
                    print(
                        f"[!] Dropper {idx}: {d_pkts} dropped pkts "
                        f"({d_octs} octets, {r_octs} WRED octets)"
                    )

            if total_drops == 0:
                print("[+] Zero algorithmic QoS queue drops detected.")

        except GenericError as err:
            print(f"[-] SNMP QoS audit failed: {err}")


    if __name__ == "__main__":
        audit_diffserv_qos("127.0.0.1")

📥 `Download this script: audit_diffserv_qos.py <https://raw.githubusercontent.com/carlkidcrypto/carlkidcrypto.github.io/main/example_scripts/ezsnmp-qos-diffserv-queue-drop-telemetry/audit_diffserv_qos.py>`_

Interpreting Drop Counters & Computing Loss Rates
=================================================

Because ``diffServCountActPkts`` and ``diffServAlgDropPkts`` are 64-bit
monotonic counters (``Counter64``), a single snapshot only reflects cumulative
history since the last router reboot. For production alerting:

1. **Compute Delta Rates**: Store two consecutive polls separated by a known
   interval (e.g., 60 seconds) and calculate the per-second packet drop rate.
2. **Distinguish WRED vs. Tail Drops**: Subtract
   ``diffServAlgRandomDropOctets`` from ``diffServAlgDropOctets``. Rising
   random drops indicate proactive TCP congestion avoidance (WRED), whereas
   pure tail drops indicate sudden queue buffer exhaustion.
3. **Protect Expedited Forwarding (DSCP 46 / EF)**: Alert immediately if any
   dropper assigned to voice or real-time control queues increments above zero.

Summary & What's Next
=====================

By polling ``DIFFSERV-MIB`` with `ezsnmp
<https://github.com/carlkidcrypto/ezsnmp>`_, network engineers move beyond
coarse interface-level discard counters to granular, per-class QoS telemetry
across enterprise WANs and campus backbones.

In our next blog post, we will rotate to `purpleair_api
<https://github.com/carlkidcrypto/purpleair_api>`_, exploring asynchronous
batch polling and high-concurrency telemetry pipelines for statewide air
quality sensor grids.

----

.. warning::

   AI-generated content may contain misinformation or mistakes. A human does review this, but we are only human.

