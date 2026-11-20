"""Build every SVG/PNG in assets/. Run from the repo root: python scripts/build_visuals.py"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import svgkit  # noqa: E402
from render_png import render  # noqa: E402

ASSETS = HERE.parent / "assets"


def main(only: list[str] | None = None) -> None:
    ASSETS.mkdir(exist_ok=True)
    jobs = {}
    import diagram_executive
    jobs["architecture-executive"] = diagram_executive.build
    import diagram_overview
    jobs["overview"] = diagram_overview.build
    import diagram_social
    jobs["social-preview"] = diagram_social.build
    try:
        import diagram_engineering
        jobs["architecture-engineering"] = diagram_engineering.build
        import diagram_loop
        jobs["claim-verification-loop"] = diagram_loop.build
        import diagram_hero
        jobs["hero"] = diagram_hero.build
    except ImportError:
        pass
    for name, fn in jobs.items():
        if only and name not in only:
            continue
        S = fn()
        svg = ASSETS / f"{name}.svg"
        S.save(str(svg))
        render(svg, ASSETS / f"{name}.png")
        print("built", name)
    for w in svgkit.WARNINGS:
        print("WARN", w)


if __name__ == "__main__":
    main(sys.argv[1:] or None)
