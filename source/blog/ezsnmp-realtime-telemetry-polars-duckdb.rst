.. meta::
   :description: Modern network engineers increasingly require sub-interval telemetry: polling switch fabrics, optical links, and data center core routers at 1- to 5-second...
   :keywords: Python, Snmp, Polars, Duckdb, Telemetry, Ezsnmp, Analytics, Python, ezsnmp, Networking, DevOps
   :author: Carlos Santos (@carlkidcrypto)
   :property=og:title: Real-Time Network Telemetry with ezsnmp, Polars, and DuckDB
   :property=og:description: Modern network engineers increasingly require sub-interval telemetry: polling switch fabrics, optical links, and data center core routers at 1- to 5-second...
   :property=og:type: article
   :property=og:url: https://carlkidcrypto.github.io/blog/ezsnmp-realtime-telemetry-polars-duckdb.html
   :property=og:image: https://carlkidcrypto.github.io/_static/logo.png
   :name=twitter:card: summary
   :name=twitter:title: Real-Time Network Telemetry with ezsnmp, Polars, and DuckDB
   :name=twitter:description: Modern network engineers increasingly require sub-interval telemetry: polling switch fabrics, optical links, and data center core routers at 1- to 5-second...
   :name=twitter:image: https://carlkidcrypto.github.io/_static/logo.png

============================================================
Real-Time Network Telemetry with ezsnmp, Polars, and DuckDB
============================================================

.. note::

   * **Published:** October 25, 2026
   * **Authors:** Written by Gemini 3.8 Flash, Co-Authored & Reviewed by `Carlos Santos (@carlkidcrypto) <https://github.com/carlkidcrypto>`_
   * **Estimated Reading Time:** 5 minutes
   * **Tags:** `Python` • `Snmp` • `Polars` • `Duckdb` • `Telemetry` • `Ezsnmp` • `Analytics`

The Rise of Embedded Columnar Analytics in Telemetry
====================================================

Modern network engineers increasingly require sub-interval telemetry: polling
switch fabrics, optical links, and data center core routers at 1- to 5-second
frequencies to detect microbursts, packet buffer drops, and link saturation.

Traditionally, streaming high-frequency network metrics demanded complex
external infrastructure: InfluxDB clusters, Kafka brokers, or dedicated
Prometheus instances. While powerful, these stacks introduce significant
operational overhead, storage cost, and indexing delays.

Recent advancements in Python data engineering offer a cleaner alternative:
pairing **in-process columnar analytics engines**—specifically `Polars
<https://pola.rs>`_ and `DuckDB <https://duckdb.org>`_—with high-speed C
polling.

However, high-frequency polling pipelines collapse if the SNMP collection
layer cannot extract hundreds of interfaces within milliseconds.

`ezsnmp <https://github.com/carlkidcrypto/ezsnmp>`_ provides compiled Net-SNMP
C/C++17 speed, allowing telemetry daemons to gather raw counter data in
fractions of a second and stream directly into Apache Arrow memory.


The Pipeline Architecture
=========================

The telemetry pipeline consists of three coordinated stages:

1. **Native Ingestion (ezsnmp)**: Multi-threaded ``bulkwalk`` queries 64-bit
   High Capacity (HC) counters (``ifHCInOctets``, ``ifHCOutOctets``) every
   few seconds, tagging each batch with high-resolution timestamps.
2. **Vectorized Rate Calculation (Polars)**: Raw counter metrics are converted
   into Apache Arrow DataFrames. Vectorized window functions compute delta rates
   (bits/sec) across sliding time windows with sub-millisecond execution.
3. **Analytical Persistence (DuckDB)**: Cleaned telemetry batches stream
   directly into DuckDB tables or partitioned Parquet files, allowing instant
   analytical SQL queries with zero external database servers.


Practical Implementation: Streaming Telemetry Pipeline
======================================================

Below is a complete implementation that samples interface counters, computes
bandwidth rates via Polars, and executes analytical SQL in DuckDB:

.. code-block:: python

    import time
    import duckdb
    import polars as pl
    from ezsnmp import Session

    def sample_interface_counters(
        session: Session, hostname: str
    ) -> list[dict]:
        """Collect current 64-bit octet counters across all switch ports."""
        timestamp = time.time()
        in_vars = session.bulkwalk("ifHCInOctets", max_repetitions=25)
        out_vars = session.bulkwalk("ifHCOutOctets", max_repetitions=25)

        out_map = {v.oid_index: int(v.value) for v in out_vars}
        records = []

        for v in in_vars:
            idx = v.oid_index
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


Handling Counter Overflows & Device Resets
==========================================

When monitoring high-speed networks, counter rollover handling is vital:

* **32-Bit Counters**: At 10 Gbps, standard 32-bit ``ifInOctets`` wraps in
  approximately 3.4 seconds. Always target 64-bit High Capacity objects
  (``ifHCInOctets``), which take centuries to wrap even at 400 Gbps.
* **Agent Reboots & Counter Wraps**: When a device restarts or an interface
  flaps, counter values drop, resulting in negative deltas.
  Using ``pl.when(pl.col("delta_rx_bytes") >= 0)`` safely filters out reboot
  discontinuities without polluting analytics graphs with bogus spikes.


Production Best Practices
=========================

* **Zero-Copy Arrow Interchange**: Polars and DuckDB share the Apache Arrow
  in-memory standard. Converting a Polars DataFrame into DuckDB or exporting to
  Parquet incurs zero serialization overhead.
* **Batch Writes to Parquet**: In production daemons, flush completed Polars
  DataFrames every minute to partitioned Parquet files on NVMe storage:

  .. code-block:: python

      telemetry_df.write_parquet(
          f"data/telemetry_{int(time.time())}.parquet",
          compression="zstd"
      )

* **Multi-Device Polling Pools**: Combine ezsnmp's thread-safe C++17 session
  primitives with ``concurrent.futures.ThreadPoolExecutor`` to poll dozens of
  switches simultaneously before unifying into a single Polars DataFrame.


Migration Notes: Easy SNMP vs ezsnmp
====================================

High-frequency telemetry pipelines run continuous polling loops 24 hours a day,
7 days a week:

* **Zero Memory Creep**: Legacy ``easysnmp`` suffered from gradual memory
  accumulation during continuous cyclic walks. ``ezsnmp``'s C++17 RAII memory
  management ensures Net-SNMP PDU chains and variable buffers are freed after
  every batch.
* **Stable Numeric Unpacking**: Direct C-to-Python integer conversions prevent
  integer truncation or overflow faults when handling high-capacity 64-bit
  counters.


Useful Links & Community
========================

* **Source Repository**: `carlkidcrypto/ezsnmp on GitHub
  <https://github.com/carlkidcrypto/ezsnmp>`_
* **PyPI Distribution**: `ezsnmp Package on PyPI
  <https://pypi.org/project/ezsnmp/>`_
* **Documentation**: `ezsnmp Online Documentation
  <https://carlkidcrypto.github.io/ezsnmp/>`_
* **Blog & Updates**: `Carlos Santos Blog Updates`_

.. _Carlos Santos Blog Updates:
 https://github.com/carlkidcrypto/carlkidcrypto.github.io/tree/feature/updates
