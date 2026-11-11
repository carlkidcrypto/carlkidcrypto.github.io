#!/usr/bin/env python3
"""Example script for: Building Custom Observability Exporters with ezsnmp
Source: https://carlkidcrypto.github.io/blog/ezsnmp-custom-observability-exporters.html
"""

import time
from opentelemetry import metrics
from opentelemetry.metrics import CallbackOptions, Observation
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import (
    ConsoleMetricExporter,
    PeriodicExportingMetricReader,
)
from ezsnmp import Session

# 1. Initialize OpenTelemetry Metrics SDK with a periodic exporter
reader = PeriodicExportingMetricReader(
    ConsoleMetricExporter(), export_interval_millis=15000
)
provider = MeterProvider(metric_readers=[reader])
metrics.set_meter_provider(provider)

meter = metrics.get_meter("ezsnmp.network.telemetry")
session = Session(
    hostname="192.168.1.1",
    community="public",
    version=2,
    set_max_repeaters_to_num=25
)

def observe_interface_traffic(options: CallbackOptions):
    """Asynchronous observable callback triggered by the OTel SDK."""
    observations = []
    try:
        results = session.bulk_walk("ifHCInOctets")
        for var in results:
            observations.append(
                Observation(
                    value=int(var.value),
                    attributes={"interface.index": var.index}
                )
            )
    except Exception:
        pass
    return observations

# 2. Register cumulative counter as an ObservableCounter
meter.create_observable_counter(
    name="network.interface.rx_bytes",
    callbacks=[observe_interface_traffic],
    description="Incoming octets per network interface",
    unit="By"
)

if __name__ == "__main__":
    print("OTel exporter running. Press Ctrl+C to exit.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
