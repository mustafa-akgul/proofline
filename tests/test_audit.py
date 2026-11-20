import sqlite3

import pytest


def test_chain_is_valid_and_links_records(audit):
    for i in range(5):
        audit.append("actor", "event", {"n": i})
    assert audit.verify() == (True, None)
    recs = audit.records()
    assert recs[0]["prev_hash"] == "0" * 64
    assert all(recs[i]["prev_hash"] == recs[i - 1]["hash"] for i in range(1, 5))


def test_update_and_delete_are_rejected(audit):
    audit.append("a", "e", {"x": 1})
    conn = audit.raw_connection()
    with pytest.raises(sqlite3.DatabaseError, match="append-only"):
        conn.execute("UPDATE audit SET actor = 'mallory'")
    with pytest.raises(sqlite3.DatabaseError, match="append-only"):
        conn.execute("DELETE FROM audit")


def test_tampering_by_a_privileged_user_is_detected(audit):
    for i in range(4):
        audit.append("a", "e", {"n": i})
    conn = audit.raw_connection()
    conn.execute("DROP TRIGGER audit_no_update")
    conn.execute("UPDATE audit SET payload = ? WHERE seq = 2", ('{"n":99}',))
    conn.commit()
    assert audit.verify() == (False, 2)


def test_deleting_a_record_is_detected(audit):
    for i in range(4):
        audit.append("a", "e", {"n": i})
    conn = audit.raw_connection()
    conn.execute("DROP TRIGGER audit_no_delete")
    conn.execute("DELETE FROM audit WHERE seq = 2")
    conn.commit()
    ok, bad = audit.verify()
    assert not ok and bad == 3
