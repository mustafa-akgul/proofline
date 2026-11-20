"""Narrative step: turns findings into claims. The narrator never decides what is true;
the verifier does.

`TemplateNarrator` is deterministic and is the default, so the prototype needs no API key.
`LLMNarrator` is the adapter seam for a real model and is intentionally not implemented.
`SimulatedFaultyNarrator` exists to show the verifier working: its first draft contains two
deliberately bad claims, standing in for the failure modes of a real model.
"""

from __future__ import annotations

from typing import Protocol

from proofline.analysis import paid_invoice_ids
from proofline.contracts import Claim, Finding, RiskEvent
from proofline.evidence import EvidenceStore
from proofline.verifier import format_value, make_fact

FREE_TEXT_FIELDS = {"note"}


class Narrator(Protocol):
    def draft(self, findings: list[Finding], store: EvidenceStore, risk: RiskEvent,
              feedback: list[Claim] | None = None) -> list[Claim]: ...


def safe_context(store: EvidenceStore) -> list[dict]:
    """What a model-backed narrator is allowed to see: validated, structured fields only.
    Free-text fields are dropped, and items whose text looked like instructions are marked."""
    out = []
    for item in store.validated():
        payload = {k: v for k, v in item.payload.items() if k not in FREE_TEXT_FIELDS}
        out.append({"evidence_id": item.evidence_id, "kind": item.kind, "data": payload,
                    "free_text_removed": bool(FREE_TEXT_FIELDS & set(item.payload)),
                    "integrity_flags": item.text_flags})
    return out


def _name(store: EvidenceStore, entity_id: str) -> str:
    item = store.by_ref(f"entities:{entity_id}")
    return item.payload["name"] if item else entity_id


