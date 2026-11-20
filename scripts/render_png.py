"""Render SVG -> PNG with headless Chrome or Edge (no extra Python dependencies)."""

from __future__ import annotations

import re
import subprocess
import tempfile
from pathlib import Path

CANDIDATES = [r"C:\Program Files\Google\Chrome\Application\chrome.exe",
              r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
              "/usr/bin/google-chrome", "/usr/bin/chromium"]


def browser() -> str:
    for c in CANDIDATES:
        if Path(c).exists():
            return c
    raise SystemExit("no Chrome/Edge found for PNG rendering")


def svg_size(svg: Path) -> tuple[int, int]:
    head = svg.read_text(encoding="utf-8")[:600]
    m = re.search(r'viewBox="0 0 (\d+) (\d+)"', head)
    return int(m.group(1)), int(m.group(2))


def render(svg: Path, png: Path, scale: int = 2) -> None:
    w, h = svg_size(svg)
    with tempfile.TemporaryDirectory() as prof:
        subprocess.run([browser(), "--headless=new", "--disable-gpu", "--hide-scrollbars",
                        f"--user-data-dir={prof}", f"--force-device-scale-factor={scale}",
                        f"--window-size={w},{h}", f"--screenshot={png}", svg.resolve().as_uri()],
                       check=True, capture_output=True, timeout=120)
