#!/usr/bin/env python3
"""Example script for: Navigating Complex SNMP Tables with ezsnmp: Advanced Patterns
Source: https://carlkidcrypto.github.io/blog/ezsnmp-advanced-table-navigation.html
"""

from dataclasses import dataclass

@dataclass
class InterfaceMetrics:
    index: str
    description: str
    in_octets: int
    out_octets: int

def build_metric_dto(index: str, raw_row: dict) -> InterfaceMetrics:
    return InterfaceMetrics(
        index=index,
        description=raw_row.get("ifDescr", f"Interface-{index}"),
        in_octets=int(raw_row.get("ifHCInOctets", 0)),
        out_octets=int(raw_row.get("ifHCOutOctets", 0))
    )
