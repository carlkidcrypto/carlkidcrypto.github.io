#!/usr/bin/env python3
"""Example script for: Modern SNMP in Python with ezsnmp: Practical Guide & Migration
Source: https://carlkidcrypto.github.io/blog/ezsnmp-getting-started-guide.html
"""

from concurrent.futures import ProcessPoolExecutor, as_completed
from ezsnmp import Session
from ezsnmp.exceptions import TimeoutError, GenericError

TARGET_HOSTS = ['10.0.0.1', '10.0.0.2', '10.0.0.3']

def poll_device(host):
    with Session(hostname=host, community='public', version=2, timeout=2) as session:
        try:
            results = session.get('sysDescr.0')
            return host, results[0].value if results else None
        except TimeoutError:
            return host, "Timeout"
        except GenericError as exc:
            return host, f"Error: {exc}"

# Multiprocessing isolates Net-SNMP process state per worker
with ProcessPoolExecutor(max_workers=4) as executor:
    futures = {executor.submit(poll_device, h): h for h in TARGET_HOSTS}
    for future in as_completed(futures):
        host, status = future.result()
        print(f"{host}: {status}")
