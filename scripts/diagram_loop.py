"""Claim verification loop: why a model's draft is never trusted."""

from svgkit import (AMBER, AMBER_T, CARD, INK, INK2, INK3, LINE, NAVY, SLATE, TEAL, TEAL_T, Svg, tw)

W, H = 1500, 760


def node(S, x, y, w, h, title, lines, stroke=LINE, fill=CARD, title_fill=INK):
    S.rect(x, y, w, h, fill=fill, stroke=stroke, sw=1.5, rx=10)
    S.text(x + 16, y + 28, title, 15.5, 650, title_fill, maxw=w - 28)
    for i, ln in enumerate(lines):
        S.text(x + 16, y + 52 + i * 19, ln, 13, 400, INK2, maxw=w - 28)


def build() -> Svg:
    S = Svg(W, H, "Proofline claim verification loop")
    S.text(48, 60, "Claim verification loop", 28, 700, INK)
    S.text(48, 88, "A model may draft the narrative. Nothing it writes is published until deterministic checks accept it.", 16, 400, INK2)
    S.line(48, 108, W - 48, 108, LINE, 1.2)

    node(S, 48, 160, 210, 110, "Findings and evidence", ["Validated evidence items", "and the findings computed", "from them."])
    node(S, 318, 160, 210, 110, "Narrator", ["Drafts claims: statement,", "cited evidence, numeric", "facts, structural checks."], stroke=AMBER, fill=AMBER_T)
    node(S, 588, 140, 320, 190, "Verifier", ["1  cited evidence exists and is", "    validated", "2  every number recomputed", "3  every record id is cited", "4  structural checks hold", "5  no legal conclusions"], stroke=TEAL, fill=TEAL_T)

    # decision diamond
    cx, cy = 1030, 235
    S.add(f'<polygon points="{cx},{cy - 62} {cx + 78},{cy} {cx},{cy + 62} {cx - 78},{cy}" fill="#FFFFFF" stroke="{NAVY}" stroke-width="1.8"/>')
    S.text(cx, cy - 4, "All claims", 13, 650, INK, "middle")
    S.text(cx, cy + 14, "pass?", 13, 650, INK, "middle")
    node(S, 1176, 180, 276, 110, "Verified claims", ["Go into the case package", "with their evidence links."], stroke=TEAL)

    node(S, 760, 410, 300, 96, "Rejected, with reasons", ["fact_value_mismatch, ungrounded_number,", "uncited_record_id, legal_conclusion ..."], stroke=AMBER, fill=AMBER_T)
    node(S, 1176, 410, 276, 96, "Withheld", ["Still failing after 3 rounds:", "never published."], stroke=SLATE)

    # arrows
    S.path([(258, 215), (318, 215)], NAVY)
    S.path([(528, 215), (588, 215)], NAVY)
    S.path([(908, 235), (952, 235)], NAVY)
    S.path([(1108, 235), (1176, 235)], TEAL)
    S.text(1142, 224, "yes", 12.5, 650, TEAL, "middle")
    S.path([(1030, 297), (1030, 410 - 0)], AMBER, dash="6 4")
    S.text(1042, 360, "no", 12.5, 650, AMBER)
    S.path([(760, 458), (423, 458), (423, 270)], AMBER, dash="6 4")
    S.text(590, 448, "feedback to the narrator, up to 3 rounds", 12.5, 600, AMBER, "middle")
    S.path([(1060, 458), (1176, 458)], SLATE)

    # real example
    S.rect(48, 556, 1404, 164, fill=CARD, stroke=LINE, sw=1.3, rx=12)
    S.text(68, 586, "From the demo run: a simulated faulty first draft, caught", 15.5, 700, INK)
    S.text(68, 606, "Real output of `python -m proofline demo`. The faulty draft is scripted to show the mechanism; it is not a measured model failure rate.", 12.5, 400, INK3)
    rows = [("\"In 2026-10, E017 issued 37 invoices, a sharp jump.\"",
             "fact_value_mismatch:invoices in month:claimed 37 actual 11"),
            ("\"E017 committed tax fraud through a circular invoice scheme.\"",
             "legal_conclusion:committed, legal_conclusion:fraud, no_evidence_cited, uncited_record_id:E017")]
    for i, (claim, why) in enumerate(rows):
        y = 640 + i * 38
        S.rect(68, y - 17, 62, 24, fill=AMBER_T, stroke=AMBER, sw=1, rx=12)
        S.text(99, y, "rejected", 11.5, 700, AMBER, "middle")
        S.text(146, y, claim, 12, 400, INK, mono=True, maxw=600)
        S.text(770, y, why, 11.5, 400, INK2, mono=True, maxw=670)
    return S
