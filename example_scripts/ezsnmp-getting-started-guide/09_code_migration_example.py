#!/usr/bin/env python3
"""Example script for: Modern SNMP in Python with ezsnmp: Practical Guide & Migration
Source: https://carlkidcrypto.github.io/blog/ezsnmp-getting-started-guide.html
"""

# Legacy easysnmp:
# from easysnmp import Session, EasySNMPTimeoutError
# session = Session(
#     hostname='10.0.0.1',
#     version=3,
#     security_username='snmp_admin',
#     security_level='auth_with_privacy',
#     auth_protocol='SHA',
#     auth_password='secret',
#     privacy_protocol='AES',
#     privacy_password='privsecret'
# )
# val = session.bulkwalk('ifDescr')

# Modern ezsnmp:
from ezsnmp import Session
from ezsnmp.exceptions import TimeoutError

with Session(
    hostname='10.0.0.1',
    version=3,
    security_level='authPriv',
    security_username='snmp_admin',
    auth_protocol='SHA',
    auth_passphrase='secret',
    privacy_protocol='AES',
    privacy_passphrase='privsecret'
) as session:
    try:
        results = session.bulk_walk('ifDescr')
        for item in results:
            print(f"Interface {item.index}: {item.value}")
    except TimeoutError:
        print("Device did not respond in time.")
