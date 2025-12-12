from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any

DEFAULT_STATE: dict[str, Any] = {"orders": {}, "positions": {}, "meta": {}}


def _connect(db_path: str) -> sqlite3.Connection:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn


def ensure_tables(db_path: str) -> None:
    with _connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS agent_state (
                state_key   TEXT PRIMARY KEY,
                state_json  TEXT NOT NULL,
                updated_ts  INTEGER NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS agent_events (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                state_key   TEXT NOT NULL,
                ts          INTEGER NOT NULL,
                event_type  TEXT NOT NULL,
                payload_json TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_agent_events_key_ts ON agent_events(state_key, ts)"
        )


def load_state(db_path: str, state_key: str) -> dict[str, Any]:
    ensure_tables(db_path)

    with _connect(db_path) as conn:
        row = conn.execute(
            "SELECT state_json FROM agent_state WHERE state_key = ?",
            (state_key,),
        ).fetchone()

    if not row:
        # no existing state, return defaults
        return dict(DEFAULT_STATE)

    try:
        data = json.loads(row[0])
    except Exception:
        return dict(DEFAULT_STATE)

    if not isinstance(data, dict):
        return dict(DEFAULT_STATE)

    data.setdefault("orders", {})
    data.setdefault("positions", {})
    data.setdefault("meta", {})
    return data


def save_state(db_path: str, state_key: str, state: dict[str, Any]) -> None:
    ensure_tables(db_path)

    payload = json.dumps(state, ensure_ascii=False)
    now = int(time.time())

    with _connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO agent_state(state_key, state_json, updated_ts)
            VALUES(?, ?, ?)
            ON CONFLICT(state_key) DO UPDATE SET
                state_json = excluded.state_json,
                updated_ts = excluded.updated_ts
            """,
            (state_key, payload, now),
        )


def append_event(
    db_path: str,
    state_key: str,
    event_type: str,
    payload: dict[str, Any],
) -> None:
    ensure_tables(db_path)

    now = int(time.time())
    payload_json = json.dumps(payload, ensure_ascii=False)

    with _connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO agent_events(state_key, ts, event_type, payload_json)
            VALUES(?, ?, ?, ?)
            """,
            (state_key, now, event_type, payload_json),
        )
