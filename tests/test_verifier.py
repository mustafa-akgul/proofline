import pytest

from proofline.contracts import Claim
from proofline.narrator import TemplateNarrator
from proofline.verifier import make_fact, verify_claim


@pytest.fixture
def case(inv, risk):
    c = inv.run(risk)
    return c


def ids_for(case, **match):
    return [i.evidence_id for i in case.store.validated("invoice")
            if all(i.payload[k] == v for k, v in match.items())]


def test_template_claims_all_verify(case):
    assert case.claims and not case.withheld
    assert all(c.status == "verified" and not c.reasons for c in case.claims)


def test_hallucinated_number_is_caught(case):
    ids = ids_for(case, invoice_no="ORC-2026-0107")
    fact = make_fact("n", "count", None, ids, "count", case.store)
    fact.value = 9
    claim = Claim("X", "Invoice number ORC-2026-0107 appears on 9 invoices from E017.", "observation", ids, [fact])
    verify_claim(claim, case.store)
    assert claim.status == "rejected"
    assert any(r.startswith("fact_value_mismatch") for r in claim.reasons)


def test_number_in_text_without_a_fact_is_caught(case):
    ids = ids_for(case, invoice_no="ORC-2026-0107")
    fact = make_fact("n", "count", None, ids, "count", case.store)
    claim = Claim("X", f"{int(fact.value)} invoices share a number and 450 of them were unpaid.",
                  "observation", ids, [fact])
    verify_claim(claim, case.store)
    assert "ungrounded_number:450" in claim.reasons


def test_fabricated_record_id_is_caught(case):
    ids = ids_for(case, invoice_no="ORC-2026-0107")
    fact = make_fact("n", "count", None, ids, "count", case.store)
    claim = Claim("X", f"{int(fact.value)} invoices including INV-0001 share a number.", "observation", ids, [fact])
    verify_claim(claim, case.store)
    assert "uncited_record_id:INV-0001" in claim.reasons


@pytest.mark.parametrize("text", ["E017 committed tax fraud.", "This is a criminal scheme.",
                                  "The entity is guilty of evasion."])
def test_legal_conclusions_are_rejected(case, text):
    ids = ids_for(case, invoice_no="ORC-2026-0107")
    claim = Claim("X", text, "observation", ids)
    verify_claim(claim, case.store)
    assert any(r.startswith("legal_conclusion") for r in claim.reasons)


def test_claim_without_evidence_is_rejected(case):
    claim = Claim("X", "Something happened.", "observation", [])
    verify_claim(claim, case.store)
    assert "no_evidence_cited" in claim.reasons


def test_unvalidated_or_unknown_evidence_is_rejected(case):
    some = case.store.validated("invoice")[0]
    some.validation_status = "rejected"
    claim = Claim("X", "An invoice exists.", "observation", [some.evidence_id, "EV-9999"])
    verify_claim(claim, case.store)
    assert f"evidence_not_validated:{some.evidence_id}" in claim.reasons
    assert "unknown_evidence:EV-9999" in claim.reasons


def test_structural_check_catches_a_chain_that_is_not_closed(case):
    ring = ids_for(case, issuer_id="E017", recipient_id="E021") + ids_for(case, issuer_id="E022", recipient_id="E017")
    claim = Claim("X", "Two invoices form a chain.", "observation", ring,
                  checks=[{"op": "closed_chain", "evidence_ids": ring}])
    verify_claim(claim, case.store)
    assert "check_failed:closed_chain" in claim.reasons


def test_fact_over_evidence_the_claim_does_not_cite_is_rejected(case):
    a, b = ids_for(case, invoice_no="ORC-2026-0107")
    fact = make_fact("n", "count", None, [a, b], "count", case.store)
    claim = Claim("X", "2 invoices share a number.", "observation", [a], [fact])
    verify_claim(claim, case.store)
    assert any(r.startswith("fact_uses_uncited_evidence") for r in claim.reasons)


def test_predicate_fact_is_recomputed_not_trusted(case):
    ids = [i.evidence_id for i in case.store.validated("invoice") if i.payload["issuer_id"] == "E017"][:3]
    fact = make_fact("n", "count_where", None, ids, "count", case.store, pred="tax_mismatch")
    fact.value = 3  # the first three E017 invoices are all correctly taxed
    claim = Claim("X", "3 invoices have a tax mismatch.", "observation", ids, [fact])
    verify_claim(claim, case.store)
    assert any(r.startswith("fact_value_mismatch") for r in claim.reasons)


def test_narrator_uses_only_validated_evidence(case, inv, risk):
    for item in case.store.items.values():
        if item.kind == "monthly_summary":
            item.validation_status = "rejected"
    from proofline import analysis
    assert analysis.volume_finding(case.store, risk) is None
    assert TemplateNarrator().draft(analysis.analyze(case.store, risk), case.store, risk)
