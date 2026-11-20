import sqlite3

import pytest

from proofline.contracts import ToolCall
from proofline.evidence import EvidenceStore, validate
from proofline.gateway import Gateway, load_policy

PURPOSE = "risk-case-investigation"


def call(tool, entity="E017", principal="agent-01", purpose=PURPOSE, case="C1", **extra):
    return ToolCall("c-1", case, "collect", tool, {"entity_id": entity, **extra}, purpose, principal)


@pytest.fixture
def gw(db_path, audit, clock):
    g = Gateway(db_path, audit, clock)
    g.open_case("C1", ["E017"], "agent-01")
    return g


def test_in_scope_read_is_allowed_and_audited(gw, audit):
    decision, records = gw.execute(call("get_entity"))
    assert decision.decision == "allow" and records and records[0]["payload"]["entity_id"] == "E017"
    events = [r["event"] for r in audit.records()]
    assert events.count("tool_decision") == 1 and events.count("tool_result") == 1


@pytest.mark.parametrize("tool,kind", [("freeze_account", "enforcement"), ("issue_notice", "enforcement"),
                                       ("flag_entity", "write")])
def test_write_and_enforcement_tools_are_denied(gw, tool, kind):
    decision, records = gw.execute(call(tool))
    assert decision.decision == "deny" and records is None
    assert decision.reason == f"read_only_violation:{kind}_tool"


def test_out_of_scope_entity_is_denied(gw):
    decision, records = gw.execute(call("list_invoices", entity="E021"))
    assert decision.reason == "out_of_scope:E021" and records is None


@pytest.mark.parametrize("kwargs,reason", [
    ({"principal": "ghost"}, "unknown_principal"),
    ({"purpose": "curiosity"}, "purpose_not_permitted"),
    ({"principal": "reviewer-01", "purpose": "case-review"}, "tool_not_granted_to_role"),
    ({"case": "NOPE"}, "unknown_case"),
])
def test_identity_purpose_and_role_checks(gw, kwargs, reason):
    assert gw.execute(call("get_entity", **kwargs))[0].reason == reason


def test_unknown_tool_is_denied(gw):
    assert gw.execute(call("drop_database"))[0].reason == "unknown_tool"


def test_denied_calls_are_audited_too(gw, audit):
    gw.execute(call("freeze_account"))
    last = audit.records()[-1]
    assert last["event"] == "tool_decision" and '"decision":"deny"' in last["payload"]


def test_row_limit_is_enforced(db_path, audit, clock):
    policy = load_policy()
    policy["roles"]["investigation-agent"]["max_rows"] = 2
    g = Gateway(db_path, audit, clock, policy)
    g.open_case("C1", ["E017"], "agent-01")
    decision, records = g.execute(call("list_invoices", role="any"))
    assert decision.reason == "row_limit_exceeded" and records is None


def test_data_connection_cannot_write(gw):
    with pytest.raises(sqlite3.OperationalError):
        gw._conn.execute("DELETE FROM invoices")
    with pytest.raises(sqlite3.OperationalError):
        gw._conn.execute("INSERT INTO entities VALUES ('X','x','company','2020-01-01','north')")


def _evidence(gw, clock, entity="E017"):
    store = EvidenceStore("C1", clock)
    c = call("list_invoices", entity=entity, role="any")
    _, recs = gw.execute(c)
    store.add(recs, c)
    return store


def test_scope_grant_requires_role_validation_and_mention(gw, db_path, clock):
    store = _evidence(gw, clock)
    validate(store, db_path)
    ring_invoice = next(i for i in store.validated("invoice") if i.payload["recipient_id"] == "E021")
    other = next(i for i in store.validated("invoice") if "E021" not in i.payload.values())

    assert gw.grant_scope("C1", "E021", "agent-01", ring_invoice).reason == "role_cannot_expand_scope"
    assert gw.grant_scope("C1", "E021", "reviewer-01", other).reason == "justification_does_not_mention_entity"
    ring_invoice.validation_status = "pending"
    assert gw.grant_scope("C1", "E021", "reviewer-01", ring_invoice).reason == "justification_not_validated"
    ring_invoice.validation_status = "validated"
    assert gw.grant_scope("C1", "E021", "reviewer-01", ring_invoice).decision == "allow"
    assert "E021" in gw.scope("C1")


def test_scope_is_capped(db_path, audit, clock):
    policy = load_policy()
    policy["roles"]["reviewer"]["max_scope_entities"] = 1
    g = Gateway(db_path, audit, clock, policy)
    g.open_case("C1", ["E017"], "agent-01")
    store = _evidence(g, clock)
    validate(store, db_path)
    item = next(i for i in store.validated("invoice") if i.payload["recipient_id"] == "E021")
    assert g.grant_scope("C1", "E021", "reviewer-01", item).reason == "scope_cap_reached"
