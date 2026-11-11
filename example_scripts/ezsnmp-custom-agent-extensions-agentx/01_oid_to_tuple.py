#!/usr/bin/env python3
"""Example script for: Building Custom SNMP Agent Extensions with Python and ezsnmp
Source: https://carlkidcrypto.github.io/blog/ezsnmp-custom-agent-extensions-agentx.html
"""

import sys
import time

BASE_OID = ".1.3.6.1.4.1.99999.1"

# Define custom metrics under our enterprise branch
METRICS = {
    # Active worker jobs
    f"{BASE_OID}.1.0": ("integer", lambda: 42),
    # Current queue depth
    f"{BASE_OID}.2.0": ("gauge", lambda: int(time.time()) % 100),
    # Service health string
    f"{BASE_OID}.3.0": ("string", lambda: "Service-Online-OK"),
}

def oid_to_tuple(s: str) -> tuple[int, ...]:
    """Convert a dotted OID string into an integer tuple for numeric comparison."""
    return tuple(int(p) for p in s.strip(".").split(".") if p)

def handle_pass_persist():
    while True:
        line = sys.stdin.readline()
        if not line:
            break
        cmd = line.strip()

        if cmd == "PING":
            print("PONG", flush=True)

        elif cmd == "set":
            # pass_persist SET provides: OID, then TYPE and VALUE lines
            _target_oid = sys.stdin.readline()
            _val_type_and_val = sys.stdin.readline()
            # Explicitly reject writes for this read-only metric provider
            print("not-writable", flush=True)

        elif cmd == "get":
            oid = sys.stdin.readline().strip()
            if oid in METRICS:
                val_type, val_fn = METRICS[oid]
                print(oid)
                print(val_type)
                print(str(val_fn()), flush=True)
            else:
                print("NONE", flush=True)

        elif cmd == "getnext":
            oid = sys.stdin.readline().strip()
            target_key = oid_to_tuple(oid)
            sorted_oids = sorted(METRICS.keys(), key=oid_to_tuple)
            match = next((o for o in sorted_oids if oid_to_tuple(o) > target_key), None)
            if match:
                val_type, val_fn = METRICS[match]
                print(match)
                print(val_type)
                print(str(val_fn()), flush=True)
            else:
                print("NONE", flush=True)

if __name__ == "__main__":
    handle_pass_persist()
