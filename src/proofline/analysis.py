"""Deterministic relationship and pattern analysis over validated evidence only.

No model is involved. Each finding names the evidence it rests on, and says whether it is
confirmed by the collected records or only a candidate that needs more evidence.
"""

from __future__ import annotations

import statistics

from proofline.contracts import EvidenceItem, Finding, RiskEvent
from proofline.evidence import EvidenceStore

REFERENCE_TAX_RATE = 0.20
SIMILAR_VALUE_RATIO = 1.10
MAX_CHAIN = 4


def expected_tax(amount_cents: int) -> int:
    return round(amount_cents * REFERENCE_TAX_RATE)


def tax_mismatch(item: EvidenceItem) -> bool:
    p = item.payload
    return item.kind == "invoice" and p["tax_cents"] != expected_tax(p["amount_cents"])


def window_month(risk: RiskEvent) -> str:
    y, m = int(risk.timestamp[:4]), int(risk.timestamp[5:7])
    y, m = (y - 1, 12) if m == 1 else (y, m - 1)
    return f"{y:04d}-{m:02d}"


def _inv(store: EvidenceStore) -> list[EvidenceItem]:
    return store.validated("invoice")


def paid_invoice_ids(store: EvidenceStore) -> set[str]:
    return {t.payload["ref_invoice_id"] for t in store.validated("transaction")
            if t.payload.get("ref_invoice_id")}


def volume_finding(store: EvidenceStore, risk: RiskEvent) -> Finding | None:
    month = window_month(risk)
    rows = [i for i in store.validated("monthly_summary")
            if i.record_ref.startswith(f"agg:monthly:{risk.entity_ref}:")]
    last = [i for i in rows if i.payload["month"] == month]
    base = [i for i in rows if i.payload["month"] < month]
    if not last or len(base) < 3:
        return None
    median = statistics.median(i.payload["invoice_count"] for i in base)
    if last[0].payload["invoice_count"] <= 2 * median:
        return None
    return Finding("F-VOLUME", "volume_spike", "Invoice volume above the entity's own baseline",
                   "confirmed", [i.evidence_id for i in last + base],
                   {"month": month, "last": last[0].payload["invoice_count"], "median": median,
                    "baseline_months": len(base), "last_ids": [i.evidence_id for i in last],
                    "baseline_ids": [i.evidence_id for i in base]})


def tax_finding(store: EvidenceStore, risk: RiskEvent) -> Finding | None:
    bad = [i for i in _inv(store) if i.payload["issuer_id"] == risk.entity_ref and tax_mismatch(i)]
    if not bad:
        return None
    return Finding("F-TAX", "tax_amount_mismatch", "Tax amount differs from the reference rate",
                   "confirmed", [i.evidence_id for i in bad], {"ids": [i.evidence_id for i in bad]})


def duplicate_finding(store: EvidenceStore, risk: RiskEvent) -> Finding | None:
    groups: dict[str, list[EvidenceItem]] = {}
    for i in _inv(store):
        if i.payload["issuer_id"] == risk.entity_ref:
            groups.setdefault(i.payload["invoice_no"], []).append(i)
    for number, items in sorted(groups.items()):
        if len(items) > 1 and len({i.payload["amount_cents"] for i in items}) > 1:
            return Finding("F-DUPLICATE", "reused_invoice_number",
                           "One invoice number used on invoices with different amounts", "confirmed",
                           [i.evidence_id for i in items],
                           {"invoice_no": number, "ids": [i.evidence_id for i in items]})
    return None


def unsettled_finding(store: EvidenceStore, risk: RiskEvent) -> Finding | None:
    if not store.validated("transaction"):
        return None
    month = window_month(risk)
    touching = [i for i in _inv(store) if risk.entity_ref in (i.payload["issuer_id"], i.payload["recipient_id"])
                and i.payload["issue_date"].startswith(month)]
    paid = paid_invoice_ids(store)
    unsettled = [i for i in touching if i.payload["invoice_id"] not in paid]
    if not unsettled:
        return None
    return Finding("F-UNSETTLED", "no_matching_payment",
                   "Invoices with no matching payment in the collected records", "confirmed",
                   [i.evidence_id for i in touching] + [t.evidence_id for t in store.validated("transaction")],
                   {"month": month, "all_ids": [i.evidence_id for i in touching],
                    "unsettled_ids": [i.evidence_id for i in unsettled]})


