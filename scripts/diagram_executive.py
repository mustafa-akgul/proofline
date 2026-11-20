"""Executive architecture: one page, readable in about thirty seconds."""

from svgkit import (AMBER, AMBER_T, CARD, INK, INK2, INK3, LINE, NAVY, SLATE, TEAL, TEAL_T, Svg, tw)

W, H = 1600, 1000


def card(S, x, y, w, h, title, lines, tag, kind="built", stroke=LINE, num=None, fill=CARD,
         title_size=16.5, line_gap=19, first=56, ty=33):
    S.rect(x, y, w, h, fill=fill, stroke=stroke, sw=1.4, rx=10, dash="6 4" if kind == "design" else None)
    tx = x + 18
    if num:
        S.rect(x + 14, y + 14, 26, 26, fill=NAVY, stroke=None, rx=13)
        S.text(x + 27, y + 32, str(num), 13, 700, "#FFFFFF", "middle")
        tx = x + 54
    pw = tw(tag, 10.5, bold=True) + 16
    S.text(tx, y + ty, title, title_size, 650, INK, maxw=w - (tx - x) - pw - 28)
    for i, ln in enumerate(lines):
        S.text(tx, y + first + i * line_gap, ln, 13, 400, INK2, maxw=w - (tx - x) - 16)
    S.pill(x + w - pw - 12, y + 14, tag, kind)


