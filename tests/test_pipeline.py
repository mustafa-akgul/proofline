import json
from pathlib import Path

import pytest

from proofline.casepkg import build_package, render_html, render_markdown
from proofline.cli import main, run_demo
from proofline.contracts import ReviewDecision
from proofline.investigation import Investigation
from proofline.narrator import LLMNarrator, SimulatedFaultyNarrator, safe_context
from proofline.synth import INJECTION_NOTE


def codes(case):
    return {f.code: f.status for f in case.findings}


def test_v1_finds_patterns_and_keeps_the_chain_as_a_candidate(inv, risk):
    case = inv.run(risk)
    assert codes(case) == {"volume_spike": "confirmed", "candidate_invoice_chain": "candidate",
                           "no_matching_payment": "confirmed", "tax_amount_mismatch": "confirmed",
                           "reused_invoice_number": "confirmed"}
    assert case.scope == ["E017"] and case.status == "PENDING_REVIEW"
    hypotheses = [c for c in case.claims if c.kind == "hypothesis"]
    assert len(hypotheses) == 1 and "cannot be confirmed" in hypotheses[0].statement
    assert {s["entity_id"] for s in case.suggested_requests if s["tool"] == "list_invoices"} == {"E021", "E022"}


def test_claim_numbers_match_the_database(inv, risk, db_path):
    import sqlite3
    case = inv.run(risk)
    c = sqlite3.connect(db_path)
    october = c.execute("SELECT COUNT(*) FROM invoices WHERE issuer_id='E017' AND issue_date LIKE '2026-10%'").fetchone()[0]
    volume = next(c for c in case.claims if c.statement.startswith("In 2026-10"))
    assert f"issued {october} invoices" in volume.statement


def test_faulty_first_draft_is_rejected_then_repaired(db_path, audit, clock, risk):
    case = Investigation(db_path, audit, clock, SimulatedFaultyNarrator()).run(risk)
    first, second = case.draft_rounds[0], case.draft_rounds[1]
    assert len(first["rejected"]) == 2 and not second["rejected"]
    reasons = " ".join(r for rej in first["rejected"] for r in rej["reasons"])
    assert "fact_value_mismatch" in reasons and "legal_conclusion:fraud" in reasons and "no_evidence_cited" in reasons
    assert not case.withheld and all(c.status == "verified" for c in case.claims)
    assert not any("37" in c.statement or "fraud" in c.statement for c in case.claims)


def test_narrator_that_never_corrects_itself_is_withheld_not_trusted(db_path, audit, clock, risk):
    class Stubborn(SimulatedFaultyNarrator):
        def draft(self, findings, store, risk, feedback=None):
            return super().draft(findings, store, risk, None)

    case = Investigation(db_path, audit, clock, Stubborn()).run(risk)
    assert len(case.draft_rounds) == 3 and len(case.withheld) == 2
    assert all(c.status == "verified" for c in case.claims)


def test_prompt_injection_text_never_reaches_claims_or_narrator_context(inv, risk):
    case = inv.run(risk)
    assert not any("cleared" in c.statement.lower() or "ignore" in c.statement.lower() for c in case.claims)
    ctx = safe_context(case.store)
    assert INJECTION_NOTE not in json.dumps(ctx)
    flagged = [c for c in ctx if c["integrity_flags"]]
    assert len(flagged) == 1 and flagged[0]["free_text_removed"]
    assert case.findings  # the injected "report as cleared" had no effect on the analysis


def test_reviewer_request_closes_the_open_question(inv, risk):
    v1 = inv.run(risk)
    reqs = [{"tool": "list_invoices", "entity_id": e, "role": "any"} for e in ("E021", "E022")]
    v2 = inv.review(v1, ReviewDecision(v1.case_id, "request_evidence", "reviewer-01", "need link",
                                       tuple(reqs), "t"))
    assert v1.status == "EVIDENCE_REQUESTED" and v2.version == 2
    assert codes(v2)["closed_invoice_chain"] == "confirmed" and "candidate_invoice_chain" not in codes(v2)
    assert v2.scope == ["E017", "E021", "E022"]
    chain = next(c for c in v2.claims if "closed chain" in c.statement)
    assert "E017 -> E021 -> E022 -> E017" in chain.statement and "1,425,000.00" in chain.statement


