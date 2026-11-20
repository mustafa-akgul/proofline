"""Append-only, hash-chained audit log.

Each record stores the SHA-256 of the previous record, so any later edit, deletion or
reordering breaks the chain and `verify()` reports where. SQLite triggers reject UPDATE
and DELETE through the normal connection. A database owner can still drop the triggers,
which is why the chain (not the triggers) is the tamper-evidence; anchoring the head hash
outside the database is a design item, not implemented here.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from typing import Any

from proofline.clock import Clock

GENESIS = "0" * 64


def _canonical(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _digest(prev_hash: str, ts: str, actor: str, event: str, payload_json: str) -> str:
    body = "|".join((prev_hash, ts, actor, event, payload_json))
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


class AuditLog:
    def __init__(self, path: str, clock: Clock) -> None:
        self._conn = sqlite3.connect(path)
        self._clock = clock
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS audit (
                seq INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT NOT NULL, actor TEXT NOT NULL, event TEXT NOT NULL,
                payload TEXT NOT NULL, prev_hash TEXT NOT NULL, hash TEXT NOT NULL
            );
            CREATE TRIGGER IF NOT EXISTS audit_no_update BEFORE UPDATE ON audit
              BEGIN SELECT RAISE(ABORT, 'audit log is append-only'); END;
            CREATE TRIGGER IF NOT EXISTS audit_no_delete BEFORE DELETE ON audit
              BEGIN SELECT RAISE(ABORT, 'audit log is append-only'); END;
            """
        )

    def head(self) -> str:
        row = self._conn.execute("SELECT hash FROM audit ORDER BY seq DESC LIMIT 1").fetchone()
        return row[0] if row else GENESIS

    def append(self, actor: str, event: str, payload: dict[str, Any]) -> str:
        ts = self._clock.now()
        payload_json = _canonical(payload)
        prev = self.head()
        h = _digest(prev, ts, actor, event, payload_json)
        self._conn.execute(
            "INSERT INTO audit (ts, actor, event, payload, prev_hash, hash) VALUES (?,?,?,?,?,?)",
            (ts, actor, event, payload_json, prev, h),
        )
        self._conn.commit()
        return h

    def records(self) -> list[dict[str, Any]]:
        cur = self._conn.execute(
            "SELECT seq, ts, actor, event, payload, prev_hash, hash FROM audit ORDER BY seq"
        )
        cols = [c[0] for c in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]

    def verify(self) -> tuple[bool, int | None]:
        """Returns (ok, first_bad_seq)."""
        prev = GENESIS
        for r in self.records():
            expected = _digest(prev, r["ts"], r["actor"], r["event"], r["payload"])
            if r["prev_hash"] != prev or r["hash"] != expected:
                return False, r["seq"]
            prev = r["hash"]
        return True, None

    def count(self) -> int:
        return self._conn.execute("SELECT COUNT(*) FROM audit").fetchone()[0]

    def raw_connection(self) -> sqlite3.Connection:
        """Test hook: lets tests attempt tampering."""
        return self._conn
