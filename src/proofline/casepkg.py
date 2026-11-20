"""Case package: the review-ready output. JSON for machines, Markdown and HTML for people.

Every factual statement in the package is a verified claim linked to evidence ids, and the
package says what it could not establish. It contains no verdict: the decision boundary
is stated in the document and enforced by the verifier's wording check.
"""

from __future__ import annotations

import html
from dataclasses import asdict
from typing import Any

from proofline import analysis
from proofline.audit import AuditLog
from proofline.investigation import Case

BOUNDARY = ("This package assembles evidence for a human reviewer. It makes no legal finding, "
            "does not declare any party guilty of anything, and triggers no external action.")


def money(cents: int) -> str:
    return f"{cents / 100:,.2f}"


def build_package(case: Case, audit: AuditLog) -> dict[str, Any]:
    store, risk = case.store, case.risk
    month = analysis.window_month(risk)
    cited: dict[str, list[str]] = {}
    for c in case.claims:
        cited[c.claim_id] = list(c.evidence_ids)

    matrix = []
    for c in case.claims:
        kinds: dict[str, int] = {}
        for eid in c.evidence_ids:
            k = store.get(eid).kind
            kinds[k] = kinds.get(k, 0) + 1
        matrix.append({"claim_id": c.claim_id, "kind": c.kind, "evidence_total": len(c.evidence_ids),
                       "evidence_by_kind": kinds,
                       "key_records": [store.get(e).record_ref for e in c.evidence_ids
                                       if store.get(e).kind != "transaction"][:8]})

    uncertainty = [f"Possible closed chain cannot be confirmed: no invoice from "
                   f"{f.data['missing_link']['from']} to {f.data['missing_link']['to']} within the authorized scope"
                   for f in case.findings if f.status == "candidate"]
    uncertainty += [f"Evidence requirement not met: {m['requirement']} ({m['have']} of {m['need']})"
                    for m in case.validation["missing"]]
    uncertainty += ["Absence of a payment is judged only against the collected transaction records"
                    for f in case.findings if f.code == "no_matching_payment"]
    integrity = [{"evidence_id": i.evidence_id, "record_ref": i.record_ref, "flags": i.text_flags,
                  "handling": "free-text field excluded from narrative input; record kept as evidence"}
                 for i in store.items.values() if i.text_flags]

    ok, bad = audit.verify()
    return {
        "case_id": case.case_id, "version": case.version, "status": case.status,
        "generated_at": case.generated_at, "decision_boundary": BOUNDARY,
        "risk_event": asdict(case.risk), "scope": case.scope,
        "summary": [{"claim_id": c.claim_id, "statement": c.statement, "kind": c.kind}
                    for c in case.claims],
        "findings": [asdict(f) for f in case.findings],
        "claims": [asdict(c) for c in case.claims],
        "withheld_claims": [asdict(c) for c in case.withheld],
        "draft_rounds": case.draft_rounds,
        "evidence_matrix": matrix,
        "evidence": [asdict(i) for i in store.items.values()],
        "source_references": {i.evidence_id: i.record_ref for i in store.items.values()},
        "timeline": [e for e in analysis.timeline(store) if e["date"].startswith(month)],
        "entity_graph": analysis.entity_edges(store, month),
        "uncertainty": uncertainty, "integrity_notes": integrity,
        "suggested_evidence_requests": case.suggested_requests,
        "validation": case.validation,
        "gateway_decisions": [asdict(d) for d in case.gateway_decisions],
        "reviews": case.reviews,
        "audit": {"records": audit.count(), "head_hash": audit.head(), "chain_valid": ok,
                  "first_bad_seq": bad},
    }


