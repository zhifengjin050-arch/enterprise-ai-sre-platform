#!/usr/bin/env python3
"""Render README PNGs from docs/screenshots/html (Playwright).

Usage:
    pip install playwright
    python -m playwright install chromium
    python scripts/render_readme_images.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / "docs" / "screenshots" / "html"
IMAGES = ROOT / "docs" / "images"

MAP = [
    ("architecture.html", IMAGES / "architecture.png", {"width": 1440, "height": 900}),
    ("dashboard.html", IMAGES / "dashboard.png", {"width": 1440, "height": 900}),
    ("agent-chat.html", IMAGES / "agent-chat.png", {"width": 1440, "height": 900}),
    ("kubernetes.html", IMAGES / "kubernetes.png", {"width": 1440, "height": 900}),
]


def main() -> int:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("pip install playwright && python -m playwright install chromium")
        return 1

    IMAGES.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for name, dest, vp in MAP:
            src = HTML / name
            if not src.exists():
                print("missing", src)
                return 1
            page = browser.new_page(viewport=vp, device_scale_factor=2)
            page.goto(src.as_uri(), wait_until="load")
            dest.parent.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(dest), full_page=False)
            print("wrote", dest.relative_to(ROOT))
            page.close()
        browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
