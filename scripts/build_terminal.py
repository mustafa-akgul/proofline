"""Capture the real `proofline demo` output and render it as an animated terminal SVG
(assets/demo.svg) plus a static PNG (assets/demo.png). Run from the repo root."""

from __future__ import annotations

import os
import re
import subprocess
import sys
from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
from render_png import render  # noqa: E402

BG, FG = "#0F1B2B", "#D6E0EA"
COLORS = {"32": "#5FD0A5", "31": "#F0877A", "33": "#E9B65A"}
FONT = "'Cascadia Mono',Consolas,'DejaVu Sans Mono',monospace"
SIZE, LH, CW = 13.5, 20, 8.4
SGR = re.compile(r"\x1b\[([0-9;]*)m")


def capture() -> list[str]:
    env = {**os.environ, "PROOFLINE_COLOR": "1", "PYTHONPATH": str(ROOT / "src"), "PYTHONIOENCODING": "utf-8"}
    env.pop("NO_COLOR", None)
    out = subprocess.run([sys.executable, "-m", "proofline", "demo", "--out", "out"],
                         capture_output=True, env=env, cwd=ROOT, check=True).stdout.decode("utf-8")
    return out.replace("\r\n", "\n").rstrip("\n").split("\n")


def spans(line: str) -> tuple[str, int]:
    """ANSI line -> SVG tspans, plus its visible length."""
    out, pos, color, bold, dim, n = [], 0, FG, False, False, 0
    def emit(txt):
        nonlocal n
        if not txt:
            return
        n += len(txt)
        style = f'fill="{color}"' + (' font-weight="700"' if bold else "") + (' opacity="0.6"' if dim else "")
        out.append(f'<tspan {style}>{escape(txt)}</tspan>')
    for m in SGR.finditer(line):
        emit(line[pos:m.start()])
        pos = m.end()
        for code in (m.group(1) or "0").split(";"):
            if code in ("0", ""):
                color, bold, dim = FG, False, False
            elif code == "1":
                bold = True
            elif code == "2":
                dim = True
            elif code in COLORS:
                color = COLORS[code]
    emit(line[pos:])
    return "".join(out), n


def build(lines: list[str], animated: bool) -> str:
    parsed = [spans(ln) for ln in lines]
    width = int(max(n for _, n in parsed) * CW + 70)
    width = max(width, 760)
    height = 52 + len(lines) * LH + 28
    css = ("@keyframes show{from{opacity:0}to{opacity:1}}.l{opacity:0;animation:show .01s forwards}"
           if animated else ".l{opacity:1}")
    body, t = [], 0.5
    for i, (markup, n) in enumerate(parsed):
        if animated:
            style = f' style="animation-delay:{t:.2f}s"'
            t += 0.55 if lines[i].strip() == "" else 0.16
            if re.match(r"^\x1b\[1m\d  ", lines[i]):
                t += 0.5
        else:
            style = ""
        body.append(f'<text class="l" x="28" y="{52 + (i + 1) * LH - 6}" xml:space="preserve" '
                    f'font-family="{FONT}" font-size="{SIZE}"{style}>{markup}</text>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" '
            f'height="{height}" role="img" aria-label="Terminal recording of python -m proofline demo">'
            f'<style>{css}</style><rect width="{width}" height="{height}" rx="12" fill="{BG}"/>'
            f'<rect width="{width}" height="36" rx="12" fill="#16273B"/><rect y="24" width="{width}" height="12" fill="#16273B"/>'
            '<circle cx="22" cy="18" r="6" fill="#F0877A"/><circle cx="42" cy="18" r="6" fill="#E9B65A"/>'
            '<circle cx="62" cy="18" r="6" fill="#5FD0A5"/>'
            f'<text x="{width / 2}" y="22" text-anchor="middle" font-family="{FONT}" font-size="12" fill="#7C8FA3">'
            'python -m proofline demo</text>' + "".join(body) + "</svg>")


def main() -> None:
    lines = capture()
    assets = ROOT / "assets"
    (assets / "demo.svg").write_text(build(lines, True), encoding="utf-8")
    static = assets / "_demo_static.svg"
    static.write_text(build(lines, False), encoding="utf-8")
    render(static, assets / "demo.png")
    static.unlink()
    print(f"built demo ({len(lines)} lines)")


if __name__ == "__main__":
    main()