def test_request_for_an_entity_the_evidence_never_mentions_gets_no_scope(inv, risk):
    v1 = inv.run(risk)
    stranger = "E011"  # never a counterparty of E017 in the synthetic data
    assert not any(stranger in map(str, i.payload.values()) for i in v1.store.items.values())
    v2 = inv.review(v1, ReviewDecision(v1.case_id, "request_evidence", "reviewer-01", "fishing",
                                       ({"tool": "list_invoices", "entity_id": stranger, "role": "any"},), "t"))
    assert stranger not in v2.scope
    assert not any(stranger in map(str, i.payload.values()) for i in v2.store.items.values())


def test_agent_cannot_record_a_decision(inv, risk, audit):
    case = inv.run(risk)
    with pytest.raises(PermissionError):
        inv.review(case, ReviewDecision(case.case_id, "approve", "agent-01", "self", (), "t"))
    assert case.status == "PENDING_REVIEW" and audit.records()[-1]["event"] == "review_denied"


def test_unknown_principal_cannot_record_a_decision(inv, risk):
    case = inv.run(risk)
    with pytest.raises(PermissionError):
        inv.review(case, ReviewDecision(case.case_id, "approve", "ghost", "x", (), "t"))


@pytest.mark.parametrize("decision,status", [("approve", "APPROVED"), ("reject", "CLOSED")])
def test_reviewer_decisions_are_recorded(inv, risk, audit, decision, status):
    case = inv.run(risk)
    out = inv.review(case, ReviewDecision(case.case_id, decision, "reviewer-01", "because", (), "t"))
    assert out.status == status and out.reviews[0]["decision"] == decision
    assert audit.records()[-1]["event"] == "review_decision"


def test_package_is_complete_and_serializable(inv, risk, audit):
    case = inv.run(risk)
    pkg = build_package(case, audit)
    json.dumps(pkg)
    for key in ("summary", "findings", "evidence_matrix", "timeline", "entity_graph", "uncertainty",
                "source_references", "integrity_notes", "audit", "decision_boundary"):
        assert pkg[key] is not None
    assert pkg["audit"]["chain_valid"] and pkg["integrity_notes"][0]["flags"]
    assert all(e["evidence_id"] in pkg["source_references"] for e in pkg["timeline"])
    md = render_markdown(pkg)
    assert "makes no legal finding" in md and "## Evidence matrix" in md


def test_html_report_escapes_content(inv, risk, audit):
    pkg = build_package(inv.run(risk), audit)
    pkg["summary"][0]["statement"] = "<script>alert(1)</script>"
    out = render_html(pkg)
    assert "<script>" not in out and "&lt;script&gt;" in out


def test_llm_adapter_is_a_seam_not_an_implementation(inv, risk):
    with pytest.raises(NotImplementedError):
        LLMNarrator().draft([], None, risk)


def test_end_to_end_demo_writes_all_artifacts_and_keeps_the_audit_chain_valid(tmp_path):
    lines: list[str] = []
    result = run_demo(tmp_path, say=lines.append)
    for name in ("case_v1.json", "case_v2.json", "case_v2.md", "case_v2.html", "audit.db", "synthetic.db"):
        assert (tmp_path / name).exists()
    assert result["audit_valid"] and result["case2"].status == "APPROVED"
    assert all(d.decision == "deny" for _, _, d in result["probes"])
    assert any("hash chain" in line for line in lines)


def test_cli_entry_points(tmp_path):
    assert main(["demo", "--out", str(tmp_path / "o")]) == 0
    assert main(["audit-verify", str(tmp_path / "o" / "audit.db")]) == 0


def test_demo_is_reproducible(tmp_path):
    run_demo(tmp_path / "a", say=lambda s: None)
    run_demo(tmp_path / "b", say=lambda s: None)
    a = Path(tmp_path / "a" / "case_v2.json").read_text(encoding="utf-8")
    b = Path(tmp_path / "b" / "case_v2.json").read_text(encoding="utf-8")
    assert a == b
