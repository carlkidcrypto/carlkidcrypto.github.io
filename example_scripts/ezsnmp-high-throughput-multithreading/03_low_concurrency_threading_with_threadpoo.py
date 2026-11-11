#!/usr/bin/env python3
"""Example script for: High-Throughput Network Monitoring: Scaling ezsnmp Concurrency
Source: https://carlkidcrypto.github.io/blog/ezsnmp-high-throughput-multithreading.html
"""

import concurrent.futures
from ezsnmp import Session

# Strict limit: at most 4 concurrent threads to protect Net-SNMP global state
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
    future_to_device = {
        executor.submit(poll_device, dev): dev for dev in DEVICE_INVENTORY
    }
    for future in concurrent.futures.as_completed(future_to_device):
        res = future.result()
        print(f"[{res['status']}] Polled {res['ip']}")
