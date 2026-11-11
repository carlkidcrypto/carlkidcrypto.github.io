#!/usr/bin/env python3
"""Example script for: Building Custom Observability Exporters with ezsnmp
Source: https://carlkidcrypto.github.io/blog/ezsnmp-custom-observability-exporters.html
"""

import time
from prometheus_client import start_http_server
from prometheus_client.core import (
    CounterMetricFamily,
    GaugeMetricFamily,
    REGISTRY
)
from ezsnmp import Session
from ezsnmp.exceptions import GenericError

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
            labels=["device", "if_index", "interface"]
        )
        tx_octets = CounterMetricFamily(
            "network_interface_transmit_bytes_total",
            "Total octets transmitted on the interface (64-bit HC counter)",
            labels=["device", "if_index", "interface"]
        )

        for name, ip in self.targets.items():
            try:
                session = Session(
                    hostname=ip,
                    community="public",
                    version=2,
                    timeout=1,
                    retries=1,
                    set_max_repeaters_to_num=25
                )

                # Bulk-walk interface descriptions and 64-bit counters
                descr_vars = session.bulk_walk("ifDescr")
                in_vars = session.bulk_walk("ifHCInOctets")
                out_vars = session.bulk_walk("ifHCOutOctets")

                # Index metrics by interface index
                in_map = {v.index: v.value for v in in_vars}
                out_map = {v.index: v.value for v in out_vars}

                for d in descr_vars:
                    idx = d.index
                    iface_name = d.value
                    if idx in in_map:
                        rx_octets.add_metric(
                            [name, str(idx), iface_name], float(in_map[idx])
                        )
                    if idx in out_map:
                        tx_octets.add_metric(
                            [name, str(idx), iface_name], float(out_map[idx])
                        )

                device_up.add_metric([name], 1)

            except GenericError:
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