def circular_finding(store: EvidenceStore, risk: RiskEvent) -> Finding | None:
    suspect = risk.entity_ref
    invoices = sorted(_inv(store), key=lambda i: (i.payload["issue_date"], i.payload["invoice_id"]))
    month = window_month(risk)
    recent = [i for i in invoices if i.payload["issue_date"].startswith(month)]

    def extend(path: list[EvidenceItem]) -> list[EvidenceItem] | None:
        last = path[-1].payload
        if len(path) > 1 and last["recipient_id"] == suspect:
            return path
        if len(path) == MAX_CHAIN:
            return None
        for nxt in recent:
            n = nxt.payload
            if n["issuer_id"] == last["recipient_id"] and n["issue_date"] >= last["issue_date"] \
                    and nxt not in path:
                found = extend(path + [nxt])
                if found:
                    return found
        return None

    for start in recent:
        if start.payload["issuer_id"] == suspect:
            chain = extend([start])
            if chain:
                total = sum(i.payload["amount_cents"] for i in chain)
                return Finding("F-CIRCULAR", "closed_invoice_chain",
                               "Closed chain of invoices returning to the origin", "confirmed",
                               [i.evidence_id for i in chain],
                               {"parties": [c.payload["issuer_id"] for c in chain] + [suspect],
                                "chain_ids": [i.evidence_id for i in chain], "total_cents": total,
                                "first_date": chain[0].payload["issue_date"],
                                "last_date": chain[-1].payload["issue_date"]})

    outgoing = [i for i in recent if i.payload["issuer_id"] == suspect]
    incoming = [i for i in recent if i.payload["recipient_id"] == suspect]
    for a in outgoing:
        for c in incoming:
            y, z = a.payload["recipient_id"], c.payload["issuer_id"]
            hi = max(a.payload["amount_cents"], c.payload["amount_cents"])
            lo = min(a.payload["amount_cents"], c.payload["amount_cents"])
            if y != z and hi / lo <= SIMILAR_VALUE_RATIO:
                return Finding("F-CIRCULAR-CANDIDATE", "candidate_invoice_chain",
                               "Possible closed chain; connecting invoice not in authorized scope",
                               "candidate", [a.evidence_id, c.evidence_id],
                               {"pair_ids": [a.evidence_id, c.evidence_id],
                                "missing_link": {"from": y, "to": z}})
    return None


def analyze(store: EvidenceStore, risk: RiskEvent) -> list[Finding]:
    fns = (volume_finding, circular_finding, unsettled_finding, tax_finding, duplicate_finding)
    return [f for fn in fns if (f := fn(store, risk))]


def timeline(store: EvidenceStore) -> list[dict[str, str]]:
    """Dated events from validated invoice and payment evidence, oldest first."""
    events = []
    for i in store.validated("invoice"):
        p = i.payload
        events.append({"date": p["issue_date"], "evidence_id": i.evidence_id,
                       "event": f"Invoice {p['invoice_id']} {p['issuer_id']} -> {p['recipient_id']}",
                       "amount_cents": p["amount_cents"]})
    for t in store.validated("transaction"):
        p = t.payload
        events.append({"date": p["txn_date"], "evidence_id": t.evidence_id,
                       "event": f"Payment {p['txn_id']} {p['payer_id']} -> {p['payee_id']}",
                       "amount_cents": p["amount_cents"]})
    return sorted(events, key=lambda e: (e["date"], e["evidence_id"]))


def entity_edges(store: EvidenceStore, month: str | None = None) -> list[dict[str, object]]:
    """Directed invoice graph aggregated per pair (optionally one month), for the case package."""
    agg: dict[tuple[str, str], dict[str, int]] = {}
    for i in _inv(store):
        if month and not i.payload["issue_date"].startswith(month):
            continue
        k = (i.payload["issuer_id"], i.payload["recipient_id"])
        e = agg.setdefault(k, {"invoices": 0, "total_cents": 0})
        e["invoices"] += 1
        e["total_cents"] += i.payload["amount_cents"]
    return [{"from": a, "to": b, **v} for (a, b), v in sorted(agg.items())]
