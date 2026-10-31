.. meta::
   :description: In modern Site Reliability Engineering (SRE) and cloud infrastructure, network metrics belong alongside application telemetry in centralized platforms like...
   :keywords: Python, Snmp, Prometheus, Opentelemetry, Ezsnmp, Devops, Python, ezsnmp, Networking, DevOps
   :author: Carlos Santos (@carlkidcrypto)
   :property=og:title: Building Custom Observability Exporters with ezsnmp
   :property=og:description: In modern Site Reliability Engineering (SRE) and cloud infrastructure, network metrics belong alongside application telemetry in centralized platforms like...
   :property=og:type: article
   :property=og:url: https://carlkidcrypto.github.io/blog/ezsnmp-custom-observability-exporters.html
   :property=og:image: https://carlkidcrypto.github.io/_static/logo.png
   :name=twitter:card: summary
   :name=twitter:title: Building Custom Observability Exporters with ezsnmp
   :name=twitter:description: In modern Site Reliability Engineering (SRE) and cloud infrastructure, network metrics belong alongside application telemetry in centralized platforms like...
   :name=twitter:image: https://carlkidcrypto.github.io/_static/logo.png

============================================================
Building Custom Observability Exporters with ezsnmp
============================================================

.. note::

   * **Published:** October 22, 2026
   * **Authors:** Written by Gemini 3.8 Flash, Co-Authored & Reviewed by `Carlos Santos (@carlkidcrypto) <https://github.com/carlkidcrypto>`_
   * **Estimated Reading Time:** 5 minutes
   * **Tags:** `Python` • `Snmp` • `Prometheus` • `Opentelemetry` • `Ezsnmp` • `Devops`

Why Build a Custom SNMP Exporter?
=================================

In modern Site Reliability Engineering (SRE) and cloud infrastructure, network
metrics belong alongside application telemetry in centralized platforms like
Prometheus, Grafana, and OpenTelemetry (OTel).

While generic tools like the Prometheus ``snmp_exporter`` exist, they often
rely on massive, auto-generated YAML configurations that can be unwieldy to
customize. Building a custom Python exporter offers compelling advantages:

* **Dynamic Device Discovery**: Automatically query inventory from NetBox,
  Consul, or Kubernetes APIs rather than hardcoding static target lists.
* **On-the-Fly Metric Transformation**: Compute normalized rates, calculate
  transceiver optical margins, or synthesize health scores before publishing.
* **Lightweight Footprint**: Tailor collection strictly to the exact metrics
  your team monitors, slashing polling overhead.

However, custom Python exporters must complete scrapes well within Prometheus'
scrape timeout (typically 10 to 15 seconds). Pure-Python SNMP libraries often
stall under high scrape concurrency.

`ezsnmp <https://github.com/carlkidcrypto/ezsnmp>`_ provides native Net-SNMP C
speed, enabling sub-second multi-OID data collection that effortlessly meets
aggressive Prometheus scrape deadlines.


Architecture: The Custom Prometheus Collector Pattern
=====================================================

The official ``prometheus_client`` Python library provides a custom
``Collector`` registry pattern. Instead of updating global metric gauges in a
tight loop, you implement a ``collect()`` generator that queries ezsnmp only
when Prometheus initiates a scrape request.

Key advantages:

* **Pull-Based Synchronization**: Network queries occur strictly on Prometheus
  scrape intervals, preventing redundant background polling.
* **Dynamic Labeling**: Interface names, hardware types, and IP addresses are
  mapped directly into Prometheus metric labels.
* **Clean Scrape Accounting**: Native exposure of scrape duration and
  reachability gauges (e.g. ``device_up``).


Practical Implementation: Prometheus SNMP Collector
===================================================

Below is a complete, production-ready custom Prometheus collector querying
interface traffic and operational status via ezsnmp:

