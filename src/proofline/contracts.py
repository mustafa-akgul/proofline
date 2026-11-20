"""Data contracts exchanged between pipeline components."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class RiskEvent:
    """Output of an upstream detector. Proofline treats it as an untrusted input."""

    risk_id: str
    entity_ref: str
    risk_category: str
    risk_score: float
    detection_evidence: tuple[str, ...]
    source_refs: tuple[str, ...]
    timestamp: str


@dataclass(frozen=True)
class ToolCall:
    call_id: str
    case_id: str
    step: str
    tool: str
    args: dict[str, Any]
    purpose: str
    principal_id: str


@dataclass(frozen=True)
class GatewayDecision:
    call_id: str
    decision: str  # "allow" | "deny"
    reason: str
    policy_ref: str
    role: str
    checked_at: str


@dataclass
class EvidenceItem:
    evidence_id: str
    source_system: str
    record_ref: str
    retrieved_at: str
    kind: str  # entity_profile | invoice | transaction | monthly_summary
    provenance: dict[str, Any]
    payload: dict[str, Any]
    validation_status: str = "pending"  # pending | validated | rejected
    validation_notes: list[str] = field(default_factory=list)
    text_flags: list[str] = field(default_factory=list)


@dataclass
class Finding:
    finding_id: str
    code: str
    title: str
    status: str  # confirmed | candidate
    evidence_ids: list[str]
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class Fact:
    """A number the claim states, recomputable from cited evidence."""

    label: str
    agg: str  # sum | count | max | min | median | count_where
    field: str | None
    evidence_ids: list[str]
    value: float
    unit: str  # count | money
    pred: str | None = None


@dataclass
class Claim:
    claim_id: str
    statement: str
    kind: str  # observation | hypothesis
    evidence_ids: list[str]
    facts: list[Fact] = field(default_factory=list)
    checks: list[dict[str, Any]] = field(default_factory=list)
    status: str = "pending"  # pending | verified | rejected
    reasons: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ReviewDecision:
    case_id: str
    decision: str  # approve | reject | request_evidence
    reviewer_id: str
    rationale: str
    requested_evidence: tuple[dict[str, Any], ...] = ()
    decided_at: str = ""


def to_dict(obj: Any) -> dict[str, Any]:
    return asdict(obj)
