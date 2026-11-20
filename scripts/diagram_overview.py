"""README overview: the five stages in large type, so it stays legible at GitHub's column width.

The one-page executive and engineering diagrams carry the detail; this one carries the idea.
"""

from svgkit import AMBER, AMBER_T, INK, INK2, NAVY, SLATE, TEAL, TEAL_T, Svg

W, H = 1200, 540
CARD_W, CARD_H, GAP, X0, Y0 = 200, 150, 24, 52, 118

STAGES = [
    ("1", "Plan and collect", ["Every tool call goes", "through the gateway"], "CODE", TEAL, TEAL_T),
    ("2", "Validate", ["Re-read from source,", "check the numbers"], "CODE", TEAL, TEAL_T),
    ("3", "Narrate", ["A model may draft", "claims, nothing more"], "DRAFT", SLATE, "#FFFFFF"),
    ("4", "Verify claims", ["Recompute each figure,", "no legal conclusions"], "CODE", TEAL, TEAL_T),
    ("5", "Human review", ["Approve, reject or", "ask for more evidence"], "HUMAN", AMBER, AMBER_T),
]


def build() -> Svg:
    S = Svg(W, H, "Proofline overview")
    S.text(52, 62, "How Proofline works", 30, 700, INK)
    S.text(52, 94, "A model may draft. Code decides what is true. A human decides what to do.", 19, 400, INK2)

    xs = []
    for i, (num, title, lines, tag, stroke, fill) in enumerate(STAGES):
        x = X0 + i * (CARD_W + GAP)
        xs.append(x + CARD_W / 2)
        dash = "6 4" if tag == "DRAFT" else None
        S.rect(x, Y0, CARD_W, CARD_H, fill=fill, stroke=stroke, sw=2, rx=12, dash=dash)
        S.text(x + 18, Y0 + 34, num, 17, 700, stroke)
        S.text(x + CARD_W - 18, Y0 + 34, tag, 14, 700, stroke, anchor="end", spacing="1.2")
        S.text(x + 18, Y0 + 74, title, 21, 650, INK, maxw=CARD_W - 36)
        for j, ln in enumerate(lines):
            S.text(x + 18, Y0 + 106 + j * 24, ln, 16, 400, INK2, maxw=CARD_W - 28)
        if i < len(STAGES) - 1:
            S.path([(x + CARD_W + 3, Y0 + CARD_H / 2), (x + CARD_W + GAP - 3, Y0 + CARD_H / 2)], stroke=NAVY)

    bottom = Y0 + CARD_H
    # rejected claims go back to the narrator
    S.path([(xs[3], bottom + 4), (xs[3], bottom + 44), (xs[2], bottom + 44), (xs[2], bottom + 6)],
           stroke=AMBER, dash="6 4")
    S.text((xs[2] + xs[3]) / 2, bottom + 70, "rejected: rewrite", 16, 600, AMBER, anchor="middle")
    # the reviewer can widen the evidence
    S.path([(xs[4], bottom + 4), (xs[4], bottom + 96), (xs[0], bottom + 96), (xs[0], bottom + 6)],
           stroke=AMBER, dash="6 4")
    S.text((xs[0] + xs[2]) / 2, bottom + 122, "more evidence requested: re-plan", 16, 600, AMBER, anchor="middle")

    # the gateway and the audit log sit under everything
    S.rect(52, 420, 1096, 78, fill="#FFFFFF", stroke=NAVY, sw=1.6, rx=12)
    S.text(76, 452, "Policy and tool gateway", 19, 700, NAVY)
    S.text(76, 480, "Read-only, scoped per call, role-checked. Every decision goes into a hash-chained audit log.",
           16, 400, INK2, maxw=1040)
    return S