.. code-block:: python

    import time
    from prometheus_client import start_http_server
    from prometheus_client.core import (
        CounterMetricFamily,
        GaugeMetricFamily,
        REGISTRY
    )
    from ezsnmp import Session
    from ezsnmp.exceptions import EasySNMPError

    class NetworkDeviceCollector:
        """Custom Prometheus collector using ezsnmp for high-speed scrapes."""

        def __init__(self, targets: dict[str, str]):
            # Mapping of device_name -> target_ip
            self.targets = targets

        def collect(self):
            # Define metric families with consistent Prometheus naming
            device_up = GaugeMetricFamily(
                "network_device_up",
                "Binary indicator if the device responded to SNMP queries",
                labels=["device"]
            )
            rx_octets = CounterMetricFamily(
                "network_interface_receive_bytes_total",
                "Total octets received on the interface (64-bit HC counter)",
                labels=["device", "interface"]
            )
            tx_octets = CounterMetricFamily(
                "network_interface_transmit_bytes_total",
                "Total octets transmitted on the interface (64-bit HC counter)",
                labels=["device", "interface"]
            )

            for name, ip in self.targets.items():
                try:
                    session = Session(
                        hostname=ip,
                        community="public",
                        version=2,
                        timeout=1,
                        retries=1
                    )

                    # Bulk-walk interface descriptions and 64-bit counters
                    descr_vars = session.bulkwalk("ifDescr", max_repetitions=25)
                    in_vars = session.bulkwalk(
                        "ifHCInOctets", max_repetitions=25
                    )
                    out_vars = session.bulkwalk(
                        "ifHCOutOctets", max_repetitions=25
                    )

                    # Index metrics by interface index
                    in_map = {v.oid_index: v.value for v in in_vars}
                    out_map = {v.oid_index: v.value for v in out_vars}

                    for d in descr_vars:
                        idx = d.oid_index
                        iface_name = d.value
                        if idx in in_map:
                            rx_octets.add_metric(
                                [name, iface_name], float(in_map[idx])
                            )
                        if idx in out_map:
                            tx_octets.add_metric(
                                [name, iface_name], float(out_map[idx])
                            )

                    device_up.add_metric([name], 1)

                except EasySNMPError:
                    # Record device as down if unreachable
                    device_up.add_metric([name], 0)

            yield device_up
            yield rx_octets
            yield tx_octets

    if __name__ == "__main__":
        # Sample inventory
        DEVICES = {
            "edge-router-01": "192.168.1.1",
            "core-switch-01": "192.168.1.2",
        }

        # Register custom collector and serve /metrics on port 9116
        REGISTRY.register(NetworkDeviceCollector(DEVICES))
        start_http_server(9116)
        print("Prometheus exporter listening on port 9116 (/metrics)")

        while True:
            time.sleep(3600)


Integrating with OpenTelemetry (OTel)
=====================================

For teams standardizing on OpenTelemetry (OTel), you can pair ezsnmp with the
OpenTelemetry Metrics SDK using an ``ObservableGauge``.

Instead of managing an HTTP server, the OTel SDK triggers your ezsnmp polling
callback periodically and pushes metric batches directly to the OpenTelemetry
Collector via OTLP (gRPC or HTTP/protobuf):

.. code-block:: python

    from opentelemetry import metrics
    from opentelemetry.metrics import CallbackOptions, Observation
    from ezsnmp import Session

    meter = metrics.get_meter("ezsnmp.network.telemetry")
    session = Session(hostname="192.168.1.1", community="public", version=2)

    def observe_interface_traffic(options: CallbackOptions):
        """Asynchronous observable callback triggered by the OTel SDK."""
        observations = []
        try:
            results = session.bulkwalk("ifHCInOctets", max_repetitions=25)
            for var in results:
                observations.append(
                    Observation(
                        value=int(var.value),
                        attributes={"interface.index": var.oid_index}
                    )
                )
        except Exception:
            pass
        return observations

    meter.create_observable_gauge(
        name="network.interface.rx_bytes",
        callbacks=[observe_interface_traffic],
        description="Incoming octets per network interface",
        unit="By"
    )


Production Best Practices
=========================

* **Bound Label Cardinality**: Avoid embedding volatile attributes (like IP
  addresses that change frequently or packet timestamps) into Prometheus metric
  labels to prevent metric index bloat.
* **Reuse Session Objects**: In long-running exporter daemons, cache ``Session``
  instances by IP to bypass Net-SNMP UDP socket re-allocation on every scrape.
* **Tune Max Repetitions**: Set ``max_repetitions=25..50`` in ``bulkwalk``
  to retrieve dozens of metrics per packet, keeping scrape durations
  under 500ms even across high-density switch stacks.


Migration Notes: Easy SNMP vs ezsnmp
====================================

* **Memory Stability in Scrape Daemons**: Exporters run 24/7, executing millions
  of scrapes over time. ``ezsnmp``'s modern C++17 RAII architecture guarantees
  that Net-SNMP response structs are freed on every scrape cycle, eliminating
  the slow memory growth seen in legacy ``easysnmp``.
* **GIL Release**: Concurrently scraping multiple devices within a single
  scrape window runs fully in parallel without Python GIL bottlenecks.


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
