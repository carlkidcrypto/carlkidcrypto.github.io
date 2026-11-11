#!/usr/bin/env python3
"""Example script for: Cross-Platform Installation & Troubleshooting ezsnmp Builds
Source: https://carlkidcrypto.github.io/blog/ezsnmp-cross-platform-installation-troubleshooting.html
"""

from importlib.metadata import version
from ezsnmp import Session

print(f"ezsnmp version: {version('ezsnmp')}")

# Query local daemon or test agent
with Session(hostname="localhost", community="public", version=2) as session:
    (sys_descr,) = session.get("sysDescr.0")
    print(f"Connected: {sys_descr.value}")
