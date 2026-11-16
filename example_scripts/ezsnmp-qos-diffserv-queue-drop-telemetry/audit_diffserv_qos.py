#!/usr/bin/env python3
"""Example script for: Real-Time QoS Telemetry: Auditing Differentiated Services (DiffServ) & Queue Drops with ezsnmp
Source: https://carlkidcrypto.github.io/blog/ezsnmp-qos-diffserv-queue-drop-telemetry.html
"""

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
            print(f"    - Action {idx:<6}: {pkts:>12} pkts | " f"{octets:>14} octets")

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
