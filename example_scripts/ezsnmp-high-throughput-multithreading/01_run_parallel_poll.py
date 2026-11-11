#!/usr/bin/env python3
"""Example script for: High-Throughput Network Monitoring: Scaling ezsnmp Concurrency
Source: https://carlkidcrypto.github.io/blog/ezsnmp-high-throughput-multithreading.html
"""

import concurrent.futures
import os
import time
from ezsnmp import Session
from ezsnmp.exceptions import ConnectionError, GenericError, TimeoutError

# Target inventory of network nodes
DEVICE_INVENTORY = [
    {"ip": "10.0.1.1", "community": "public"},
    {"ip": "10.0.1.2", "community": "public"},
    {"ip": "10.0.1.3", "community": "public"},
    {"ip": "10.0.1.4", "community": "public"},
    {"ip": "10.0.1.5", "community": "public"},
]

OIDS = ["sysUpTime.0", "sysDescr.0"]

def poll_device(device_info: dict) -> dict:
    """Poll a single device with isolated session lifecycle inside worker."""
    ip = device_info["ip"]
    result = {"ip": ip, "status": "UNKNOWN", "metrics": {}}

    try:
        # Set explicit timeouts and retries for predictable fail-fast behavior
        with Session(
            hostname=ip,
            community=device_info["community"],
            version=2,
            timeout=1,
            retries=1
        ) as session:
            # Retrieve multiple scalar metrics in a single network round-trip
            items = session.get(OIDS)
            for item in items:
                result["metrics"][item.oid] = item.value
            result["status"] = "OK"

    except TimeoutError:
        result["status"] = "TIMEOUT"
    except ConnectionError:
        result["status"] = "CONNECTION_ERROR"
    except GenericError as err:
        result["status"] = f"ERROR: {err}"

    return result

def run_parallel_poll(devices: list, max_workers: int = 4):
    start_time = time.perf_counter()
    results = []

    # ProcessPoolExecutor gives each worker an independent Net-SNMP memory space
    with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
        future_to_device = {
            executor.submit(poll_device, dev): dev for dev in devices
        }

        for future in concurrent.futures.as_completed(future_to_device):
            res = future.result()
            results.append(res)
            print(f"[{res['status']}] Polled {res['ip']}")

    duration = time.perf_counter() - start_time
    print(f"\nPolled {len(devices)} devices in {duration:.2f} seconds.")
    return results

if __name__ == "__main__":
    # Size workers according to available CPU cores or monitoring load
    workers = min(os.cpu_count() or 4, 8)
    run_parallel_poll(DEVICE_INVENTORY, max_workers=workers)
