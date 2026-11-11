#!/usr/bin/env python3
"""Example script for: Navigating Complex SNMP Tables with ezsnmp: Advanced Patterns
Source: https://carlkidcrypto.github.io/blog/ezsnmp-advanced-table-navigation.html
"""

from collections import defaultdict
from ezsnmp import Session

def collect_interface_table(hostname: str, community: str = "public"):
    session = Session(
        hostname=hostname,
        community=community,
        version=2,
        timeout=2,
        retries=1,
        set_max_repeaters_to_num=25
    )

    # Columns to retrieve from IF-MIB
    columns = [
        "ifDescr",
        "ifType",
        "ifSpeed",
        "ifOperStatus",
        "ifHCInOctets",
        "ifHCOutOctets"
    ]

    # Reconstruct rows: table[index][column_name] = value
    # Note: Independent walks per column collect data sequentially;
    # in environments with rapid interface churn, verify row completeness.
    table = defaultdict(dict)

    for col in columns:
        # Utilize Net-SNMP GETBULK acceleration for each column
        results = session.bulk_walk(col)
        for var in results:
            # Key by requested column name since var.oid may include the MIB prefix (e.g. IF-MIB::ifDescr)
            table[var.index][col] = var.value

    return table

if __name__ == "__main__":
    interfaces = collect_interface_table("switch-core01.local")
    for idx, row in sorted(interfaces.items(), key=lambda x: int(x[0])):
        descr = row.get("ifDescr", "Unknown")
        status = row.get("ifOperStatus", "Unknown")
        in_octets = row.get("ifHCInOctets", "0")
        print(
            f"Interface [{idx}] {descr:<15} "
            f"Status: {status} In: {in_octets}"
        )
