.. meta::
   :description: Learn how to build process-isolated SNMP telemetry pipelines with ezsnmp_data_logger, mapping scalar and IF-MIB bulk walks into SQLite or TimescaleDB.
   :keywords: ezsnmp, ezsnmp_data_logger, Python, SNMP, TimescaleDB, SQLite, Telemetry, Networking, DevOps
   :author: Carlos Santos (@carlkidcrypto)
   :property=og:title: Getting Started with ezsnmp_data_logger: SNMP Telemetry Pipelines
   :property=og:description: Learn how to build process-isolated SNMP telemetry pipelines with ezsnmp_data_logger, mapping scalar and IF-MIB bulk walks into SQLite or TimescaleDB.
   :property=og:type: article
   :property=og:url: https://carlkidcrypto.github.io/blog/ezsnmp-data-logger-getting-started-pipelines.html
   :property=og:image: https://carlkidcrypto.github.io/_static/logo.png
   :name=twitter:card: summary
   :name=twitter:title: Getting Started with ezsnmp_data_logger: SNMP Telemetry Pipelines
   :name=twitter:description: Learn how to build process-isolated SNMP telemetry pipelines with ezsnmp_data_logger, mapping scalar and IF-MIB bulk walks into SQLite or TimescaleDB.
   :name=twitter:image: https://carlkidcrypto.github.io/_static/logo.png

=================================================================
Getting Started with ezsnmp_data_logger: SNMP Telemetry Pipelines
=================================================================

.. note::

   * **Published:** November 20, 2026
   * **Authors:** Written by Gemini 3.8 Flash, Co-Authored & Reviewed by `Carlos Santos (@carlkidcrypto) <https://github.com/carlkidcrypto>`_
   * **Estimated Reading Time:** 7 minutes
   * **Tags:** `Ezsnmp` • `Ezsnmp_Data_Logger` • `Python` • `Snmp` • `Timescaledb` • `Sqlite` • `Telemetry`

Polling network devices with `ezsnmp <https://github.com/carlkidcrypto/ezsnmp>`_
gives Python engineers direct, high-speed access to Net-SNMP's C++17 bindings.
However, building a production monitoring stack requires more than ad-hoc
``Session.get()`` or ``Session.bulk_walk()`` calls. You need deterministic
scheduling, process isolation around Net-SNMP's C state, structured schema
mapping, and durable time-series persistence.

That is the exact gap `ezsnmp_data_logger
<https://github.com/carlkidcrypto/ezsnmp_data_logger>`_ is built to solve.
Modeled on the same proven architectural patterns as `purpleair_data_logger
<https://github.com/carlkidcrypto/purpleair_data_logger>`_,
``ezsnmp_data_logger`` turns raw SNMP scalar and table walks into clean,
timestamped records stored in SQLite, CSV, or PostgreSQL/TimescaleDB.

In this tutorial, we will explore the architecture of ``ezsnmp_data_logger``,
configure multi-device polling targets, design an efficient time-series storage
schema, and implement process-isolated collection pipelines that follow modern
``ezsnmp`` API standards.

Why Dedicated SNMP Data Logging Matters
=======================================

Ad-hoc monitoring scripts often fail in production for three predictable
reasons:

- **Unbounded Concurrency Contention**: Net-SNMP maintains process-global C
  state protected by internal mutexes. Spawning dozens of threads inside a
  single Python process creates lock contention rather than linear speedups.
- **Inconsistent Result Normalization**: SNMP agents return mixed types—from
  64-bit interface counters (``Counter64``) to ``NOSUCHOBJECT`` or
  ``NOSUCHINSTANCE`` type strings in SNMPv2c/v3—which must be validated before
  database insertion.
- **Clock Drift in Polling Loops**: Using ``time.sleep()`` without tracking
  monotonic execution deltas causes polling intervals to drift over days,
  skewing rate-per-second calculations.

``ezsnmp_data_logger`` standardizes these concerns into a modular pipeline
separating **target inventory**, **collection workers**, and **storage
backends**.

Installation & Environment Verification
=======================================

Install ``ezsnmp_data_logger`` alongside ``ezsnmp`` inside a clean Python 3.10+
virtual environment:

.. code-block:: bash

    pip install ezsnmp ezsnmp-data-logger

Verify the installed ``ezsnmp`` runtime using ``importlib.metadata`` (note
that ``ezsnmp`` does not expose a ``__version__`` attribute):

