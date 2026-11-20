"""Dark variants of the light diagrams, made by remapping the palette.

Each figure is drawn once in the light palette; `to_dark` swaps every colour for its role in a
GitHub-dark palette, so the two variants cannot drift apart. The README chooses one with
<picture> and `prefers-color-scheme`.
"""

from __future__ import annotations

import re

DARK = {
    "#f6f4ee": "#0d1117",  # page
    "#ffffff": "#151c26",  # card
    "#d9d4c7": "#2d3a4a",  # hairline
    "#0f2236": "#e8eef5",  # ink
    "#4a5b6e": "#9fb0c3",  # ink 2
    "#76879a": "#8a9bb0",  # ink 3
    "#8895a3": "#6f8196",  # slate
    "#17324f": "#8fb3dc",  # navy
    "#e6ecf3": "#172536",  # navy tint
    "#1b766f": "#4cc2b4",  # teal
    "#e1efec": "#10272a",  # teal tint
    "#b97a1d": "#e2a94f",  # amber
    "#fbf1dd": "#2b2314",  # amber tint
}


def to_dark(svg: str) -> str:
    return re.sub(r"#[0-9a-fA-F]{6}\b", lambda m: DARK.get(m.group(0).lower(), m.group(0)), svg)
