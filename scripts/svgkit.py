"""Tiny SVG toolkit for the Proofline visuals. Hand-placed layout, text width checked."""

from __future__ import annotations

from html import escape

INK, INK2, INK3 = "#0F2236", "#4A5B6E", "#76879A"
PAPER, CARD, LINE = "#F6F4EE", "#FFFFFF", "#D9D4C7"
TEAL, TEAL_T = "#1B766F", "#E1EFEC"
AMBER, AMBER_T = "#B97A1D", "#FBF1DD"
NAVY, NAVY_T = "#17324F", "#E6ECF3"
SLATE = "#8895A3"
SANS = "'Segoe UI','Helvetica Neue',Arial,sans-serif"
MONO = "'Cascadia Mono',Consolas,'DejaVu Sans Mono',monospace"

WARNINGS: list[str] = []


def tw(s: str, size: float, mono: bool = False, bold: bool = False) -> float:
    """Conservative width estimate in px."""
    k = 0.62 if mono else (0.56 if bold else 0.53)
    return len(s) * size * k


class Svg:
    def __init__(self, w: int, h: int, name: str, bg: str | None = PAPER) -> None:
        self.w, self.h, self.name = w, h, name
        self.parts: list[str] = []
        self.bg = bg

    def add(self, s: str) -> None:
        self.parts.append(s)

    def rect(self, x, y, w, h, fill=CARD, stroke=LINE, sw=1.2, rx=8, dash=None, opacity=None):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        o = f' opacity="{opacity}"' if opacity else ""
        st = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ""
        self.add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}"{st}{d}{o}/>')

    def text(self, x, y, s, size=14, weight=400, fill=INK, anchor="start", mono=False,
             maxw=None, italic=False, spacing=None):
        if maxw is not None and tw(s, size, mono, weight >= 600) > maxw:
            WARNINGS.append(f"[{self.name}] text too wide ({tw(s, size, mono, weight >= 600):.0f}>{maxw}): {s[:50]}")
        fam = MONO if mono else SANS
        it = ' font-style="italic"' if italic else ""
        ls = f' letter-spacing="{spacing}"' if spacing else ""
        self.add(f'<text x="{x}" y="{y}" font-family="{fam}" font-size="{size}" font-weight="{weight}" '
                 f'fill="{fill}" text-anchor="{anchor}"{it}{ls}>{escape(s)}</text>')

    def line(self, x1, y1, x2, y2, stroke=LINE, sw=1.2, dash=None):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.add(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def path(self, pts, stroke=NAVY, sw=1.8, dash=None, arrow=True, color_id=None):
        d = "M" + " L".join(f"{x},{y}" for x, y in pts)
        da = f' stroke-dasharray="{dash}"' if dash else ""
        m = f' marker-end="url(#a-{color_id or self._cid(stroke)})"' if arrow else ""
        self.add(f'<path d="{d}" fill="none" stroke="{stroke}" stroke-width="{sw}"{da} '
                 f'stroke-linejoin="round" stroke-linecap="round"{m}/>')

    @staticmethod
    def _cid(color: str) -> str:
        return color.lstrip("#")

    def pill(self, x, y, label, kind="built", size=10.5):
        """Status pill. kind: built | design | sim"""
        w = tw(label, size, bold=True) + 16
        if kind == "built":
            self.rect(x, y, w, 20, fill=TEAL_T, stroke=TEAL, sw=1, rx=10)
            col = TEAL
        elif kind == "sim":
            self.rect(x, y, w, 20, fill=AMBER_T, stroke=AMBER, sw=1, rx=10)
            col = AMBER
        else:
            self.rect(x, y, w, 20, fill="none", stroke=SLATE, sw=1, rx=10, dash="4 3")
            col = INK3
        self.text(x + w / 2, y + 14, label, size, 700, col, "middle", spacing="0.6")
        return w

    def render(self) -> str:
        ids = {c: self._cid(c) for c in (NAVY, TEAL, AMBER, SLATE, INK)}
        defs = "".join(
            f'<marker id="a-{i}" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="7" markerHeight="7" '
            f'orient="auto-start-reverse"><path d="M1,1 L9,5 L1,9 z" fill="{c}"/></marker>'
            for c, i in ids.items())
        bg = f'<rect width="{self.w}" height="{self.h}" fill="{self.bg}"/>' if self.bg else ""
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.w} {self.h}" width="{self.w}" '
                f'height="{self.h}" role="img" aria-label="{escape(self.name)}"><defs>{defs}</defs>{bg}'
                + "".join(self.parts) + "</svg>")

    def save(self, path: str) -> None:
        open(path, "w", encoding="utf-8").write(self.render())
