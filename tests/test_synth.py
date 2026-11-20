import sqlite3

from proofline import synth


def test_generation_is_deterministic(tmp_path):
    a, b = tmp_path / "a.db", tmp_path / "b.db"
    assert synth.generate(str(a)) == synth.generate(str(b))
    q = "SELECT group_concat(invoice_id || amount_cents) FROM invoices"
    assert sqlite3.connect(a).execute(q).fetchone() == sqlite3.connect(b).execute(q).fetchone()


def test_planted_anomalies_exist(db_path):
    c = sqlite3.connect(db_path)
    monthly = dict(c.execute("SELECT substr(issue_date,1,7), COUNT(*) FROM invoices "
                             "WHERE issuer_id='E017' GROUP BY 1"))
    assert monthly["2026-10"] == 11 and all(monthly[f"2026-0{m}"] == 3 for m in range(5, 10))
    ring = c.execute("SELECT issuer_id, recipient_id FROM invoices WHERE invoice_no IN "
                     "('ORC-2026-0900','BAS-2026-0311','COB-2026-0077') ORDER BY issue_date").fetchall()
    assert ring == [("E017", "E021"), ("E021", "E022"), ("E022", "E017")]
    paid_ring = c.execute(
        "SELECT COUNT(*) FROM transactions WHERE ref_invoice_id IN (SELECT invoice_id FROM invoices "
        "WHERE invoice_no IN ('ORC-2026-0900','BAS-2026-0311','COB-2026-0077'))").fetchone()[0]
    assert paid_ring == 0
    assert c.execute("SELECT COUNT(*) FROM invoices WHERE invoice_no='ORC-2026-0107'").fetchone()[0] == 2
    assert c.execute("SELECT COUNT(*) FROM invoices WHERE note LIKE 'SYSTEM NOTE%'").fetchone()[0] == 1
