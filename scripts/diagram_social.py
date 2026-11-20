"""Social preview card (1280x640) for the repository settings."""

from svgkit import AMBER, INK2, SLATE, TEAL, Svg

W, H = 1280, 640
BG, FG, DIM = "#0F2236", "#EAF0F6", "#93A6BA"


def build() -> Svg:
    S = Svg(W, H, "Proofline social preview", bg=BG)
    for x in range(0, W, 40):
        S.line(x, 0, x, H, "#16304A", 0.6)
    for y in range(0, H, 40):
        S.line(0, y, W, y, "#16304A", 0.6)
    S.text(96, 190, "REFERENCE PROTOTYPE  /  SYNTHETIC DATA", 20, 700, "#4CC2B4", spacing="1.6")
    S.text(96, 300, "Proofline", 112, 700, FG)
    S.text(96, 372, "An investigation agent that cannot", 36, 400, FG)
    S.text(96, 418, "assert what it cannot prove.", 36, 400, FG)
    S.text(96, 490, "A human decides.", 30, 600, "#E2A94F")
    S.text(96, 560, "Python stdlib only  /  65 tests  /  hash-chained audit log", 22, 500, DIM)
    return S
