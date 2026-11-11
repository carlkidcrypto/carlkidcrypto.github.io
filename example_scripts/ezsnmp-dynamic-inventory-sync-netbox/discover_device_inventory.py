#!/usr/bin/env python3
"""Example script for: Dynamic Inventory Sync: Populating NetBox & Nautobot via ezsnmp
Source: https://carlkidcrypto.github.io/blog/ezsnmp-dynamic-inventory-sync-netbox.html
"""

import pynetbox
from ezsnmp import Session
from ezsnmp.exceptions import GenericError

NETBOX_URL = "https://netbox.internal.net"
NETBOX_TOKEN = "0123456789abcdef0123456789abcdef01234567"

def parse_mac_address(raw_val: str | bytes) -> str:
    """Normalize raw octets or formatted hex strings to standard colon-separated MAC."""
    if isinstance(raw_val, bytes):
        return ":".join(f"{b:02x}" for b in raw_val)
    cleaned = raw_val.replace(":", "").replace("-", "").replace(" ", "")
    try:
        raw_bytes = bytes.fromhex(cleaned)
        if len(raw_bytes) == 6:
            return ":".join(f"{b:02x}" for b in raw_bytes)
    except ValueError:
        pass
    if len(raw_val) == 6:
        return ":".join(f"{ord(c):02x}" for c in raw_val)
    return ""

def discover_device_inventory(
    hostname: str, community: str = "public"
) -> dict:
    """Extract chassis serial and interfaces via ezsnmp."""
    session = Session(
        hostname=hostname,
        community=community,
        version=2,
        timeout=2,
        retries=1,
        print_enums_numerically=True,
        set_max_repeaters_to_num=25
    )

    try:
        # 1. Query system metadata (unpack Result tuple from session.get)
        sys_name = session.get("sysName.0")[0].value
        sys_descr = session.get("sysDescr.0")[0].value

        # 2. Extract Chassis Serial from ENTITY-MIB
        class_vars = session.bulk_walk("entPhysicalClass")
        serial_vars = session.bulk_walk("entPhysicalSerialNum")
        name_vars = session.bulk_walk("entPhysicalName")

        serials = {v.index: v.value for v in serial_vars}
        names = {v.index: v.value for v in name_vars}

        chassis_serial = "UNKNOWN"
        for var in class_vars:
            # Class 3 = chassis (numeric or symbolic)
            if var.value in ("3", "chassis"):
                candidate = serials.get(var.index, "").strip()
                if candidate:
                    chassis_serial = candidate
                    break

        # 3. Collect interface MAC addresses from IF-MIB
        if_names = session.bulk_walk("ifName")
        if_macs = session.bulk_walk("ifPhysAddress")
        mac_map = {
            v.index: parse_mac_address(v.value)
            for v in if_macs
            if parse_mac_address(v.value)
        }

        interfaces = {
            v.value: mac_map.get(v.index, "")
            for v in if_names if v.index in mac_map
        }

        return {
            "hostname": sys_name,
            "serial": chassis_serial,
            "description": sys_descr,
            "interfaces": interfaces
        }

    except GenericError as exc:
        print(f"[{hostname}] Discovery failed: {exc}")
        return {}

def reconcile_with_netbox(discovered: dict):
    """Compare operational reality against NetBox Source of Truth."""
    nb = pynetbox.api(NETBOX_URL, token=NETBOX_TOKEN)
    device = nb.dcim.devices.get(name=discovered["hostname"])

    if not device:
        print(f"Device {discovered['hostname']} not found in NetBox!")
        return

    print(f"\n--- Audit Report: {device.name} ---")

    # Serial number drift detection
    disc_serial = discovered.get("serial", "UNKNOWN")
    if disc_serial in ("", "UNKNOWN"):
        print(
            f"  [INCONCLUSIVE] Chassis serial could not be discovered via SNMP;\n"
            f"    preserving NetBox serial {device.serial} without overwriting."
        )
    elif device.serial != disc_serial:
        print(
            f"  [DRIFT DETECTED] Serial mismatch!\n"
            f"    NetBox Intent : {device.serial}\n"
            f"    Actual Switch : {disc_serial}"
        )
        # Reconcile serial if authorized
        # device.serial = disc_serial
        # device.save()
    else:
        print(f"  [OK] Serial number matches: {device.serial}")

if __name__ == "__main__":
    inv = discover_device_inventory("edge-leaf01.internal")
    if inv:
        reconcile_with_netbox(inv)
