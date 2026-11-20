"""Governed tools. Only read-only tools can ever run; the enforcement tools exist so the
policy has something real to refuse, and they raise if they are ever reached."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Any, Callable

Records = list[dict[str, Any]]


@dataclass(frozen=True)
class ToolSpec:
    name: str
    access: str  # read | write | enforcement
    entity_args: tuple[str, ...]
    fn: Callable[[sqlite3.Connection, dict[str, Any], int], Records]
    description: str


def _rows(conn: sqlite3.Connection, sql: str, params: tuple) -> list[dict[str, Any]]:
    cur = conn.execute(sql, params)
    cols = [c[0] for c in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def _record(kind: str, ref: str, payload: dict, sql: str, params: tuple) -> dict[str, Any]:
    return {"kind": kind, "record_ref": ref, "payload": payload, "sql": sql, "params": list(params)}


def get_entity(conn, args, limit) -> Records:
    sql = "SELECT * FROM entities WHERE entity_id = ?"
    p = (args["entity_id"],)
    return [_record("entity_profile", f"entities:{r['entity_id']}", r, sql, p) for r in _rows(conn, sql, p)]


def list_invoices(conn, args, limit) -> Records:
    role = args.get("role", "any")
    eid = args["entity_id"]
    where = {"issuer": "issuer_id = ?", "recipient": "recipient_id = ?",
             "any": "(issuer_id = ? OR recipient_id = ?)"}[role]
    p = (eid,) if role != "any" else (eid, eid)
    sql = f"SELECT * FROM invoices WHERE {where} ORDER BY issue_date, invoice_id LIMIT {limit + 1}"
    return [_record("invoice", f"invoices:{r['invoice_id']}", r, sql, p) for r in _rows(conn, sql, p)]


def list_transactions(conn, args, limit) -> Records:
    eid = args["entity_id"]
    sql = ("SELECT * FROM transactions WHERE payer_id = ? OR payee_id = ? "
           f"ORDER BY txn_date, txn_id LIMIT {limit + 1}")
    p = (eid, eid)
    return [_record("transaction", f"transactions:{r['txn_id']}", r, sql, p) for r in _rows(conn, sql, p)]


MONTHLY_SQL = (
    "SELECT substr(issue_date,1,7) AS month, COUNT(*) AS invoice_count, "
    "SUM(amount_cents) AS total_cents FROM invoices "
    "WHERE issuer_id = ? AND substr(issue_date,1,7) = ? GROUP BY month"
)


def monthly_invoice_summary(conn, args, limit) -> Records:
    eid = args["entity_id"]
    months = [r["m"] for r in _rows(
        conn, "SELECT DISTINCT substr(issue_date,1,7) AS m FROM invoices WHERE issuer_id = ? "
              f"ORDER BY m LIMIT {limit + 1}", (eid,))]
    out: Records = []
    for m in months:
        p = (eid, m)
        for r in _rows(conn, MONTHLY_SQL, p):
            out.append(_record("monthly_summary", f"agg:monthly:{eid}:{m}", r, MONTHLY_SQL, p))
    return out


def _refuse(name: str):
    def fn(conn, args, limit):
        raise PermissionError(f"{name} is an enforcement tool and is never executable by Proofline")
    return fn


REGISTRY: dict[str, ToolSpec] = {
    t.name: t for t in (
        ToolSpec("get_entity", "read", ("entity_id",), get_entity, "Entity profile"),
        ToolSpec("list_invoices", "read", ("entity_id",), list_invoices, "Invoices of an entity"),
        ToolSpec("list_transactions", "read", ("entity_id",), list_transactions, "Payments of an entity"),
        ToolSpec("monthly_invoice_summary", "read", ("entity_id",), monthly_invoice_summary,
                 "Issued invoices per month, one record per month"),
        ToolSpec("flag_entity", "write", ("entity_id",), _refuse("flag_entity"), "Mark an entity"),
        ToolSpec("issue_notice", "enforcement", ("entity_id",), _refuse("issue_notice"), "Send a notice"),
        ToolSpec("freeze_account", "enforcement", ("entity_id",), _refuse("freeze_account"), "Freeze funds"),
    )
}