def render_markdown(pkg: dict[str, Any]) -> str:
    r = pkg["risk_event"]
    out = [f"# Case {pkg['case_id']} (version {pkg['version']})", "",
           f"**Status:** {pkg['status']}  ", f"**Entity under review:** {r['entity_ref']}  ",
           f"**Risk category:** {r['risk_category']} (upstream score {r['risk_score']}, synthetic input)  ",
           f"**Authorized scope:** {', '.join(pkg['scope'])}", "", f"> {pkg['decision_boundary']}", "",
           "## Summary of verified claims", ""]
    out += [f"- **{c['claim_id']}** ({c['kind']}): {c['statement']}" for c in pkg["summary"]] or ["- none"]
    out += ["", "## Findings", "", "| Finding | Status | Evidence records |", "|---|---|---|"]
    out += [f"| {f['title']} | {f['status']} | {len(f['evidence_ids'])} |" for f in pkg["findings"]]
    out += ["", "## Evidence matrix", "", "| Claim | Kind | Evidence | By kind | Key records |", "|---|---|---|---|---|"]
    for m in pkg["evidence_matrix"]:
        kinds = ", ".join(f"{k} {v}" for k, v in sorted(m["evidence_by_kind"].items()))
        keys = ", ".join(m["key_records"][:5]) + (" ..." if len(m["key_records"]) > 5 else "")
        out.append(f"| {m['claim_id']} | {m['kind']} | {m['evidence_total']} | {kinds} | {keys} |")
    out += ["", "## Verification", ""]
    for rd in pkg["draft_rounds"]:
        out.append(f"- Draft round {rd['round']}: {rd['drafted']} claims drafted, "
                   f"{len(rd['verified'])} verified, {len(rd['rejected'])} rejected.")
        for rej in rd["rejected"]:
            out.append(f"  - Rejected {rej['claim_id']}: \"{rej['statement']}\" ({'; '.join(rej['reasons'])})")
    if pkg["withheld_claims"]:
        out.append(f"- {len(pkg['withheld_claims'])} claim(s) withheld after the last round.")
    out += ["", "## Timeline (analysis window)", "", "| Date | Event | Amount | Evidence |", "|---|---|---|---|"]
    out += [f"| {e['date']} | {e['event']} | {money(e['amount_cents'])} | {e['evidence_id']} |"
            for e in pkg["timeline"]]
    out += ["", "## Entity relationships (invoices in the window)", "", "| From | To | Invoices | Total |", "|---|---|---|---|"]
    out += [f"| {e['from']} | {e['to']} | {e['invoices']} | {money(e['total_cents'])} |"
            for e in pkg["entity_graph"]]
    out += ["", "## Missing evidence and uncertainty", ""]
    out += [f"- {u}" for u in pkg["uncertainty"]] or ["- none recorded"]
    if pkg["suggested_evidence_requests"]:
        out += ["", "Suggested evidence requests for the reviewer:", ""]
        out += [f"- `{s['tool']}` {s['entity_id']}: {s['reason']}" for s in pkg["suggested_evidence_requests"]]
    if pkg["integrity_notes"]:
        out += ["", "## Evidence integrity notes", ""]
        out += [f"- {n['evidence_id']} ({n['record_ref']}): {', '.join(n['flags'])}. {n['handling']}."
                for n in pkg["integrity_notes"]]
    if pkg["reviews"]:
        out += ["", "## Review history", ""]
        out += [f"- {v['decided_at']} {v['reviewer_id']}: {v['decision']} ({v['rationale']})"
                for v in pkg["reviews"]]
    a = pkg["audit"]
    out += ["", "## Audit", "",
            f"{a['records']} audit records, chain valid: {a['chain_valid']}, head `{a['head_hash'][:16]}...`", ""]
    return "\n".join(out)


def render_html(pkg: dict[str, Any]) -> str:
    esc = html.escape
    body = []
    for line in render_markdown(pkg).split("\n"):
        body.append(line)
    # Minimal, safe conversion: everything is escaped; structure comes from our own markup.
    parts = [f"<h1>Case {esc(pkg['case_id'])} <small>v{pkg['version']} &middot; {esc(pkg['status'])}</small></h1>",
             f"<p class='boundary'>{esc(pkg['decision_boundary'])}</p>",
             "<h2>Verified claims</h2><ul>"]
    parts += [f"<li><b>{esc(c['claim_id'])}</b> <i>{esc(c['kind'])}</i>: {esc(c['statement'])}</li>"
              for c in pkg["summary"]]
    parts += ["</ul><h2>Findings</h2><table><tr><th>Finding</th><th>Status</th><th>Evidence</th></tr>"]
    parts += [f"<tr><td>{esc(f['title'])}</td><td>{esc(f['status'])}</td><td>{len(f['evidence_ids'])}</td></tr>"
              for f in pkg["findings"]]
    parts += ["</table><h2>Timeline</h2><table><tr><th>Date</th><th>Event</th><th>Amount</th><th>Evidence</th></tr>"]
    parts += [f"<tr><td>{esc(e['date'])}</td><td>{esc(e['event'])}</td><td>{money(e['amount_cents'])}</td>"
              f"<td>{esc(e['evidence_id'])}</td></tr>" for e in pkg["timeline"]]
    parts += ["</table><h2>Missing evidence and uncertainty</h2><ul>"]
    parts += [f"<li>{esc(u)}</li>" for u in pkg["uncertainty"]] or ["<li>none recorded</li>"]
    a = pkg["audit"]
    parts += ["</ul><h2>Audit</h2>",
              f"<p>{a['records']} records &middot; chain valid: {a['chain_valid']} &middot; "
              f"head <code>{esc(a['head_hash'][:16])}</code></p>"]
    css = ("body{font:15px/1.5 system-ui,sans-serif;max-width:60rem;margin:2rem auto;padding:0 1rem;"
           "color:#1b2a3a;background:#fff}h1 small{font-weight:400;color:#5a6b7d}"
           "table{border-collapse:collapse;width:100%;margin:.5rem 0 1.5rem}th,td{border:1px solid #d5dde6;"
           "padding:.3rem .5rem;text-align:left;font-size:13px}th{background:#f1f5f9}"
           ".boundary{border-left:4px solid #c58a2b;background:#fbf6ec;padding:.6rem .9rem}"
           "@media(prefers-color-scheme:dark){body{background:#0f1720;color:#dbe4ee}th{background:#1a2735}"
           "th,td{border-color:#2b3b4d}.boundary{background:#2a2316}}")
    return (f"<!doctype html><html lang='en'><meta charset='utf-8'><meta name='viewport' "
            f"content='width=device-width,initial-scale=1'><title>{esc(pkg['case_id'])}</title>"
            f"<style>{css}</style><body>{''.join(parts)}</body></html>")