.. code-block:: python

    from importlib.metadata import version

    print(f"ezsnmp runtime version: {version('ezsnmp')}")

Defining Device Targets & OID Profiles
======================================

A clean logger decouples *what* to poll from *where* to poll. Group standard
scalar system metrics and high-capacity interface counters (``IF-MIB``) into
reusable polling profiles:

- **System Scalars**: ``sysUpTime.0`` (``.1.3.6.1.2.1.1.3.0``) and
  ``sysName.0`` (``.1.3.6.1.2.1.1.5.0``) queried in a single batched
  ``session.get([...])`` call.
- **Interface Counters**: ``ifDescr`` (``.1.3.6.1.2.1.2.2.1.2``),
  ``ifOperStatus`` (``.1.3.6.1.2.1.2.2.1.8``), ``ifHCInOctets``
  (``.1.3.6.1.2.1.31.1.1.1.6``), and ``ifHCOutOctets``
  (``.1.3.6.1.2.1.31.1.1.1.10``) retrieved via ``session.bulk_walk()``.

Building a Process-Isolated Collector
=====================================

Because Net-SNMP uses process-global C state, scaling across a fleet of switches
and routers is cleanest with ``concurrent.futures.ProcessPoolExecutor``. Each
worker process instantiates its own ``ezsnmp.Session`` with
``set_max_repeaters_to_num=25`` and ``print_enums_numerically=True``.

Remember these modern ``ezsnmp`` rules when writing collector workers:

1. Never pass ``max_repetitions`` to ``session.bulk_walk(oid)``—configure
   ``set_max_repeaters_to_num`` on the ``Session`` constructor instead.
2. Always read ``.index`` and ``.type`` on ``Result`` objects (never legacy
   ``.oid_index`` or ``.snmp_type``).
3. Catch modern ``ezsnmp.exceptions`` classes (``GenericError``,
   ``TimeoutError``, ``ConnectionError``) and inspect ``var.type`` for
   ``NOSUCHOBJECT`` or ``NOSUCHINSTANCE``.

Here is a complete collector worker and SQLite persistence pipeline:

