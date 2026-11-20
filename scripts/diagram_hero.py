"""Hero banner for the README."""

import subprocess
import sys
from pathlib import Path

from svgkit import MONO, SANS, Svg

ROOT = Path(__file__).resolve().parent.parent
BG, FG, DIM = "#0F2236", "#EAF0F6", "#93A6BA"
TEAL, AMBER, RED = "#4CC2B4", "#E2A94F", "#F08A7C"
W, H = 1280, 420


def test_count() -> str:
    try:
        out = subprocess.run([sys.executable, "-m", "pytest", "--collect-only", "-q"], cwd=ROOT,
                             capture_output=True, text=True, timeout=120).stdout
        last = [ln for ln in out.splitlines() if "test" in ln and "collected" in ln]
        return last[-1].split()[0] if last else ""
    except Exception:
        return ""


def build() -> Svg:
    S = Svg(W, H, "Proofline: evidence-grounded investigation agent", bg=BG)
    for x in range(0, W, 40):
        S.line(x, 0, x, H, "#16304A", 0.6)
    for y in range(0, H, 40):
        S.line(0, y, W, y, "#16304A", 0.6)
    S.text(64, 84, "REFERENCE PROTOTYPE  /  SYNTHETIC DATA  /  NO API KEY", 15, 700, TEAL, spacing="1.4")
    S.text(64, 170, "Proofline", 76, 700, FG)
    S.text(64, 222, "Evidence-grounded investigation agent.", 26, 400, FG)
    S.text(64, 262, "A risk event goes in. A verified case file comes out.", 21, 400, DIM)
    S.text(64, 296, "A human decides.", 21, 600, AMBER)
    n = test_count()
    S.text(64, 372, "Python standard library only" + (f"  /  {n} tests" if n else "") + "  /  hash-chained audit log", 16, 500, DIM)

    # evidence panel: real lines from `python -m proofline demo`
    S.rect(640, 48, 600, 324, fill="#0B1A2A", stroke="#27425F", sw=1.4, rx=14)
    S.text(664, 86, "claim verification, from the demo run", 16, 700, FG)
    mono = [
        (DIM, "round 1: 7 claims drafted, 5 verified, 2 rejected"),
        (RED, "x C-006 fact_value_mismatch:invoices in month:"),
        (RED, "         claimed 37 actual 11"),
        (RED, "x C-007 legal_conclusion:fraud, ..."),
        (DIM, "round 2: 5 claims drafted, 5 verified, 0 rejected"),
        (TEAL, "+ 5 verified claims go into the case package"),
        (TEAL, "+ reviewer-01 approved: no external action triggered"),
        (RED, "deny  principal agent-01 may not record decisions"),
    ]
    for i, (c, ln) in enumerate(mono):
        S.add(f'<text x="664" y="{124 + i * 31}" font-family="{MONO}" font-size="16" fill="{c}">'
              f'{ln.replace("&", "&amp;").replace("<", "&lt;")}</text>')
    return S
