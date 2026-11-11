#!/usr/bin/env python3
"""Example script for: Automating Network Topology Discovery: LLDP and CDP with ezsnmp
Source: https://carlkidcrypto.github.io/blog/ezsnmp-network-topology-discovery-lldp-cdp.html
"""

def format_chassis_mac(raw_hex: str) -> str:
    """Normalize hex-formatted chassis MAC string to colon-separated notation."""
    clean_hex = raw_hex.replace(" ", "").replace(":", "").replace("-", "")
    if len(clean_hex) == 12:
        return ":".join(clean_hex[i:i + 2].lower() for i in range(0, 12, 2))
    return raw_hex
