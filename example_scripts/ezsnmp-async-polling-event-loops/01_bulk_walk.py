#!/usr/bin/env python3
"""Example script for: Asynchronous Polling with ezsnmp: Integrating into asyncio
Source: https://carlkidcrypto.github.io/blog/ezsnmp-async-polling-event-loops.html
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from ezsnmp import Session
from ezsnmp.exceptions import GenericError, TimeoutError

class AsyncSNMPClient:
    """Asynchronous wrapper for ezsnmp Session operations."""

    def __init__(
        self,
        hostname: str,
        community: str = "public",
        version: int = 2,
        timeout: int = 2,
        retries: int = 1,
        max_repetitions: int = 25,
        executor: ThreadPoolExecutor | None = None
    ):
        self.session = Session(
            hostname=hostname,
            community=community,
            version=version,
            timeout=timeout,
            retries=retries,
            set_max_repeaters_to_num=max_repetitions
        )
        self._executor = executor
        self._lock = asyncio.Lock()

    async def get(self, oids: str | list[str]):
        """Execute a non-blocking SNMP GET."""
        async with self._lock:
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(
                self._executor, self.session.get, oids
            )

    async def walk(self, oid: str):
        """Execute a non-blocking SNMP WALK on a single root OID."""
        async with self._lock:
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(
                self._executor, self.session.walk, oid
            )

    async def bulk_walk(self, oids: str | list[str]):
        """Execute a non-blocking GETBULK walk."""
        async with self._lock:
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(
                self._executor, self.session.bulk_walk, oids
            )
