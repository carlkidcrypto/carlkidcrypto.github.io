#!/usr/bin/env python3
"""Example script for: Working with MIBs in ezsnmp: OID Translation & Enterprise MIBs
Source: https://carlkidcrypto.github.io/blog/ezsnmp-working-with-mibs-guide.html
"""

from ezsnmp import Session

session = Session(hostname='192.168.1.1', community='public', version=2)

var = session.get('sysUpTime.0')[0]
print(f"Symbolic OID : {var.oid}")        # 'sysUpTime'
print(f"Index        : {var.index}")      # '0'
print(f"Value        : {var.value}")      # '12345678'
print(f"Type         : {var.type}")       # 'TICKS'
