#!/usr/bin/env python3
"""Example script for: Resilient SNMP Polling with ezsnmp: Timeouts, Retries & Errors
Source: https://carlkidcrypto.github.io/blog/ezsnmp-resilient-polling-error-handling.html
"""

import time

class DeviceCircuitBreaker:
    """Temporarily skip polling devices that consistently time out."""

    def __init__(self, failure_threshold: int = 3, cooldown: float = 120.0):
        self.failure_threshold = failure_threshold
        self.cooldown = cooldown
        self.failures: dict[str, int] = {}
        self.tripped_until: dict[str, float] = {}

    def is_available(self, host: str) -> bool:
        now = time.monotonic()
        if host in self.tripped_until:
            if now < self.tripped_until[host]:
                return False
            # Cooldown expired: probe device again
            del self.tripped_until[host]
            self.failures[host] = 0
        return True

    def record_failure(self, host: str):
        count = self.failures.get(host, 0) + 1
        self.failures[host] = count
        if count >= self.failure_threshold:
            self.tripped_until[host] = time.monotonic() + self.cooldown
            print(
                f"[{host}] Circuit tripped! "
                f"Pausing polls for {self.cooldown}s."
            )

    def record_success(self, host: str):
        self.failures[host] = 0
        self.tripped_until.pop(host, None)
