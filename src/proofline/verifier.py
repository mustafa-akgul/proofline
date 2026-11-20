"""Claim-level verification. Deterministic, no model.

A claim is accepted only if every cited evidence record exists and is validated, every
number in the statement is backed by a fact recomputed from that evidence, every record id
mentioned is cited, the structural checks (closed chain, same invoice number, ...) hold,
and the wording stays on the evidence side of the decision boundary: no legal conclusions.
"""

from __future__ import annotations

import re
import statistics
from typing import Any

from proofline.analysis import paid_invoice_ids, tax_mismatch
from proofline.contracts import Claim, EvidenceItem, Fact
from proofline.evidence import EvidenceStore

ID_RE = re.compile(
    r"\b[A-Z]{2,5}-[A-Za-z0-9-]*\d[A-Za-z0-9-]*\b"   # INV-0007, ORC-2026-0107, EV-0003
    r"|\bE\d{3}\b"                                    # entity ids
    r"|\b\d{4}-\d{2}(?:-\d{2})?\b"                    # dates and months
)
NUM_RE = re.compile(r"\d[\d,]*(?:\.\d+)?")
RECORD_ID_RE = re.compile(r"\b(?:INV|TXN)-\d+\b|\bE\d{3}\b")
LEGAL_RE = re.compile(
    r"\b(fraud\w*|guilt\w*|criminal\w*|illegal\w*|evad\w+|evasion|launder\w*|crime\w*|"
    r"offen[cs]e\w*|violat\w+|committed)\b", re.IGNORECASE)


def format_value(unit: str, value: float) -> str:
    return f"{value / 100:,.2f}" if unit == "money" else f"{value:g}"


def _unsettled(item: EvidenceItem, store: EvidenceStore) -> bool:
    return item.kind == "invoice" and item.payload["invoice_id"] not in paid_invoice_ids(store)


PREDICATES = {
    "tax_mismatch": lambda item, store: tax_mismatch(item),
    "unsettled": _unsettled,
}


def compute_fact(fact: Fact, store: EvidenceStore) -> float:
    items = []
    for eid in fact.evidence_ids:
        item = store.get(eid)
        if item is None or item.validation_status != "validated":
            raise ValueError(f"evidence {eid} missing or not validated")
        items.append(item)
    if fact.agg == "count":
        return float(len(items))
    if fact.agg == "count_where":
        pred = PREDICATES[fact.pred or ""]
        if fact.pred == "unsettled" and not store.validated("transaction"):
            raise ValueError("predicate 'unsettled' needs validated transaction evidence")
        return float(sum(1 for i in items if pred(i, store)))
    values = [i.payload[fact.field] for i in items]
    return float({"sum": sum, "max": max, "min": min, "median": statistics.median}[fact.agg](values))


def make_fact(label: str, agg: str, field: str | None, ids: list[str], unit: str,
              store: EvidenceStore, pred: str | None = None) -> Fact:
    f = Fact(label, agg, field, list(ids), 0.0, unit, pred)
    f.value = compute_fact(f, store)
    return f


def _check(check: dict[str, Any], store: EvidenceStore) -> str | None:
    items = [store.get(i) for i in check["evidence_ids"]]
    if any(i is None or i.validation_status != "validated" for i in items):
        return f"check_{check['op']}:evidence_unavailable"
    ps = [i.payload for i in items if i]
    op = check["op"]
    if op == "all_equal":
        ok = len({p[check["field"]] for p in ps}) == 1
    elif op == "not_all_equal":
        ok = len({p[check["field"]] for p in ps}) > 1
    elif op == "closed_chain":
        ok = all(ps[k]["recipient_id"] == ps[k + 1]["issuer_id"] for k in range(len(ps) - 1)) \
            and ps[-1]["recipient_id"] == ps[0]["issuer_id"]
    elif op == "same_month":
        ok = len({p[check["field"]][:7] for p in ps}) == 1
    elif op == "within_ratio":
        vals = [p[check["field"]] for p in ps]
        ok = max(vals) / min(vals) <= 1 + check["ratio"]
    elif op == "all_pred":
        ok = all(PREDICATES[check["pred"]](i, store) for i in items if i)
    else:
        return f"check_unknown:{op}"
    return None if ok else f"check_failed:{op}"


def verify_claim(claim: Claim, store: EvidenceStore) -> Claim:
    reasons: list[str] = []
    stripped = ID_RE.sub(" ", claim.statement)

    if not claim.evidence_ids:
        reasons.append("no_evidence_cited")
    cited: list[EvidenceItem] = []
    for eid in claim.evidence_ids:
        item = store.get(eid)
        if item is None:
            reasons.append(f"unknown_evidence:{eid}")
        elif item.validation_status != "validated":
            reasons.append(f"evidence_not_validated:{eid}")
        else:
            cited.append(item)

    for word in sorted({m.group(0).lower() for m in LEGAL_RE.finditer(claim.statement)}):
        reasons.append(f"legal_conclusion:{word}")

    # Every number in the text must be one of the stated facts, and each fact must be right.
    shown = set()
    for fact in claim.facts:
        if not set(fact.evidence_ids) <= set(claim.evidence_ids):
            reasons.append(f"fact_uses_uncited_evidence:{fact.label}")
            continue
        try:
            actual = compute_fact(fact, store)
        except (ValueError, KeyError) as exc:
            reasons.append(f"fact_not_computable:{fact.label}:{exc}")
            continue
        if abs(actual - fact.value) > 1e-9:
            reasons.append(f"fact_value_mismatch:{fact.label}:claimed {format_value(fact.unit, fact.value)}"
                           f" actual {format_value(fact.unit, actual)}")
        shown.add(format_value(fact.unit, fact.value).replace(",", ""))
    for token in NUM_RE.findall(stripped):
        if token.replace(",", "").rstrip(".") not in shown:
            reasons.append(f"ungrounded_number:{token}")
    for fact in claim.facts:
        if format_value(fact.unit, fact.value).replace(",", "") not in stripped.replace(",", ""):
            reasons.append(f"fact_not_stated:{fact.label}")

    # Record ids in the text must belong to the cited evidence.
    known: set[str] = set()
    for i in cited:
        known |= {str(v) for v in i.payload.values()}
        known |= set(i.record_ref.split(":"))
        known |= {str(p) for p in i.provenance.get("params", [])}
    for rid in set(RECORD_ID_RE.findall(claim.statement)):
        if rid not in known:
            reasons.append(f"uncited_record_id:{rid}")

    for check in claim.checks:
        if problem := _check(check, store):
            reasons.append(problem)

    claim.reasons = sorted(set(reasons))
    claim.status = "rejected" if claim.reasons else "verified"
    return claim


def verify_claims(claims: list[Claim], store: EvidenceStore) -> list[Claim]:
    return [verify_claim(c, store) for c in claims]