class TemplateNarrator:
    def draft(self, findings, store, risk, feedback=None):
        claims: list[Claim] = []
        who = f"{_name(store, risk.entity_ref)} ({risk.entity_ref})"

        def add(statement: str, kind: str, ids: list[str], facts=None, checks=None) -> None:
            claims.append(Claim(f"C-{len(claims) + 1:03d}", statement, kind, ids,
                                facts or [], checks or []))

        for f in findings:
            d = f.data
            if f.code == "volume_spike":
                facts = [make_fact("invoices in month", "sum", "invoice_count", d["last_ids"], "count", store),
                         make_fact("baseline median", "median", "invoice_count", d["baseline_ids"], "count", store),
                         make_fact("baseline months", "count", None, d["baseline_ids"], "count", store)]
                add(f"In {d['month']}, {who} issued {format_value('count', facts[0].value)} invoices, against a "
                    f"median of {format_value('count', facts[1].value)} per month over the "
                    f"{format_value('count', facts[2].value)} preceding months of record.",
                    "observation", f.evidence_ids, facts)
            elif f.code == "closed_invoice_chain":
                ids = d["chain_ids"]
                facts = [make_fact("invoices in chain", "count", None, ids, "count", store),
                         make_fact("chain total", "sum", "amount_cents", ids, "money", store)]
                checks = [{"op": "closed_chain", "evidence_ids": ids}]
                paid = paid_invoice_ids(store)
                unpaid = bool(store.validated("transaction")) and all(
                    store.get(i).payload["invoice_id"] not in paid for i in ids)
                tail = ", none with a matching payment in the collected transaction records" if unpaid else ""
                if unpaid:
                    checks.append({"op": "all_pred", "pred": "unsettled", "evidence_ids": ids})
                route = " -> ".join(d["parties"])
                add(f"{format_value('count', facts[0].value)} invoices issued between {d['first_date']} and "
                    f"{d['last_date']} form a closed chain {route}, totalling "
                    f"{format_value('money', facts[1].value)} currency units{tail}.",
                    "observation", f.evidence_ids, facts, checks)
            elif f.code == "candidate_invoice_chain":
                a, c = d["pair_ids"]
                y, z = d["missing_link"]["from"], d["missing_link"]["to"]
                checks = [{"op": "same_month", "field": "issue_date", "evidence_ids": d["pair_ids"]},
                          {"op": "within_ratio", "field": "amount_cents", "ratio": 0.10,
                           "evidence_ids": d["pair_ids"]}]
                add(f"{who} issued an invoice to {y} and received one from {z} in the same month, of similar "
                    f"value. An invoice from {y} to {z} that would close a chain is not within the authorized "
                    f"scope, so a closed chain cannot be confirmed.", "hypothesis", f.evidence_ids, [], checks)
            elif f.code == "no_matching_payment":
                un = d["unsettled_ids"]
                facts = [make_fact("invoices in month", "count", None, d["all_ids"], "count", store),
                         make_fact("without payment", "count_where", None, d["all_ids"], "count", store,
                                   pred="unsettled"),
                         make_fact("unpaid total", "sum", "amount_cents", un, "money", store)]
                add(f"Of {format_value('count', facts[0].value)} invoices issued or received by {who} in "
                    f"{d['month']}, {format_value('count', facts[1].value)} have no matching payment in the "
                    f"collected transaction records, totalling {format_value('money', facts[2].value)} "
                    f"currency units.", "observation", f.evidence_ids, facts,
                    [{"op": "all_pred", "pred": "unsettled", "evidence_ids": un}])
            elif f.code == "tax_amount_mismatch":
                ids = d["ids"]
                facts = [make_fact("mismatched invoices", "count_where", None, ids, "count", store,
                                   pred="tax_mismatch")]
                listing = ", ".join(store.get(i).payload["invoice_id"] for i in ids)
                add(f"{format_value('count', facts[0].value)} invoices issued by {who} carry a tax amount that "
                    f"differs from the reference-rate amount: {listing}.", "observation", ids, facts)
            elif f.code == "reused_invoice_number":
                ids = d["ids"]
                facts = [make_fact("invoices sharing number", "count", None, ids, "count", store)]
                listing = ", ".join(store.get(i).payload["invoice_id"] for i in ids)
                add(f"Invoice number {d['invoice_no']} appears on {format_value('count', facts[0].value)} "
                    f"invoices issued by {who} with different amounts ({listing}).", "observation", ids, facts,
                    [{"op": "all_equal", "field": "invoice_no", "evidence_ids": ids},
                     {"op": "not_all_equal", "field": "amount_cents", "evidence_ids": ids}])
        return claims


class SimulatedFaultyNarrator:
    """First draft = correct claims + two injected defects. After feedback = correct claims."""

    def __init__(self) -> None:
        self._inner = TemplateNarrator()

    def draft(self, findings, store, risk, feedback=None):
        claims = self._inner.draft(findings, store, risk, feedback)
        if feedback:
            return claims
        vol = next((f for f in findings if f.code == "volume_spike"), None)
        if vol:
            wrong = make_fact("invoices in month", "sum", "invoice_count", vol.data["last_ids"], "count", store)
            wrong.value = 37.0
            claims.append(Claim(
                f"C-{len(claims) + 1:03d}",
                f"In {vol.data['month']}, {risk.entity_ref} issued 37 invoices, a sharp jump.",
                "observation", list(vol.evidence_ids[:1]), [wrong]))
        claims.append(Claim(f"C-{len(claims) + 1:03d}",
                            f"{risk.entity_ref} committed tax fraud through a circular invoice scheme.",
                            "observation", []))
        return claims


class LLMNarrator:
    """Adapter seam for a language model. Not implemented in this prototype.

    A real implementation would send `safe_context(store)` plus the findings to a model,
    ask for claims in the `Claim` schema, and return them. Nothing it returns is trusted
    until `verifier.verify_claims` accepts it.
    """

    def draft(self, findings, store, risk, feedback=None):
        raise NotImplementedError("LLMNarrator is a design seam; use TemplateNarrator")
