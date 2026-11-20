# Verification

What was run to check this repository, and what came out. Environment: Windows 11, Python 3.11.0, pytest 9.0.2. Nothing below was run against real data.

## Commands and results

| Check | Command | Result |
|---|---|---|
| Unit and integration tests | `python -m pytest -q` | 65 passed, about 4 s |
| Fresh install | new virtualenv, `pip install -e ".[dev]"`, then `python -m proofline demo --out demo_out` from an unrelated directory | exit 0; wrote `audit.db`, `case_v1.json`, `case_v2.json`, `case_v2.md`, `case_v2.html`, `synthetic.db` |
| Tests from the fresh install | `python -m pytest -q` in that virtualenv | 65 passed |
| Audit verification | `proofline audit-verify demo_out/audit.db` | `43 records, chain valid` |
| Demo runtime | `time python -m proofline demo --out out` | about 0.4 s |
| Reproducibility | demo run twice with the fixed demo clock; `examples/case_v2.json` compared with a fresh run | identical (also covered by `test_demo_is_reproducible`) |
| Asset validity | every `assets/*.svg` parsed as XML | 5 of 5 parse |
| Brand and origin scan | case-insensitive grep of the repository for the names of the vendor, products and agencies the concept was originally written around | no matches |

## Demo output that the documentation quotes

From `python -m proofline demo`, deterministic clock:

- synthetic data: 25 entities, 269 invoices, 226 payments
- 57 evidence records validated, 0 rejected, 0 requirements missing
- round 1: 7 claims drafted, 5 verified, 2 rejected (`fact_value_mismatch:invoices in month:claimed 37 actual 11`; `legal_conclusion:committed, legal_conclusion:fraud, no_evidence_cited, uncited_record_id:E017`)
- round 2: 5 claims drafted, 5 verified
- version 1 finds a *candidate* chain; after the reviewer's evidence request, version 2 confirms the closed chain E017 -> E021 -> E022 -> E017
- agent attempt to record a decision: denied; reviewer approval recorded
- audit: 43 records, hash chain valid

The faulty first draft and the reviewer are scripted. They demonstrate the mechanism; they are not measurements of a model or a person.

## Ground-truth cross-checks in the tests

- The planted anomalies exist in the generated database (11 invoices issued by E017 in 2026-10 against 3 per month before; the three-party ring; no payments against the ring invoices; one reused invoice number; one instruction-like note).
- The October invoice count stated in the volume claim equals a direct SQL count.
- The injected note is flagged, excluded from the narrator context, absent from every claim, and leaves the findings unchanged.

## Visual checks

Each PNG was rendered with headless Chrome and inspected: executive architecture, engineering architecture, claim verification loop, hero banner, terminal recording. Issues found and fixed during inspection: overlapping connector labels, a connector passing through zone captions, text overflowing cards, and an absolute local path appearing in the terminal recording (the CLI now prints a relative path).

## Not verified

- Rendering on GitHub of the animated SVG (`assets/demo.svg`). A static `assets/demo.png` is provided as a fallback.
- Other operating systems and Python versions. The project targets Python 3.11 or newer and uses only the standard library.
- Any behaviour with a real language model. The `LLMNarrator` interface raises `NotImplementedError`, and a test asserts that.
- Any real data source, detector or reviewer workflow.
