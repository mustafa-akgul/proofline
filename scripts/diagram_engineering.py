"""Engineering architecture: trust zones, modules, data contracts."""

from svgkit import (AMBER, AMBER_T, CARD, INK, INK2, INK3, LINE, MONO, NAVY, NAVY_T, SLATE, TEAL, TEAL_T, Svg, tw)

W, H = 1800, 1170


def zone(S, x, y, w, h, title, sub, fill, stroke, sw=1.4, dash=None):
    S.rect(x, y, w, h, fill=fill, stroke=stroke, sw=sw, rx=14, dash=dash)
    S.text(x + 18, y + 30, title, 15.5, 700, INK, maxw=w - 30)
    S.text(x + 18, y + 49, sub, 12, 400, INK3, maxw=w - 30)


def box(S, x, y, w, h, title, module, lines, stroke=LINE, fill=CARD, audit=False, mono_lines=False):
    S.rect(x, y, w, h, fill=fill, stroke=stroke, sw=1.4, rx=9)
    S.text(x + 14, y + 26, title, 14.5, 650, INK, maxw=w - 28 - (50 if audit else 0))
    S.text(x + 14, y + 44, module, 11.5, 500, INK3, mono=True)
    for i, ln in enumerate(lines):
        S.text(x + 14, y + 68 + i * 17, ln, 12.5, 400, INK2, mono=mono_lines, maxw=w - 24)
    if audit:
        S.rect(x + w - 56, y + 10, 44, 18, fill=TEAL_T, stroke=TEAL, sw=1, rx=9)
        S.text(x + w - 34, y + 23, "audit", 10.5, 700, TEAL, "middle")


def num(S, x, y, n, color=NAVY):
    S.add(f'<circle cx="{x}" cy="{y}" r="9.5" fill="{color}"/>')
    S.text(x, y + 4.2, str(n), 11.5, 700, "#FFFFFF", "middle")


