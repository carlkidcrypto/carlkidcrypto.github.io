#!/usr/bin/env python3
"""Example script for: C++17 Under the Hood: Inside ezsnmp's Native Architecture
Source: https://carlkidcrypto.github.io/blog/ezsnmp-cpp17-native-architecture.html
"""

import threading
from ezsnmp import Session

# Explicit serialization when sharing a single Session across threads
session = Session(hostname="switch1.local", community="public", version=2)
session_lock = threading.Lock()

def thread_safe_get(oid):
    with session_lock:
        return session.get(oid)
