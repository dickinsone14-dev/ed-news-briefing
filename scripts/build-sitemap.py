#!/usr/bin/env python3
"""Regenerate sitemap.xml from index.html + the generated briefings/ tree.

Lists:
  - the homepage and the four legal pages
  - every /briefings/YYYY-MM-DD-{edition}/ page
  - every /briefings/YYYY-MM-DD-{edition}/{slug}/ page
"""
from __future__ import annotations

import datetime as dt
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "index.html"
SITEMAP = ROOT / "sitemap.xml"
BRIEFINGS_DIR = ROOT / "briefings"
SITE_URL = "https://thedailybrief.co.uk"

TODAY = dt.date.today().isoformat()

STATIC_PAGES = [
    ("/", TODAY, "daily", "1.0"),
    ("/privacy.html", "2026-03-14", "monthly", "0.3"),
    ("/terms.html", "2026-03-14", "monthly", "0.3"),
    ("/cookies.html", "2026-03-14", "monthly", "0.3"),
    ("/subscribe-terms.html", "2026-03-14", "monthly", "0.3"),
]


def main() -> int:
    urls: list[tuple[str, str, str, str]] = list(STATIC_PAGES)

    # Discover per-edition and per-headline pages from the briefings tree
    if BRIEFINGS_DIR.exists():
        for edition_dir in sorted(BRIEFINGS_DIR.iterdir()):
            if not edition_dir.is_dir():
                continue
            # Date is in dir name: e.g. 2026-05-14-morning → 2026-05-14
            m = re.match(r"(\d{4}-\d{2}-\d{2})-(morning|evening)", edition_dir.name)
            if not m:
                continue
            date = m.group(1)
            urls.append((
                f"/briefings/{edition_dir.name}/",
                date, "weekly", "0.9",
            ))
            for item_dir in sorted(edition_dir.iterdir()):
                if not item_dir.is_dir():
                    continue
                if not (item_dir / "index.html").exists():
                    continue
                urls.append((
                    f"/briefings/{edition_dir.name}/{item_dir.name}/",
                    date, "weekly", "0.8",
                ))

    lines: list[str] = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"',
        '        xmlns:news="http://www.google.com/schemas/sitemap-news/0.9">',
    ]
    for loc, lastmod, changefreq, priority in urls:
        lines.append("  <url>")
        lines.append(f"    <loc>{SITE_URL}{loc}</loc>")
        lines.append(f"    <lastmod>{lastmod}</lastmod>")
        lines.append(f"    <changefreq>{changefreq}</changefreq>")
        lines.append(f"    <priority>{priority}</priority>")
        lines.append("  </url>")
    lines.append("</urlset>")

    SITEMAP.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"sitemap.xml: {len(urls)} URLs")
    return 0


if __name__ == "__main__":
    sys.exit(main())
