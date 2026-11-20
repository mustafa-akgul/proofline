"""Policy and tool gateway: the single execution boundary for every tool call.

Checks, in order: identity, case state, tool exists, role grants the tool, tool is
read-only, purpose, scope, row limit. Every decision and every result is appended to the
audit log. The data connection is opened read-only (`mode=ro`, `query_only`), so even a
gateway bug cannot write to the source data.

The policy is plain JSON evaluated by Python. The design maps it onto Open Policy Agent
(Rego); that mapping is not implemented in this prototype.
"""

from __future__ import annotations

import json
import sqlite3
from importlib import resources
from pathlib import Path
from typing import Any

from proofline.audit import AuditLog
from proofline.clock import Clock
from proofline.contracts import EvidenceItem, GatewayDecision, ToolCall
from proofline.tools import REGISTRY


def load_policy(path: str | Path | None = None) -> dict[str, Any]:
    if path is not None:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    return json.loads(resources.files("proofline").joinpath("policy.json").read_text("utf-8"))


def open_readonly(db_path: str) -> sqlite3.Connection:
    uri = Path(db_path).resolve().as_uri() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.execute("PRAGMA query_only = ON")
    return conn


class Gateway:
    def __init__(self, db_path: str, audit: AuditLog, clock: Clock,
                 policy: dict[str, Any] | None = None) -> None:
        self.policy = policy or load_policy()
        self.audit = audit
        self.clock = clock
        self._conn = open_readonly(db_path)
        self._scopes: dict[str, set[str]] = {}

    # -- case scope -------------------------------------------------------------------
    def open_case(self, case_id: str, entity_ids: list[str], principal_id: str) -> None:
        self._scopes[case_id] = set(entity_ids)
        self.audit.append(principal_id, "case_opened",
                          {"case_id": case_id, "scope": sorted(entity_ids)})

    def scope(self, case_id: str) -> set[str]:
        return set(self._scopes.get(case_id, ()))

    def grant_scope(self, case_id: str, entity_id: str, principal_id: str,
                    justification: EvidenceItem) -> GatewayDecision:
        """Extending the scope needs a role that may do it, a case that exists, room under
        the scope cap, and a validated evidence record that actually mentions the entity."""
        role = self._role_of(principal_id)
        cfg = self.policy["roles"].get(role or "", {})
        reason = "ok"
        if role is None:
            reason = "unknown_principal"
        elif not cfg.get("can_expand_scope", False):
            reason = "role_cannot_expand_scope"
        elif case_id not in self._scopes:
            reason = "unknown_case"
        elif len(self._scopes[case_id]) >= cfg.get("max_scope_entities", 0):
            reason = "scope_cap_reached"
        elif justification.validation_status != "validated":
            reason = "justification_not_validated"
        elif entity_id not in {str(v) for v in justification.payload.values()}:
            reason = "justification_does_not_mention_entity"
        allowed = reason == "ok"
        if allowed:
            self._scopes[case_id].add(entity_id)
        decision = GatewayDecision(f"scope:{case_id}:{entity_id}", "allow" if allowed else "deny",
                                   reason, self.policy["policy_ref"], role or "unknown",
                                   self.clock.now())
        self.audit.append(principal_id, "scope_grant",
                          {"case_id": case_id, "entity_id": entity_id,
                           "justification": justification.evidence_id, "decision": decision.decision,
                           "reason": reason})
        return decision

    # -- authorization ----------------------------------------------------------------
    def _role_of(self, principal_id: str) -> str | None:
        p = self.policy["principals"].get(principal_id)
        return p["role"] if p else None

    def authorize(self, call: ToolCall) -> GatewayDecision:
        role = self._role_of(call.principal_id)
        reason = "ok"
        spec = REGISTRY.get(call.tool)
        cfg = self.policy["roles"].get(role or "", {})
        if role is None:
            reason = "unknown_principal"
        elif call.case_id not in self._scopes:
            reason = "unknown_case"
        elif spec is None:
            reason = "unknown_tool"
        elif spec.access != "read":
            reason = f"read_only_violation:{spec.access}_tool"
        elif call.tool not in cfg.get("tools", []):
            reason = "tool_not_granted_to_role"
        elif call.purpose not in cfg.get("purposes", []):
            reason = "purpose_not_permitted"
        else:
            for arg in spec.entity_args:
                if call.args.get(arg) not in self._scopes[call.case_id]:
                    reason = f"out_of_scope:{call.args.get(arg)}"
                    break
        return GatewayDecision(call.call_id, "allow" if reason == "ok" else "deny", reason,
                               self.policy["policy_ref"], role or "unknown", self.clock.now())

    def execute(self, call: ToolCall) -> tuple[GatewayDecision, list[dict[str, Any]] | None]:
        decision = self.authorize(call)
        self.audit.append(call.principal_id, "tool_decision", {
            "call_id": call.call_id, "case_id": call.case_id, "step": call.step, "tool": call.tool,
            "args": call.args, "purpose": call.purpose, "decision": decision.decision,
            "reason": decision.reason})
        if decision.decision == "deny":
            return decision, None
        limit = self.policy["roles"][decision.role]["max_rows"]
        records = REGISTRY[call.tool].fn(self._conn, call.args, limit)
        if len(records) > limit:
            denied = GatewayDecision(call.call_id, "deny", "row_limit_exceeded",
                                     decision.policy_ref, decision.role, self.clock.now())
            self.audit.append(call.principal_id, "tool_result",
                              {"call_id": call.call_id, "outcome": "row_limit_exceeded"})
            return denied, None
        self.audit.append(call.principal_id, "tool_result",
                          {"call_id": call.call_id, "outcome": "ok", "records": len(records)})
        return decision, records

    # -- human decisions --------------------------------------------------------------
    def may_record_decision(self, principal_id: str) -> bool:
        role = self._role_of(principal_id)
        return bool(role and self.policy["roles"][role].get("can_record_decision", False))