def build() -> Svg:
    S = Svg(W, H, "Proofline executive architecture")
    S.text(48, 62, "Proofline", 34, 700, INK)
    S.text(48, 92, "From a risk event to a verified, traceable case file. A human decides.", 17, 400, INK2)
    S.text(W - 48, 52, "Executive architecture", 14, 650, INK, "end")
    S.text(W - 48, 72, "Reference prototype on synthetic data", 12.5, 400, INK3, "end")
    S.line(48, 112, W - 48, 112, LINE, 1.2)

    for x, w, label in ((48, 370, "A   Input"), (458, 680, "B   Investigation"), (1178, 374, "C   Output and control")):
        S.text(x, 146, label, 15, 700, INK)
        S.line(x, 156, x + w, 156, NAVY, 1.6)

    # ---- A: input
    card(S, 48, 184, 370, 124, "Upstream risk detector",
         ["Pluggable: rules, anomaly models, graph", "scores. Out of scope here. Emits a", "RiskEvent, which is implemented."],
         "DESIGN", "design")
    card(S, 48, 344, 370, 148, "Governed data sources",
         ["Invoices, payments, entity records.", "Prototype: synthetic SQLite, read-only.", "Design: PostgreSQL, or Trino on Iceberg."],
         "SYNTHETIC", "sim")

    # ---- B: investigation
    S.rect(458, 168, 680, 604, fill="#FFFFFF", stroke=NAVY, sw=2, rx=14)
    steps = [
        ("Plan", "Fixed plan per risk category.", "Reviewer requests re-enter here."),
        ("Policy and tool gateway", "Identity, role, read-only, purpose, scope, row limit.", "Every decision is audited. Design: OPA."),
        ("Evidence collection", "Records become evidence items with provenance:", "tool, query, parameters and call id."),
        ("Deterministic validation", "Re-check each record against the source, check", "numeric sanity, report what is missing."),
        ("Relationship and timeline analysis", "Rule-based patterns on validated evidence only.", "A graph database is a design option."),
        ("Narrative", "Findings become claims. Template narrator;", "the LLM adapter is a design seam."),
        ("Claim-level verification", "Every number recomputed, every id cited, no legal", "conclusions. Rejected claims go back to step 6."),
    ]
    ys = []
    for k, (title, l1, l2) in enumerate(steps):
        y = 184 + k * 84
        ys.append(y)
        trusted = k in (3, 6)
        card(S, 478, y, 640, 70, title, [], "BUILT", "built", stroke=TEAL if trusted else LINE, num=k + 1, ty=30)
        S.text(532, y + 48, l1, 13, 400, INK2, maxw=560)
        S.text(532, y + 62, l2, 13, 400, INK2, maxw=560)
        if k < len(steps) - 1:
            S.path([(798, y + 70), (798, y + 84)], NAVY, 1.8)
    # step 7 -> 6 rejection loop, inside the container padding
    S.path([(1118, ys[6] + 22), (1130, ys[6] + 22), (1130, ys[5] + 40), (1118, ys[5] + 40)], AMBER, 1.6, dash="5 4")

    # ---- C: output and control
    card(S, 1178, 184, 374, 176, "Human review",
         ["Approve, reject, or request more", "evidence (dashed arrow to step 1).", "Only a human role may record a", "decision. An approval triggers no action."],
         "BUILT", "built", stroke=AMBER, fill=AMBER_T)
    card(S, 1178, 412, 374, 160, "Review-ready case package",
         ["Verified claims, findings, evidence", "matrix, timeline, entity graph, open", "questions, source references. JSON,", "Markdown and HTML."],
         "BUILT", "built")
    S.text(1178, 612, "Boundary", 13, 700, INK)
    for i, ln in enumerate(["No legal finding, no verdict, no", "enforcement tool. Read-only by policy", "and by the database handle."]):
        S.text(1178, 632 + i * 19, ln, 13, 400, INK2)

    # ---- connectors
    S.path([(418, 219), (478, 219)], NAVY, 1.8)
    S.path([(418, 418), (448, 418), (448, 332), (478, 332)], SLATE, 1.8)
    S.path([(1118, ys[6] + 44), (1148, ys[6] + 44), (1148, 492), (1178, 492)], TEAL, 1.8)
    S.path([(1365, 412), (1365, 360)], NAVY, 1.8)
    S.path([(1178, 219), (1118, 219)], AMBER, 1.8, dash="6 4")

    # ---- audit band
    S.rect(458, 790, 1094, 46, fill="#FFFFFF", stroke=TEAL, sw=1.6, rx=10)
    S.text(478, 818, "Audit trail", 14.5, 700, TEAL)
    S.text(578, 818, "Append-only, hash-chained log of every gateway decision, step and review decision. Anchoring the head hash externally is a design item.", 13, 400, INK2, maxw=960)
    S.pill(1470, 803, "BUILT", "built")

    # ---- bottom bands
    S.rect(48, 856, 700, 108, fill="#FFFFFF", stroke=LINE, rx=10)
    S.text(68, 884, "How to read this", 14.5, 700, INK)
    xx = 68
    for label, kind, note in (("BUILT", "built", "in this repo, covered by tests"),
                              ("SYNTHETIC", "sim", "stand-in data"),
                              ("DESIGN", "design", "described, not implemented")):
        w = S.pill(xx, 898, label, kind)
        S.text(xx + w + 8, 912, note, 12.5, 400, INK2)
        xx += w + 8 + tw(note, 12.5) + 22
    S.text(68, 940, "Solid teal outline: trusted deterministic checks. Amber: human control and rejection loops.", 12.5, 400, INK3)

    S.rect(768, 856, 784, 108, fill="#FFFFFF", stroke=LINE, rx=10)
    S.text(788, 884, "Open-source building blocks named in the design (not integrated in the prototype)", 14.5, 700, INK, maxw=744)
    chips = ["LangGraph", "MCP", "Open Policy Agent", "Trino + Iceberg", "PostgreSQL", "OpenTelemetry", "OpenLineage", "Apache AGE / Neo4j"]
    cx, cy = 788, 900
    for c in chips:
        w = tw(c, 12.5, bold=True) + 22
        if cx + w > 1530:
            cx, cy = 788, cy + 28
        S.rect(cx, cy, w, 22, fill="#F6F4EE", stroke=LINE, sw=1, rx=11)
        S.text(cx + w / 2, cy + 15.5, c, 12.5, 600, INK2, "middle")
        cx += w + 8
    return S