.. code-block:: python

    import sqlite3
    import time
    from concurrent.futures import ProcessPoolExecutor, as_completed
    from datetime import datetime, timezone
    from typing import Any, Dict, List

    from ezsnmp import Session
    from ezsnmp.exceptions import ConnectionError, GenericError, TimeoutError

    OID_SYS_NAME = "1.3.6.1.2.1.1.5.0"
    OID_SYS_UPTIME = "1.3.6.1.2.1.1.3.0"
    OID_IF_DESCR = "1.3.6.1.2.1.2.2.1.2"
    OID_IF_OPER_STATUS = "1.3.6.1.2.1.2.2.1.8"
    OID_IF_HC_IN_OCTETS = "1.3.6.1.2.1.31.1.1.1.6"
    OID_IF_HC_OUT_OCTETS = "1.3.6.1.2.1.31.1.1.1.10"

    DB_PATH = "snmp_telemetry.db"

    def init_sqlite_schema(db_path: str = DB_PATH) -> None:
        with sqlite3.connect(db_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS interface_metrics (
                    collected_at TEXT NOT NULL,
                    host TEXT NOT NULL,
                    sys_name TEXT,
                    if_index TEXT NOT NULL,
                    if_descr TEXT,
                    oper_status INTEGER,
                    in_octets INTEGER,
                    out_octets INTEGER,
                    PRIMARY KEY (collected_at, host, if_index)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_if_host_time
                ON interface_metrics (host, collected_at DESC)
            """)

    def safe_int(val: Any, default: int = 0) -> int:
        digits = "".join(c for c in str(val) if c.isdigit() or c == "-")
        return int(digits) if digits and digits != "-" else default

    def poll_device(target: Dict[str, Any]) -> List[tuple]:
        host = target["host"]
        community = target.get("community", "public")
        collected_at = datetime.now(timezone.utc).isoformat()
        rows: List[tuple] = []

        session = Session(
            hostname=host,
            community=community,
            version=2,
            timeout=2,
            retries=1,
            set_max_repeaters_to_num=25,
            print_enums_numerically=True,
        )

        try:
            # Batch scalar lookups in a single get() call
            scalars = session.get([OID_SYS_NAME, OID_SYS_UPTIME])
            sys_name = (
                scalars[0].value
                if scalars[0].type not in ("NOSUCHOBJECT", "NOSUCHINSTANCE")
                else host
            )

            descrs = {
                v.index: v.value
                for v in session.bulk_walk(OID_IF_DESCR)
                if v.type not in ("NOSUCHOBJECT", "NOSUCHINSTANCE")
            }
            opers = {
                v.index: safe_int(v.value, 4)
                for v in session.bulk_walk(OID_IF_OPER_STATUS)
            }
            in_octs = {
                v.index: safe_int(v.value)
                for v in session.bulk_walk(OID_IF_HC_IN_OCTETS)
            }
            out_octs = {
                v.index: safe_int(v.value)
                for v in session.bulk_walk(OID_IF_HC_OUT_OCTETS)
            }

            for if_idx, if_name in descrs.items():
                rows.append((
                    collected_at,
                    host,
                    sys_name,
                    if_idx,
                    if_name,
                    opers.get(if_idx, 4),
                    in_octs.get(if_idx, 0),
                    out_octs.get(if_idx, 0),
                ))

        except (TimeoutError, ConnectionError, GenericError) as err:
            print(f"[{host}] Poll skipped due to SNMP error: {err}")

        return rows

    def run_collection_cycle(targets: List[Dict[str, Any]]) -> None:
        all_rows: List[tuple] = []
        with ProcessPoolExecutor(max_workers=4) as pool:
            futures = {pool.submit(poll_device, t): t["host"] for t in targets}
            for fut in as_completed(futures):
                all_rows.extend(fut.result())

        if all_rows:
            with sqlite3.connect(DB_PATH) as conn:
                conn.executemany(
                    """
                    INSERT OR IGNORE INTO interface_metrics (
                        collected_at, host, sys_name, if_index,
                        if_descr, oper_status, in_octets, out_octets
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    all_rows,
                )
            print(f"[+] Persisted {len(all_rows)} interface rows.")

    if __name__ == "__main__":
        init_sqlite_schema()
        fleet = [
            {"host": "10.0.1.10", "community": "public"},
            {"host": "10.0.1.11", "community": "public"},
        ]
        interval_sec = 60.0
        next_tick = time.monotonic()

        # Execute one immediate cycle (wrap in loop for daemon mode)
        run_collection_cycle(fleet)
        sleep_for = max(0.0, (next_tick + interval_sec) - time.monotonic())
        print(f"[*] Next cycle scheduled in {sleep_for:.2f}s")

📥 `Download this script: init_sqlite_schema.py <https://raw.githubusercontent.com/carlkidcrypto/carlkidcrypto.github.io/main/example_scripts/ezsnmp-data-logger-getting-started-pipelines/init_sqlite_schema.py>`_

Production Storage & Scheduling Patterns
========================================

When moving from a local SQLite prototype to multi-site infrastructure:

1. **Use ``time.monotonic()`` for Scheduling**: Never schedule intervals with
   wall-clock ``datetime.now()`` comparisons. NTP step adjustments or daylight
   saving transitions can stall or double-fire timers, whereas
   ``time.monotonic()`` guarantees steady elapsed intervals.
2. **Enable SQLite WAL Mode or TimescaleDB**: For edge appliances,
   ``PRAGMA journal_mode=WAL;`` lets Grafana or analytical readers query
   ``snmp_telemetry.db`` concurrently while workers insert batches. For core
   networks, route inserts into PostgreSQL/TimescaleDB hypertables partitioned
   by ``collected_at``.
3. **Remember Polling Granularity**: A 60-second SNMP polling cycle measures
   interval-average throughput accurately, but sub-second microbursts require
   queue drop counters (``DIFFSERV-MIB``) or streaming telemetry.

Summary & What's Next
=====================

With `ezsnmp_data_logger
<https://github.com/carlkidcrypto/ezsnmp_data_logger>`_, network automation
engineers get a clean, repeatable pattern for turning high-speed ``ezsnmp``
walks into durable time-series records without fighting Net-SNMP global locks
or legacy exception names.

In our next blog post, we will rotate to `shared-workflows
<https://github.com/carlkidcrypto/shared-workflows>`_, exploring how to
standardize multi-repository CI/CD pipelines across Python and Node.js projects
using reusable GitHub Actions ``workflow_call`` templates.

----

.. warning::

   AI-generated content may contain misinformation or mistakes. A human does
   review this, but we are only human.
