#!/usr/bin/env python3
"""Generate news-sitemap.xml — Google News sitemap with articles
published in the last 48 hours.

Google News uses this format to prioritise recent articles for the
Top Stories carousel and News tab. One entry per per-edition page and
per-headline page within the 48-hour window.

Schema: https://www.google.com/schemas/sitemap-news/0.9
Docs:   https://developers.google.com/search/docs/crawling-indexing/sitemaps/news-sitemap

Run from repo root:
    python3 scripts/build-news-sitemap.py
"""
from __future__ import annotations

import datetime as dt
import html as html_lib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "index.html"
OUT = ROOT / "news-sitemap.xml"
SITE_URL = "https://thedailybrief.co.uk"

# Google's recommendation: only include articles ≤ 2 days old.
MAX_AGE_HOURS = 48


def parse_editions(html: str) -> list[dict]:
    """Find every (non-weekly) curated-edition and its items."""
    editions: list[dict] = []
    ed_pat = re.compile(
        r'<div\s+class="curated-edition\s+(morning|evening)"\s+'
        r'data-date="(\d{4}-\d{2}-\d{2})"\s+data-time="(\d{2}:\d{2})"[^>]*?>',
        flags=re.IGNORECASE,
    )
    for m in ed_pat.finditer(html):
        date = m.group(2)
        data_time = m.group(3)
        edition_type = "morning" if int(data_time.split(":")[0]) < 14 else "evening"

        # Block boundaries via depth-counted div
        start = m.end()
        depth = 1
        end = -1
        for nm in re.finditer(r"<div\b|</div>", html[start:]):
            tok = nm.group(0).lower()
            if tok == "</div>":
                depth -= 1
                if depth == 0:
                    end = start + nm.end()
                    break
            else:
                depth += 1
        if end < 0:
            continue
        block = html[start:end]

        # Items with their slugs and headlines
        items: list[dict] = []
        for im in re.finditer(
            r'<div\s+class="curated-item"\s+data-time="\d{2}:\d{2}"\s+data-slug="([^"]+)"[^>]*>',
            block,
        ):
            slug = im.group(1)
            # Find this item's h4
            i_start = im.end()
            i_depth = 1
            i_end = -1
            for jm in re.finditer(r"<div\b|</div>", block[i_start:]):
                tok = jm.group(0).lower()
                if tok == "</div>":
                    i_depth -= 1
                    if i_depth == 0:
                        i_end = i_start + jm.end()
                        break
                else:
                    i_depth += 1
            if i_end < 0:
                continue
            body = block[i_start:i_end]
            h4_m = re.search(r"<h4[^>]*>(.*?)</h4>", body, flags=re.IGNORECASE | re.DOTALL)
            if not h4_m:
                continue
            headline = re.sub(r"<[^>]+>", "", h4_m.group(1))
            headline = html_lib.unescape(headline)
            headline = re.sub(r"\s+", " ", headline).strip()
            items.append({"slug": slug, "headline": headline})

        editions.append({
            "date": date,
            "edition_type": edition_type,
            "data_time": data_time,
            "iso": f"{date}T{data_time}:00+01:00",
            "items": items,
        })
    return editions


def is_recent(iso_published: str, max_age_hours: int) -> bool:
    """True if the publication time is within max_age_hours of now."""
    pub = dt.datetime.fromisoformat(iso_published)
    if pub.tzinfo is None:
        pub = pub.replace(tzinfo=dt.timezone.utc)
    now = dt.datetime.now(tz=dt.timezone.utc)
    age = now - pub
    return age <= dt.timedelta(hours=max_age_hours)


def xml_escape(s: str) -> str:
    return html_lib.escape(s, quote=True)


def main() -> int:
    if not INDEX.exists():
        print("index.html missing", file=sys.stderr)
        return 1
    html = INDEX.read_text(encoding="utf-8")
    editions = parse_editions(html)

    recent = [e for e in editions if is_recent(e["iso"], MAX_AGE_HOURS)]

    lines: list[str] = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"',
        '        xmlns:news="http://www.google.com/schemas/sitemap-news/0.9">',
    ]

    def emit(loc: str, iso: str, title: str) -> None:
        lines.append("  <url>")
        lines.append(f"    <loc>{xml_escape(loc)}</loc>")
        lines.append("    <news:news>")
        lines.append("      <news:publication>")
        lines.append("        <news:name>The Daily Brief</news:name>")
        lines.append("        <news:language>en</news:language>")
        lines.append("      </news:publication>")
        lines.append(f"      <news:publication_date>{xml_escape(iso)}</news:publication_date>")
        lines.append(f"      <news:title>{xml_escape(title)}</news:title>")
        lines.append("    </news:news>")
        lines.append("  </url>")

    months = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December",
    ]
    days = ["Monday", "Tuesday", "Wednesday", "Thursday",
            "Friday", "Saturday", "Sunday"]

    entry_count = 0
    for ed in recent:
        d = dt.date.fromisoformat(ed["date"])
        date_human = f"{days[d.weekday()]} {d.day} {months[d.month - 1]} {d.year}"
        ed_label = "Morning Briefing" if ed["edition_type"] == "morning" else "Evening Briefing"
        ed_url = f"{SITE_URL}/briefings/{ed['date']}-{ed['edition_type']}/"
        emit(ed_url, ed["iso"], f"{ed_label} — {date_human}")
        entry_count += 1
        for it in ed["items"]:
            item_url = f"{SITE_URL}/briefings/{ed['date']}-{ed['edition_type']}/{it['slug']}/"
            emit(item_url, ed["iso"], it["headline"])
            entry_count += 1

    lines.append("</urlset>")
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"news-sitemap.xml: {entry_count} entries from {len(recent)} editions")
    return 0


if __name__ == "__main__":
    sys.exit(main())