def build() -> Svg:
    S = Svg(W, H, "Proofline engineering architecture")
    S.text(40, 54, "Proofline", 30, 700, INK)
    S.text(40, 82, "Engineering architecture: trust zones, modules and data contracts", 16, 400, INK2)
    S.text(W - 40, 48, "Engineering architecture", 14, 650, INK, "end")
    S.text(W - 40, 68, "Module names refer to src/proofline/", 12.5, 400, INK3, "end")
    S.line(40, 96, W - 40, 96, LINE, 1.2)

    top, bottom = 126, 840
    Z = {"in": (40, 250), "agent": (330, 300), "gate": (670, 300), "trust": (1010, 420), "human": (1470, 290)}
    zone(S, *Z["in"][:1], top, Z["in"][1], bottom - top, "Untrusted input", "treated as data, never as instructions", AMBER_T, AMBER, dash="7 5")
    zone(S, *Z["agent"][:1], top, Z["agent"][1], bottom - top, "Agent zone", "no direct data access", AMBER_T, AMBER, dash="7 5")
    zone(S, *Z["gate"][:1], top, Z["gate"][1], bottom - top, "Policy boundary", "the single execution gate", NAVY_T, NAVY, sw=2.4)
    zone(S, *Z["trust"][:1], top, Z["trust"][1], bottom - top, "Trusted deterministic zone", "no model in this zone", TEAL_T, TEAL, sw=1.8)
    zone(S, *Z["human"][:1], top, Z["human"][1], bottom - top, "Human and records", "decisions stay with people", CARD, SLATE)

    # --- Z1
    box(S, 58, 190, 214, 150, "Risk event", "contracts.RiskEvent",
        ["risk_id, entity_ref,", "risk_category, risk_score,", "detection_evidence[],", "source_refs[], timestamp"])
    S.rect(58, 370, 214, 250, fill=CARD, stroke=LINE, sw=1.2, rx=9)
    S.text(72, 396, "Handled as untrusted", 14, 650, INK)
    for i, ln in enumerate(["Risk score is context only.", "Findings are recomputed", "from validated evidence.", "",
                            "Free-text fields in records", "are flagged if they read like", "instructions, are kept as", "evidence, and are never sent", "to the narrator."]):
        S.text(72, 422 + i * 18, ln, 12.5, 400, INK2)

    # --- Z2
    box(S, 348, 190, 264, 170, "Investigation controller", "investigation.py",
        ["State machine: plan, collect,", "validate, analyze, narrate,", "verify, package, review.", "Draft rounds capped at 3."], audit=True)
    box(S, 348, 560, 264, 214, "Narrator", "narrator.py",
        ["Default: deterministic template.", "LLM adapter: design seam only.", "Sees safe_context(): validated,", "structured fields, free text", "removed. Output is a claim", "draft, trusted by nobody."])

    # --- Z3
    S.rect(688, 190, 264, 376, fill=CARD, stroke=NAVY, sw=1.8, rx=9)
    S.text(702, 216, "Policy and tool gateway", 14.5, 650, INK, maxw=180)
    S.text(702, 234, "gateway.py + policy.json", 11.5, 500, INK3, mono=True)
    S.rect(896, 200, 44, 18, fill=TEAL_T, stroke=TEAL, sw=1, rx=9)
    S.text(918, 213, "audit", 10.5, 700, TEAL, "middle")
    checks = [("1", "identity is a known principal"), ("2", "case exists"), ("3", "tool exists"),
              ("4", "role grants the tool"), ("5", "tool is read-only (write and"), ("", "enforcement tools: always deny)"),
              ("6", "purpose is permitted"), ("7", "every entity id is in scope"), ("8", "row limit not exceeded")]
    for i, (n, ln) in enumerate(checks):
        S.text(702, 262 + i * 19, n, 12, 700, NAVY)
        S.text(724, 262 + i * 19, ln, 12.5, 400, INK2)
    S.line(702, 428, 938, 428, LINE, 1)
    S.text(702, 450, "Scope grants", 13, 650, INK)
    for i, ln in enumerate(["only a role that may expand it,", "cap on entities per case,", "justified by a validated record", "that actually names the entity."]):
        S.text(702, 468 + i * 17, ln, 12.5, 400, INK2)
    S.text(702, 548, "read-only data handle (mode=ro)", 11.5, 500, INK3, mono=True, maxw=240)

    # --- Z4
    box(S, 1028, 190, 384, 130, "Governed tools", "tools.py",
        ["get_entity, list_invoices, list_transactions,", "monthly_invoice_summary: read.", "flag_entity, issue_notice, freeze_account:", "exist so the policy has something to refuse."])
    box(S, 1028, 345, 384, 150, "Evidence store and validation", "evidence.py",
        ["Evidence items carry provenance.", "Re-verify against the source through an", "independent read-only handle; numeric", "sanity; completeness; text flags."])
    box(S, 1028, 520, 384, 110, "Relationship and timeline analysis", "analysis.py",
        ["Volume, closed chains, tax, reused numbers,", "unsettled invoices. Validated items only."])
    box(S, 1028, 650, 384, 160, "Claim verifier", "verifier.py",
        ["Evidence exists and is validated.", "Every number recomputed from evidence.", "Every id cited. Structural checks hold.", "No legal conclusions."], stroke=TEAL)

    # --- Z5
    box(S, 1488, 190, 254, 190, "Human reviewer", "investigation.review()",
        ["approve | reject |", "request_evidence.", "Only roles with", "can_record_decision.", "No action is triggered."], stroke=AMBER, fill=AMBER_T, audit=True)
    box(S, 1488, 590, 254, 220, "Case package", "casepkg.py",
        ["Verified claims, findings,", "evidence matrix, timeline,", "entity graph, open questions,", "source references, integrity", "notes. JSON, Markdown, HTML."])

    # --- arrows
    S.path([(272, 250), (348, 250)], NAVY, 1.8); num(S, 310, 250, 1)
    S.path([(612, 232), (688, 232)], NAVY, 1.8); num(S, 650, 232, 2)
    S.path([(688, 300), (612, 300)], SLATE, 1.8); num(S, 650, 300, 3)
    S.path([(952, 232), (1028, 232)], NAVY, 1.8); num(S, 990, 232, 2)
    S.path([(1220, 320), (1220, 345)], NAVY, 1.8); num(S, 1240, 333, 4)
    S.path([(1220, 495), (1220, 520)], NAVY, 1.8); num(S, 1240, 508, 4)
    S.path([(1028, 600), (612, 600)], NAVY, 1.8); num(S, 820, 600, 5)
    S.path([(612, 700), (1028, 700)], NAVY, 1.8); num(S, 820, 700, 6)
    S.path([(1028, 760), (612, 760)], AMBER, 1.8, dash="6 4"); num(S, 820, 760, 6, AMBER)
    S.text(820, 780, "rejected + reasons", 11.5, 600, AMBER, "middle")
    S.path([(1412, 730), (1488, 730)], TEAL, 1.8); num(S, 1450, 730, 6, TEAL)
    S.path([(1615, 590), (1615, 380)], NAVY, 1.8)
    S.path([(1725, 190), (1725, 114), (560, 114), (560, 190)], AMBER, 1.8, dash="6 4")
    S.rect(1036, 103, 290, 22, fill="#F6F4EE", stroke=None, rx=4)
    num(S, 1050, 114, 7, AMBER)
    S.text(1068, 118, "request_evidence re-enters planning", 11.5, 600, AMBER)

    # --- audit band
    S.rect(40, 860, 1720, 52, fill=CARD, stroke=TEAL, sw=1.6, rx=10)
    S.text(60, 892, "Audit log", 14.5, 700, TEAL)
    S.text(160, 892, "audit.py. Append-only table, SHA-256 hash chain, UPDATE and DELETE rejected by triggers. Records scope grants, gateway decisions, tool results, pipeline steps, review decisions.", 12.5, 400, INK2, maxw=1580)

    # --- contracts
    S.text(40, 944, "Data contracts (dataclasses in contracts.py)", 14.5, 700, INK)
    contracts = [
        ("RiskEvent", ["risk_id, entity_ref,", "risk_category, risk_score,", "detection_evidence[],", "timestamp"]),
        ("ToolCall", ["call_id, case_id, step,", "tool, args, purpose,", "principal_id"]),
        ("GatewayDecision", ["call_id, decision, reason,", "policy_ref, role,", "checked_at"]),
        ("EvidenceItem", ["evidence_id, record_ref,", "provenance, payload,", "validation_status, text_flags"]),
        ("Finding", ["code, status", "(confirmed | candidate),", "evidence_ids[], data"]),
        ("Claim", ["statement, kind,", "evidence_ids[], facts[],", "checks[], status,", "reasons[]"]),
        ("ReviewDecision", ["decision, reviewer_id,", "rationale,", "requested_evidence[]"]),
    ]
    cw = 1720 / 7
    for i, (name, lines) in enumerate(contracts):
        x = 40 + i * cw
        S.rect(x, 958, cw - 10, 120, fill=CARD, stroke=LINE, sw=1.2, rx=9)
        num(S, x + 22, 982, i + 1, AMBER if i == 6 else NAVY)
        S.text(x + 40, 987, name, 13.5, 650, INK, mono=False, maxw=cw - 60)
        for j, ln in enumerate(lines):
            S.text(x + 14, 1012 + j * 18, ln, 11.5, 400, INK2, mono=True, maxw=cw - 28)

    S.text(40, 1130, "Tint: amber = untrusted or non-deterministic, teal = trusted deterministic checks, navy = enforcement boundary. "
                      "Numbered markers on arrows refer to the contracts above.", 12.5, 400, INK3, maxw=1720)
    return S
