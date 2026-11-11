#!/usr/bin/env python3
"""Example script for: Real-Time Network Telemetry with ezsnmp, Polars, and DuckDB
Source: https://carlkidcrypto.github.io/blog/ezsnmp-realtime-telemetry-polars-duckdb.html
"""

import time
import duckdb
import polars as pl
from ezsnmp import Session

def sample_interface_counters(
    session: Session, hostname: str
) -> list[dict]:
    """Collect current 64-bit octet counters across all switch ports."""
    timestamp = time.time()
    in_vars = session.bulk_walk("ifHCInOctets")
    out_vars = session.bulk_walk("ifHCOutOctets")

    out_map = {v.index: int(v.value) for v in out_vars}
    records = []

    for v in in_vars:
        idx = v.index
        if idx in out_map:
            records.append({
                "device": hostname,
                "if_index": int(idx),
                "timestamp": timestamp,
                "rx_bytes": int(v.value),
                "tx_bytes": out_map[idx]
            })

    return records

def process_telemetry_stream(samples: list[dict]) -> pl.DataFrame:
    """Calculate throughput rates using Polars window functions."""
    df = pl.DataFrame(samples)

    # Sort by device, interface, and timestamp
    df = df.sort(["device", "if_index", "timestamp"])

    # Calculate delta time and delta bits across consecutive polls
    df = df.with_columns([
        (pl.col("timestamp") - pl.col("timestamp").shift(1))
        .over(["device", "if_index"])
        .alias("delta_sec"),
        (pl.col("rx_bytes") - pl.col("rx_bytes").shift(1))
        .over(["device", "if_index"])
        .alias("delta_rx_bytes"),
        (pl.col("tx_bytes") - pl.col("tx_bytes").shift(1))
        .over(["device", "if_index"])
        .alias("delta_tx_bytes"),
    ])

    # Convert byte deltas to Mbps, handling counter resets safely
    df = df.with_columns([
        pl.when(
            (pl.col("delta_sec") > 0) & (pl.col("delta_rx_bytes") >= 0)
        )
        .then(
            (pl.col("delta_rx_bytes") * 8)
            / (pl.col("delta_sec") * 1_000_000)
        )
        .otherwise(None)
        .alias("rx_mbps"),

        pl.when(
            (pl.col("delta_sec") > 0) & (pl.col("delta_tx_bytes") >= 0)
        )
        .then(
            (pl.col("delta_tx_bytes") * 8)
            / (pl.col("delta_sec") * 1_000_000)
        )
        .otherwise(None)
        .alias("tx_mbps")
    ])

    return df

def run_pipeline():
    session = Session(
        hostname="switch-core01.local", community="public", version=2
    )
    history = []

    print("Sampling switch interfaces at 2-second intervals...")
    for _ in range(3):
        history.extend(
            sample_interface_counters(session, "switch-core01.local")
        )
        time.sleep(2)

    # Compute throughput metrics in Polars
    telemetry_df = process_telemetry_stream(history)

    # Query metrics directly using in-memory DuckDB SQL
    con = duckdb.connect()
    con.register("telemetry", telemetry_df)

    query = """
        SELECT
            device,
            if_index,
            ROUND(AVG(rx_mbps), 2) AS avg_rx_mbps,
            ROUND(MAX(rx_mbps), 2) AS peak_rx_mbps,
            ROUND(AVG(tx_mbps), 2) AS avg_tx_mbps
        FROM telemetry
        WHERE rx_mbps IS NOT NULL
        GROUP BY device, if_index
        ORDER BY peak_rx_mbps DESC
        LIMIT 5;
    """
    print("\nTop 5 Interfaces by Peak Bandwidth:")
    print(con.execute(query).df())

if __name__ == "__main__":
    run_pipeline()
