#!/usr/bin/env python3
"""Example script for: Asynchronous Polling with ezsnmp: Integrating into asyncio
Source: https://carlkidcrypto.github.io/blog/ezsnmp-async-polling-event-loops.html
"""

async def poll_device(
    client: AsyncSNMPClient,
    device_name: str,
    semaphore: asyncio.Semaphore
) -> dict:
    async with semaphore:
        try:
            # Query metrics asynchronously without blocking the loop
            sys_descr, uptime = await client.get(
                ["sysDescr.0", "sysUpTime.0"]
            )
            return {
                "device": device_name,
                "status": "ONLINE",
                "descr": sys_descr.value,
                "uptime": uptime.value
            }
        except TimeoutError:
            return {"device": device_name, "status": "TIMEOUT"}
        except GenericError as exc:
            return {"device": device_name, "status": f"ERROR: {exc}"}

async def main():
    # Dedicated bounded thread pool for SNMP I/O operations
    # Note: Net-SNMP uses process-global locks; keep worker counts <= 4
    # per process to avoid lock contention, or use ProcessPoolExecutor.
    snmp_pool = ThreadPoolExecutor(max_workers=4)
    loop = asyncio.get_running_loop()
    try:
        targets = [
            f"switch-{i:03d}.internal" for i in range(1, 21)
        ]
        sem = asyncio.Semaphore(4)  # Bound concurrent in-flight requests

        clients = [
            AsyncSNMPClient(host, executor=snmp_pool)
            for host in targets
        ]

        tasks = [
            poll_device(client, host, sem)
            for client, host in zip(clients, targets)
        ]

        results = await asyncio.gather(*tasks)
        online = sum(1 for r in results if r["status"] == "ONLINE")
        print(f"Polling completed: {online}/{len(targets)} nodes online.")
    finally:
        await loop.run_in_executor(None, snmp_pool.shutdown, True)

if __name__ == "__main__":
    asyncio.run(main())
