#!/usr/bin/env python3
"""Example script for: Asynchronous Batch Polling & High-Concurrency Telemetry Pipelines with purpleair_api
Source: https://carlkidcrypto.github.io/blog/purpleair-api-async-batch-polling-pipelines.html
"""

import asyncio
import os
import time
from typing import Any, Dict, List
from purpleair_api.PurpleAirReadAPI import PurpleAirReadAPI


class AsyncPurpleAirPoller:
    def __init__(
        self,
        read_key: str,
        max_concurrent: int = 4,
        min_delay_sec: float = 0.25,
    ):
        self.client = PurpleAirReadAPI(api_read_key=read_key)
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.min_delay_sec = min_delay_sec

    def _fetch_sync(self, sensor_index: int, fields: str) -> Dict[str, Any]:
        return self.client.request_sensor_data(
            sensor_index=sensor_index,
            fields=fields,
        )

    async def fetch_sensor(
        self, sensor_index: int, fields: List[str]
    ) -> Dict[str, Any]:
        fields_str = ",".join(fields)
        async with self.semaphore:
            try:
                data = await asyncio.to_thread(
                    self._fetch_sync, sensor_index, fields_str
                )
                await asyncio.sleep(self.min_delay_sec)
                return {"sensor_index": sensor_index, "data": data}
            except Exception as exc:
                return {
                    "sensor_index": sensor_index,
                    "error": str(exc),
                }

    async def poll_grid(
        self, sensor_ids: List[int], fields: List[str]
    ) -> List[Dict[str, Any]]:
        tasks = [self.fetch_sensor(sid, fields) for sid in sensor_ids]
        return await asyncio.gather(*tasks)


async def main():
    read_key = os.environ["PURPLEAIR_READ_KEY"]
    poller = AsyncPurpleAirPoller(read_key=read_key, max_concurrent=4)

    station_grid = [282168, 175420, 194382, 131075, 145612]
    fields = ["name", "pm2.5_atm", "temperature", "humidity"]

    start = time.perf_counter()
    results = await poller.poll_grid(station_grid, fields)
    elapsed = time.perf_counter() - start

    print(f"Polled {len(results)} sensors in {elapsed:.2f}s")
    for item in results:
        if "error" in item:
            print(f"[-] Sensor {item['sensor_index']}: {item['error']}")
        else:
            sensor = item["data"].get("sensor", {})
            print(
                f"[+] {sensor.get('name')}: " f"PM2.5 = {sensor.get('pm2.5_atm')} ug/m3"
            )


if __name__ == "__main__":
    asyncio.run(main())
