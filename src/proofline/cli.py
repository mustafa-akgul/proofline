"""Command line: `python -m proofline demo` runs the whole story end to end."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Callable

from proofline import synth
from proofline.audit import AuditLog
from proofline.casepkg import build_package, render_html, render_markdown
from proofline.clock import Clock, DeterministicClock
from proofline.contracts import ReviewDecision, RiskEvent
from proofline.investigation import PURPOSE, Investigation
from proofline.narrator import SimulatedFaultyNarrator, TemplateNarrator

USE_COLOR = (sys.stdout.isatty() or "PROOFLINE_COLOR" in os.environ) and "NO_COLOR" not in os.environ


def _c(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if USE_COLOR else text


def ok(t: str) -> str: return _c("32", t)
def bad(t: str) -> str: return _c("31", t)
def dim(t: str) -> str: return _c("2", t)
def bold(t: str) -> str: return _c("1", t)
def warn(t: str) -> str: return _c("33", t)


def run_demo(out_dir: Path, live_clock: bool = False, faulty: bool = True,
             say: Callable[[str], None] = print) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    db, audit_path = out_dir / "synthetic.db", out_dir / "audit.db"
    for p in (db, audit_path):
        p.unlink(missing_ok=True)
    clock: Clock = Clock() if live_clock else DeterministicClock()

    say(bold("Proofline demo") + dim("  synthetic data, no API key, scripted human reviewer"))
    counts = synth.generate(str(db))
    say(f"{ok('+')} synthetic data: {counts['entities']} entities, {counts['invoices']} invoices, "
        f"{counts['transactions']} payments")

    risk = RiskEvent(**{**synth.example_risk_event(),
                        "detection_evidence": tuple(synth.example_risk_event()["detection_evidence"]),
                        "source_refs": tuple(synth.example_risk_event()["source_refs"])})
    say(f"{ok('+')} risk event {risk.risk_id}: {risk.entity_ref}, {risk.risk_category} "
        f"{dim('(score ' + str(risk.risk_score) + ', synthetic input)')}")

    audit = AuditLog(str(audit_path), clock)
    inv = Investigation(str(db), audit, clock, SimulatedFaultyNarrator() if faulty else TemplateNarrator())

    say("\n" + bold("1  Governed collection") + dim("  every call passes the policy gateway"))
    case1 = inv.run(risk, version=1)
    for d in case1.gateway_decisions:
        c = inv.calls[d.call_id]
        say(f"   {ok('allow') if d.decision == 'allow' else bad('deny ')} {c.tool} {c.args['entity_id']}  {d.reason}")
    probes = [("freeze_account", {"entity_id": risk.entity_ref}), ("list_invoices", {"entity_id": "E021"}),
              ("flag_entity", {"entity_id": risk.entity_ref})]
    probe_results = []
    for tool, args in probes:
        d, _ = inv.gateway.execute(inv._call(case1.case_id, "probe", tool, args))
        probe_results.append((tool, args, d))
        say(f"   {bad('deny ')} {tool} {args['entity_id']}  {d.reason}")

    v = case1.validation
    say("\n" + bold("2  Deterministic validation") + dim("  re-checked against the source, no model"))
    say(f"   {ok('+')} {v['validated']} evidence records validated, {len(v['rejected'])} rejected, "
        f"{len(v['missing'])} requirements missing")
    if v["flagged_text"]:
        say(f"   {warn('!')} {len(v['flagged_text'])} record carries instruction-like text; "
            f"free text is excluded from narrative input")

    say("\n" + bold("3  Narrative and claim-level verification"))
    for rd in case1.draft_rounds:
        say(f"   round {rd['round']}: {rd['drafted']} claims drafted, {len(rd['verified'])} verified, "
            f"{len(rd['rejected'])} rejected")
        for rej in rd["rejected"]:
            say(f"     {bad('x')} {rej['claim_id']} {dim(', '.join(rej['reasons'])[:96])}")
    say(f"   {ok('+')} {len(case1.claims)} verified claims go into the case package")

    pkg1 = build_package(case1, audit)
    say("\n" + bold("4  Case v1 for human review") + dim(f"  ({len(pkg1['uncertainty'])} open questions)"))
    for u in pkg1["uncertainty"][:2]:
        say(f"   {warn('?')} {u}")

    say("\n" + bold("5  Reviewer requests more evidence") + dim("  (scripted reviewer-01)"))
    requests = [{"tool": s["tool"], "entity_id": s["entity_id"], "role": s["role"]}
                for s in case1.suggested_requests if s["tool"] == "list_invoices"]
    d1 = ReviewDecision(case1.case_id, "request_evidence", "reviewer-01",
                        "Need the connecting invoice before judging the chain.",
                        tuple(requests), inv.clock.now())
    case2 = inv.review(case1, d1)
    say(f"   scope now: {', '.join(case2.scope)}  {dim('(each grant needs validated justifying evidence)')}")
    for f in case2.findings:
        say(f"   {ok('+') if f.status == 'confirmed' else warn('?')} {f.status:<9} {f.title}")

    say("\n" + bold("6  Decision boundary"))
    try:
        inv.review(case2, ReviewDecision(case2.case_id, "approve", inv.agent_id, "self-approval", (), ""))
    except PermissionError as exc:
        say(f"   {bad('deny ')} {exc}")
    case2 = inv.review(case2, ReviewDecision(case2.case_id, "approve", "reviewer-01",
                                             "Evidence package accepted for follow-up.", (), inv.clock.now()))
    say(f"   {ok('+')} reviewer-01 approved: decision recorded, no external action triggered")

    pkg2 = build_package(case2, audit)
    valid, first_bad = audit.verify()
    say(f"\n{bold('Audit')}  {audit.count()} records, hash chain "
        f"{ok('valid') if valid else bad('BROKEN at ' + str(first_bad))}")

    (out_dir / "case_v1.json").write_text(json.dumps(pkg1, indent=2, ensure_ascii=False), encoding="utf-8")
    (out_dir / "case_v2.json").write_text(json.dumps(pkg2, indent=2, ensure_ascii=False), encoding="utf-8")
    (out_dir / "case_v2.md").write_text(render_markdown(pkg2), encoding="utf-8")
    (out_dir / "case_v2.html").write_text(render_html(pkg2), encoding="utf-8")
    say(f"\nWrote {(out_dir / 'case_v2.md').as_posix()} (+ .html, case_v1.json, case_v2.json, audit.db)")
    return {"case1": case1, "case2": case2, "pkg1": pkg1, "pkg2": pkg2, "audit_valid": valid,
            "probes": probe_results, "inv": inv, "audit": audit, "purpose": PURPOSE}


def cmd_audit_verify(path: str) -> int:
    log = AuditLog(path, Clock())
    valid, first_bad = log.verify()
    print(f"{log.count()} records, chain {'valid' if valid else f'BROKEN at seq {first_bad}'}")
    return 0 if valid else 1


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(prog="proofline", description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("demo", help="run the end-to-end demo on synthetic data")
    d.add_argument("--out", default="out", help="output directory (default: out)")
    d.add_argument("--live-clock", action="store_true", help="use wall-clock time instead of the fixed demo clock")
    d.add_argument("--no-faulty-draft", action="store_true", help="skip the simulated faulty first draft")
    a = sub.add_parser("audit-verify", help="verify the hash chain of an audit database")
    a.add_argument("path")
    args = ap.parse_args(argv)
    if args.cmd == "demo":
        run_demo(Path(args.out), args.live_clock, not args.no_faulty_draft)
        return 0
    return cmd_audit_verify(args.path)


if __name__ == "__main__":
    raise SystemExit(main())
