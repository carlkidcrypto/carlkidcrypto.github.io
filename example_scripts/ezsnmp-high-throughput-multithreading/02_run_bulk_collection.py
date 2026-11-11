#!/usr/bin/env python3
"""Example script for: High-Throughput Network Monitoring: Scaling ezsnmp Concurrency
Source: https://carlkidcrypto.github.io/blog/ezsnmp-high-throughput-multithreading.html
"""

import concurrent.futures
from ezsnmp import Session

DEVICE_INVENTORY = [
    {"ip": "10.0.1.1", "community": "public"},
    {"ip": "10.0.1.2", "community": "public"},
]

def collect_interface_table(device_info: dict) -> dict:
    ip = device_info["ip"]
    with Session(
        hostname=ip,
        community=device_info["community"],
        version=2,
        timeout=2,
        retries=1
    ) as session:
        # bulk_walk utilizes Net-SNMP GETBULK acceleration
        interfaces = session.bulk_walk("ifDescr")
        return {ip: [item.value for item in interfaces]}

def run_bulk_collection(devices: list):
    with concurrent.futures.ProcessPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(collect_interface_table, devices))
    return results
