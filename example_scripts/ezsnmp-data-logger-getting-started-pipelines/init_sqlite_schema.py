#!/usr/bin/env python3
"""Example script for: Getting Started with ezsnmp_data_logger: SNMP Telemetry Pipelines
Source: https://carlkidcrypto.github.io/blog/ezsnmp-data-logger-getting-started-pipelines.html
"""

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
            v.index: safe_int(v.value, 4) for v in session.bulk_walk(OID_IF_OPER_STATUS)
        }
        in_octs = {
            v.index: safe_int(v.value) for v in session.bulk_walk(OID_IF_HC_IN_OCTETS)
        }
        out_octs = {
            v.index: safe_int(v.value) for v in session.bulk_walk(OID_IF_HC_OUT_OCTETS)
        }

        for if_idx, if_name in descrs.items():
            rows.append(
                (
                    collected_at,
                    host,
                    sys_name,
                    if_idx,
                    if_name,
                    opers.get(if_idx, 4),
                    in_octs.get(if_idx, 0),
                    out_octs.get(if_idx, 0),
                )
            )

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
