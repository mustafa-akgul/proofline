"""Evidence collection with provenance, and deterministic (non-LLM) validation.

Collection wraps every returned record as an EvidenceItem that remembers which tool call,
query and parameters produced it. Validation then re-verifies each item against the source
through an independent read-only handle, checks numeric sanity, and reports what is missing.
Only items that pass reach analysis, narration or verification.
"""

from __future__ import annotations

import re
import sqlite3
from datetime import date
from typing import Any

from proofline.clock import Clock
from proofline.contracts import EvidenceItem, ToolCall
from proofline.gateway import open_readonly

SOURCE_SYSTEM = "proofline-demo-db"
PK = {"invoices": "invoice_id", "transactions": "txn_id", "entities": "entity_id"}
REQUIRED = {"entity_profile": 1, "invoice": 1, "transaction": 1, "monthly_summary": 3}

# Instruction-like text inside data fields. Detection is advisory: the real defence is that
# free text never reaches the narrator (see narrator.safe_context) and that every claim is
# verified against structured evidence.
INSTRUCTION_PATTERNS = [
    r"ignore (all |any )?(previous|prior|above) (instructions|rules)",
    r"\bsystem (note|prompt|message)\b",
    r"disregard (the )?(above|previous|policy)",
    r"\b(report|mark|label) (this|the) (entity|case) as (cleared|safe|fraud)",
    r"you (must|should) now",
]
_INSTRUCTION_RE = re.compile("|".join(INSTRUCTION_PATTERNS), re.IGNORECASE)


def text_flags(payload: dict[str, Any]) -> list[str]:
    flags = []
    for key, value in payload.items():
        if isinstance(value, str) and _INSTRUCTION_RE.search(value):
            flags.append(f"instruction_like_text:{key}")
    return flags


class EvidenceStore:
    def __init__(self, case_id: str, clock: Clock) -> None:
        self.case_id = case_id
        self._clock = clock
        self.items: dict[str, EvidenceItem] = {}
        self._by_ref: dict[str, str] = {}

    def add(self, records: list[dict[str, Any]], call: ToolCall) -> list[EvidenceItem]:
        added: list[EvidenceItem] = []
        for rec in records:
            existing = self._by_ref.get(rec["record_ref"])
            if existing:
                self.items[existing].provenance["call_ids"].append(call.call_id)
                continue
            eid = f"EV-{len(self.items) + 1:04d}"
            item = EvidenceItem(
                evidence_id=eid, source_system=SOURCE_SYSTEM, record_ref=rec["record_ref"],
                retrieved_at=self._clock.now(), kind=rec["kind"],
                provenance={"tool": call.tool, "call_ids": [call.call_id], "sql": rec["sql"],
                            "params": rec["params"], "case_id": call.case_id},
                payload=rec["payload"], text_flags=text_flags(rec["payload"]))
            self.items[eid] = item
            self._by_ref[rec["record_ref"]] = eid
            added.append(item)
        return added

    def validated(self, kind: str | None = None) -> list[EvidenceItem]:
        return [i for i in self.items.values()
                if i.validation_status == "validated" and (kind is None or i.kind == kind)]

    def get(self, evidence_id: str) -> EvidenceItem | None:
        return self.items.get(evidence_id)

    def by_ref(self, record_ref: str) -> EvidenceItem | None:
        eid = self._by_ref.get(record_ref)
        return self.items.get(eid) if eid else None


def _fetch_source(conn: sqlite3.Connection, item: EvidenceItem) -> dict[str, Any] | None:
    if item.kind == "monthly_summary":
        sql = item.provenance["sql"]
        if not sql.lstrip().upper().startswith("SELECT"):
            return None
        cur = conn.execute(sql, tuple(item.provenance["params"]))
        row = cur.fetchone()
        return dict(zip([c[0] for c in cur.description], row)) if row else None
    table, key = item.record_ref.split(":", 1)
    if table not in PK:  # table name is interpolated below, so only known tables pass
        return None
    cur = conn.execute(f"SELECT * FROM {table} WHERE {PK[table]} = ?", (key,))
    row = cur.fetchone()
    return dict(zip([c[0] for c in cur.description], row)) if row else None


def _numeric_problems(item: EvidenceItem) -> list[str]:
    p, problems = item.payload, []
    if item.kind == "invoice":
        if not isinstance(p.get("amount_cents"), int) or p["amount_cents"] <= 0:
            problems.append("amount_not_positive_integer")
        elif not isinstance(p.get("tax_cents"), int) or not 0 <= p["tax_cents"] <= p["amount_cents"]:
            problems.append("tax_out_of_range")
    elif item.kind == "transaction":
        if not isinstance(p.get("amount_cents"), int) or p["amount_cents"] <= 0:
            problems.append("amount_not_positive_integer")
    elif item.kind == "monthly_summary":
        if not isinstance(p.get("invoice_count"), int) or p["invoice_count"] < 1:
            problems.append("count_not_positive")
        if not isinstance(p.get("total_cents"), int) or p["total_cents"] < 0:
            problems.append("total_negative")
    elif item.kind == "entity_profile":
        try:
            date.fromisoformat(p["registered_on"])
        except (KeyError, ValueError):
            problems.append("registration_date_invalid")
    return problems


def validate(store: EvidenceStore, db_path: str) -> dict[str, Any]:
    """Re-verify every pending item. Returns a completeness report."""
    conn = open_readonly(db_path)
    try:
        for item in store.items.values():
            if item.validation_status != "pending":
                continue
            notes: list[str] = []
            source = _fetch_source(conn, item)
            if source is None:
                notes.append("source_record_not_found")
            elif source != item.payload:
                notes.append("payload_differs_from_source")
            notes.extend(_numeric_problems(item))
            item.validation_notes = notes
            item.validation_status = "rejected" if notes else "validated"
    finally:
        conn.close()

    counts: dict[str, int] = {}
    for item in store.validated():
        counts[item.kind] = counts.get(item.kind, 0) + 1
    missing = [{"requirement": kind, "have": counts.get(kind, 0), "need": need}
               for kind, need in REQUIRED.items() if counts.get(kind, 0) < need]
    rejected = [i.evidence_id for i in store.items.values() if i.validation_status == "rejected"]
    return {"validated": len(store.validated()), "rejected": rejected,
            "missing": missing, "complete": not missing,
            "flagged_text": [i.evidence_id for i in store.items.values() if i.text_flags]}
