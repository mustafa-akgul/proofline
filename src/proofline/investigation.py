"""Orchestrator: plan -> collect (through the gateway) -> validate -> analyze -> narrate ->
verify -> package -> human review. Evidence requests from the reviewer re-enter at planning.

A plain state machine rather than a framework: every transition is explicit, audited, and
easy to test. The design notes how the same graph would map onto LangGraph.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from proofline import analysis
from proofline.audit import AuditLog
from proofline.clock import Clock
from proofline.contracts import (Claim, EvidenceItem, Finding, GatewayDecision, ReviewDecision,
                                 RiskEvent, ToolCall)
from proofline.evidence import EvidenceStore, validate
from proofline.gateway import Gateway
from proofline.narrator import Narrator, TemplateNarrator
from proofline.verifier import verify_claims

PURPOSE = "risk-case-investigation"
MAX_DRAFT_ROUNDS = 3


@dataclass
class Case:
    case_id: str
    version: int
    risk: RiskEvent
    scope: list[str]
    store: EvidenceStore
    validation: dict[str, Any]
    findings: list[Finding]
    claims: list[Claim]                       # verified claims only
    withheld: list[Claim]                     # still rejected after the last draft round
    draft_rounds: list[dict[str, Any]]
    gateway_decisions: list[GatewayDecision]
    suggested_requests: list[dict[str, Any]]
    status: str = "PENDING_REVIEW"            # PENDING_REVIEW | APPROVED | CLOSED | EVIDENCE_REQUESTED
    reviews: list[dict[str, Any]] = field(default_factory=list)
    generated_at: str = ""


class Investigation:
    def __init__(self, db_path: str, audit: AuditLog, clock: Clock, narrator: Narrator | None = None,
                 agent_id: str = "agent-01") -> None:
        self.db_path = db_path
        self.audit = audit
        self.clock = clock
        self.narrator = narrator or TemplateNarrator()
        self.agent_id = agent_id
        self.gateway = Gateway(db_path, audit, clock)
        self._call_no = 0
        self.calls: dict[str, ToolCall] = {}

    # -- helpers ----------------------------------------------------------------------
    def _call(self, case_id: str, step: str, tool: str, args: dict[str, Any]) -> ToolCall:
        self._call_no += 1
        call = ToolCall(f"call-{self._call_no:04d}", case_id, step, tool, args, PURPOSE, self.agent_id)
        self.calls[call.call_id] = call
        return call

    def _step(self, case_id: str, step: str, **detail: Any) -> None:
        self.audit.append(self.agent_id, "step", {"case_id": case_id, "step": step, **detail})

    # -- main pipeline ----------------------------------------------------------------
    def run(self, risk: RiskEvent, version: int = 1,
            extra_calls: list[dict[str, Any]] | None = None) -> Case:
        case_id = f"CASE-{risk.risk_id}"
        if not self.gateway.scope(case_id):
            self.gateway.open_case(case_id, [risk.entity_ref], self.agent_id)
        self._step(case_id, "plan", version=version, entity=risk.entity_ref, category=risk.risk_category)

        plan = [("get_entity", {"entity_id": risk.entity_ref}),
                ("list_invoices", {"entity_id": risk.entity_ref, "role": "any"}),
                ("list_transactions", {"entity_id": risk.entity_ref}),
                ("monthly_invoice_summary", {"entity_id": risk.entity_ref})]
        plan += [(c["tool"], {k: v for k, v in c.items() if k not in ("tool", "reason")})
                 for c in (extra_calls or [])]

        store = EvidenceStore(case_id, self.clock)
        decisions: list[GatewayDecision] = []
        for tool, args in plan:
            call = self._call(case_id, "collect", tool, args)
            decision, records = self.gateway.execute(call)
            decisions.append(decision)
            if records is not None:
                store.add(records, call)
        self._step(case_id, "collect", evidence=len(store.items),
                   denied=sum(d.decision == "deny" for d in decisions))

        validation = validate(store, self.db_path)
        self._step(case_id, "validate", validated=validation["validated"],
                   rejected=len(validation["rejected"]), missing=len(validation["missing"]))

        findings = analysis.analyze(store, risk)
        self._step(case_id, "analyze", findings=[f.code for f in findings])

        claims, rounds = self._narrate_and_verify(case_id, findings, store, risk)
        verified = [c for c in claims if c.status == "verified"]
        withheld = [c for c in claims if c.status == "rejected"]

        case = Case(case_id, version, risk, sorted(self.gateway.scope(case_id)), store, validation,
                    findings, verified, withheld, rounds, decisions,
                    self._suggest_requests(findings, validation), generated_at=self.clock.now())
        self._step(case_id, "package", claims_verified=len(verified), claims_withheld=len(withheld))
        return case

    def _narrate_and_verify(self, case_id: str, findings: list[Finding], store: EvidenceStore,
                            risk: RiskEvent) -> tuple[list[Claim], list[dict[str, Any]]]:
        rounds: list[dict[str, Any]] = []
        feedback: list[Claim] | None = None
        claims: list[Claim] = []
        for n in range(1, MAX_DRAFT_ROUNDS + 1):
            claims = verify_claims(self.narrator.draft(findings, store, risk, feedback), store)
            bad = [c for c in claims if c.status == "rejected"]
            rounds.append({"round": n, "drafted": len(claims),
                           "verified": [c.claim_id for c in claims if c.status == "verified"],
                           "rejected": [{"claim_id": c.claim_id, "statement": c.statement,
                                         "reasons": list(c.reasons)} for c in bad]})
            self._step(case_id, "verify", round=n, drafted=len(claims), rejected=len(bad))
            if not bad:
                break
            feedback = bad
        return claims, rounds

    @staticmethod
    def _suggest_requests(findings: list[Finding], validation: dict[str, Any]) -> list[dict[str, Any]]:
        out = []
        for f in findings:
            if f.status == "candidate" and "missing_link" in f.data:
                for ent in (f.data["missing_link"]["from"], f.data["missing_link"]["to"]):
                    out.append({"tool": "list_invoices", "entity_id": ent, "role": "any",
                                "reason": f"Confirm or rule out the connecting invoice ({f.finding_id})"})
        for m in validation["missing"]:
            out.append({"tool": "(none)", "entity_id": "-", "role": "-",
                        "reason": f"Evidence requirement not met: {m['requirement']} "
                                  f"({m['have']} of {m['need']})"})
        return out

    # -- human review -----------------------------------------------------------------
    def review(self, case: Case, decision: ReviewDecision) -> Case:
        """Record a reviewer decision. Only a principal whose role allows it may do so, and an
        approval records the decision; it triggers no external action."""
        if not self.gateway.may_record_decision(decision.reviewer_id):
            self.audit.append(decision.reviewer_id, "review_denied",
                              {"case_id": case.case_id, "decision": decision.decision})
            raise PermissionError(f"principal {decision.reviewer_id} may not record decisions")
        self.audit.append(decision.reviewer_id, "review_decision", {
            "case_id": case.case_id, "version": case.version, "decision": decision.decision,
            "rationale": decision.rationale, "requested": list(decision.requested_evidence)})
        case.reviews.append({"decision": decision.decision, "reviewer_id": decision.reviewer_id,
                             "rationale": decision.rationale, "decided_at": decision.decided_at,
                             "requested_evidence": list(decision.requested_evidence)})
        if decision.decision == "approve":
            case.status = "APPROVED"
            return case
        if decision.decision == "reject":
            case.status = "CLOSED"
            return case
        if decision.decision != "request_evidence":
            raise ValueError(f"unknown decision {decision.decision}")

        case.status = "EVIDENCE_REQUESTED"
        granted: list[dict[str, Any]] = []
        for req in decision.requested_evidence:
            ent = req["entity_id"]
            if ent not in self.gateway.scope(case.case_id):
                just = self._justification_for(case.store, ent)
                if just is None:
                    self.audit.append(decision.reviewer_id, "scope_grant",
                                      {"case_id": case.case_id, "entity_id": ent,
                                       "decision": "deny", "reason": "no_justifying_evidence"})
                    continue
                if self.gateway.grant_scope(case.case_id, ent, decision.reviewer_id, just).decision != "allow":
                    continue
            granted.append(req)
        return self.run(case.risk, version=case.version + 1, extra_calls=granted)

    @staticmethod
    def _justification_for(store: EvidenceStore, entity_id: str) -> EvidenceItem | None:
        for item in store.validated("invoice"):
            if entity_id in (item.payload["issuer_id"], item.payload["recipient_id"]):
                return item
        return None
