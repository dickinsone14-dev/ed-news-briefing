#!/usr/bin/env python3
"""Generate per-edition and per-headline static HTML files for SEO.

Reads index.html, finds every curated-edition and every curated-item
inside, and emits a static file at each of:

    /briefings/YYYY-MM-DD-{morning|evening}/index.html
    /briefings/YYYY-MM-DD-{morning|evening}/{slug}/index.html

Each file is a clone of index.html with overridden <title>, meta
description, canonical URL, Open Graph tags and NewsArticle JSON-LD
schema in the <head>. The body and JS are identical, so the deeplink
routing script (inline in index.html) reads window.location.pathname
on load and switches the day-nav / opens the right headline.

Run from repo root:
    python3 scripts/build-deeplink-pages.py
"""
from __future__ import annotations

import html as html_lib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "index.html"
BRIEFINGS_DIR = ROOT / "briefings"
SITE_URL = "https://thedailybrief.co.uk"

# Months in long form for human-readable titles
MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


@dataclass
class CuratedItem:
    slug: str
    headline: str           # plain text
    summary: str            # plain text first paragraph (the <p>)
    data_time: str          # 'HH:MM'


@dataclass
class Edition:
    date: str               # YYYY-MM-DD
    edition_type: str       # 'morning' or 'evening'
    data_time: str          # 'HH:MM'
    impact_bullets: list[str]  # the impact-box <li> texts (3)
    items: list[CuratedItem]
    iso_published: str      # 'YYYY-MM-DDTHH:MM:00+01:00'

    def url_path(self) -> str:
        return f"/briefings/{self.date}-{self.edition_type}/"


# ── HTML helpers ───────────────────────────────────────────────────

def strip_tags(s: str) -> str:
    """Strip HTML tags and decode entities, return clean plain text."""
    s = re.sub(r"<[^>]+>", "", s)
    s = html_lib.unescape(s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def truncate(s: str, n: int) -> str:
    if len(s) <= n:
        return s
    return s[: n - 1].rstrip() + "…"


def format_date_long(date_iso: str) -> str:
    """'2026-05-14' → 'Thursday 14 May 2026'."""
    import datetime as dt
    d = dt.date.fromisoformat(date_iso)
    return f"{DAYS[d.weekday()]} {d.day} {MONTHS[d.month - 1]} {d.year}"


# ── Parser ─────────────────────────────────────────────────────────

def parse_editions(html: str) -> list[Edition]:
    """Extract all curated-editions and their items from index.html."""
    editions: list[Edition] = []

    # Match each <div class="curated-edition ...">
    ed_pattern = re.compile(
        r'<div\s+class="curated-edition\s+(morning|evening|weekly)"\s+'
        r'data-date="(\d{4}-\d{2}-\d{2})"\s+data-time="(\d{2}:\d{2})"[^>]*?>',
        flags=re.IGNORECASE,
    )

    for m in ed_pattern.finditer(html):
        ed_class = m.group(1).lower()
        if ed_class == "weekly":
            continue  # weekly roundups handled separately if at all

        date = m.group(2)
        data_time = m.group(3)
        edition_type = "morning" if int(data_time.split(":")[0]) < 14 else "evening"

        # Find the matching </div> closing this edition via depth counting
        start = m.end()
        depth = 1
        scan = start
        end = -1
        nest_re = re.compile(r"<div\b|</div>", flags=re.IGNORECASE)
        for nm in nest_re.finditer(html, scan):
            tok = nm.group(0).lower()
            if tok == "</div>":
                depth -= 1
                if depth == 0:
                    end = nm.end()
                    break
            else:
                depth += 1
        if end < 0:
            continue
        block = html[start:end]

        # Impact bullets (3 <li> inside .impact-list)
        impact_bullets: list[str] = []
        impact_m = re.search(
            r'<ul\s+class="impact-list">(.*?)</ul>',
            block, flags=re.IGNORECASE | re.DOTALL,
        )
        if impact_m:
            for li in re.finditer(
                r"<li[^>]*>(.*?)</li>",
                impact_m.group(1),
                flags=re.IGNORECASE | re.DOTALL,
            ):
                impact_bullets.append(strip_tags(li.group(1)))

        # Curated-items with their slugs, headlines, summaries
        items: list[CuratedItem] = []
        item_re = re.compile(
            r'<div\s+class="curated-item"\s+data-time="(\d{2}:\d{2})"'
            r'\s+data-slug="([^"]+)"[^>]*>(.*?)(?=<div\s+class="curated-item"|</div>\s*</div>)',
            flags=re.IGNORECASE | re.DOTALL,
        )
        for im in re.finditer(
            r'<div\s+class="curated-item"\s+data-time="(\d{2}:\d{2})"\s+data-slug="([^"]+)"[^>]*>',
            block,
            flags=re.IGNORECASE,
        ):
            i_time = im.group(1)
            slug = im.group(2)
            i_start = im.end()
            # Find this curated-item's end via depth counting
            i_depth = 1
            i_end = -1
            for jm in nest_re.finditer(block, i_start):
                tok = jm.group(0).lower()
                if tok == "</div>":
                    i_depth -= 1
                    if i_depth == 0:
                        i_end = jm.end()
                        break
                else:
                    i_depth += 1
            if i_end < 0:
                continue
            item_body = block[i_start:i_end]

            h4_m = re.search(
                r"<h4[^>]*>(.*?)</h4>",
                item_body, flags=re.IGNORECASE | re.DOTALL,
            )
            p_m = re.search(
                r"<p[^>]*>(.*?)</p>",
                item_body, flags=re.IGNORECASE | re.DOTALL,
            )
            headline = strip_tags(h4_m.group(1)) if h4_m else ""
            summary = strip_tags(p_m.group(1)) if p_m else ""
            if not headline or not slug:
                continue
            items.append(CuratedItem(
                slug=slug, headline=headline,
                summary=summary, data_time=i_time,
            ))

        iso_published = f"{date}T{data_time}:00+01:00"

        editions.append(Edition(
            date=date,
            edition_type=edition_type,
            data_time=data_time,
            impact_bullets=impact_bullets,
            items=items,
            iso_published=iso_published,
        ))

    return editions


# ── Generator ──────────────────────────────────────────────────────

def build_head_overrides(*,
    title: str,
    description: str,
    canonical: str,
    published_iso: str,
    schema_obj: dict,
) -> str:
    """Build the <head> override block to inject into a clone of index.html."""
    desc_safe = html_lib.escape(truncate(description, 280), quote=True)
    title_safe = html_lib.escape(title, quote=True)
    canonical_safe = html_lib.escape(canonical, quote=True)
    schema_json = json.dumps(schema_obj, ensure_ascii=False)
    return f"""<!-- deeplink-overrides -->
<title>{title_safe}</title>
<meta name="description" content="{desc_safe}"/>
<link rel="canonical" href="{canonical_safe}"/>
<meta property="og:type" content="article"/>
<meta property="og:title" content="{title_safe}"/>
<meta property="og:description" content="{desc_safe}"/>
<meta property="og:url" content="{canonical_safe}"/>
<meta property="og:site_name" content="The Daily Brief"/>
<meta property="article:published_time" content="{published_iso}"/>
<meta name="twitter:card" content="summary_large_image"/>
<meta name="twitter:title" content="{title_safe}"/>
<meta name="twitter:description" content="{desc_safe}"/>
<script type="application/ld+json">{schema_json}</script>"""


def apply_head_overrides(index_html: str, overrides: str) -> str:
    """Inject the override block at the end of <head>, after stripping
    the homepage's original <title>, meta description and canonical so
    they don't take precedence over the per-page values."""
    cleaned = index_html

    # Strip any prior overrides block from a previous build run
    cleaned = re.sub(
        r"<!-- deeplink-overrides -->.*?(?=\s*</head>)",
        "",
        cleaned,
        flags=re.DOTALL,
    )

    # Strip the homepage's original <title>
    cleaned = re.sub(
        r"<title>[^<]*</title>",
        "",
        cleaned,
        count=1,
        flags=re.IGNORECASE,
    )

    # Strip the homepage's original meta description
    cleaned = re.sub(
        r'<meta\s+name="description"[^>]*/?>',
        "",
        cleaned,
        count=1,
        flags=re.IGNORECASE,
    )

    # Strip the homepage's original canonical link
    cleaned = re.sub(
        r'<link\s+rel="canonical"[^>]*/?>',
        "",
        cleaned,
        count=1,
        flags=re.IGNORECASE,
    )

    # Strip homepage's og:title, og:description, og:url so per-page ones win
    cleaned = re.sub(
        r'<meta\s+property="og:(?:title|description|url)"[^>]*/?>',
        "",
        cleaned,
        flags=re.IGNORECASE,
    )

    return cleaned.replace("</head>", overrides + "\n</head>", 1)


def make_news_article_schema(*,
    headline: str,
    description: str,
    canonical: str,
    published_iso: str,
    article_body: str | None = None,
) -> dict:
    schema = {
        "@context": "https://schema.org",
        "@type": "NewsArticle",
        "headline": headline,
        "description": description,
        "datePublished": published_iso,
        "dateModified": published_iso,
        "author": {"@type": "Organization", "name": "The Daily Brief"},
        "publisher": {
            "@type": "Organization",
            "name": "The Daily Brief",
            "url": SITE_URL,
        },
        "mainEntityOfPage": {
            "@type": "WebPage",
            "@id": canonical,
        },
    }
    if article_body:
        schema["articleBody"] = article_body
    return schema


def write_static_page(out_path: Path, content: str) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(content, encoding="utf-8")


def build_edition_page(index_html: str, ed: Edition) -> tuple[Path, str]:
    """Generate the static HTML for an edition URL."""
    date_human = format_date_long(ed.date)
    edition_label = "Morning Briefing" if ed.edition_type == "morning" else "Evening Briefing"
    title = f"{edition_label} — {date_human} — The Daily Brief"
    description = " ".join(ed.impact_bullets)[:280] or (
        f"{edition_label} for {date_human}. Curated geopolitical and UK domestic stories from The Daily Brief."
    )
    canonical = SITE_URL + ed.url_path()

    body_text = " • ".join(it.headline for it in ed.items[:10])
    schema = make_news_article_schema(
        headline=f"{edition_label} — {date_human}",
        description=description,
        canonical=canonical,
        published_iso=ed.iso_published,
        article_body=body_text,
    )
    overrides = build_head_overrides(
        title=title, description=description,
        canonical=canonical, published_iso=ed.iso_published,
        schema_obj=schema,
    )
    page = apply_head_overrides(index_html, overrides)
    out_path = BRIEFINGS_DIR / f"{ed.date}-{ed.edition_type}" / "index.html"
    return out_path, page


def build_item_page(index_html: str, ed: Edition, it: CuratedItem) -> tuple[Path, str]:
    """Generate the static HTML for a per-headline URL."""
    title = f"{it.headline} — The Daily Brief"
    description = it.summary or it.headline
    canonical = SITE_URL + f"/briefings/{ed.date}-{ed.edition_type}/{it.slug}/"

    schema = make_news_article_schema(
        headline=it.headline,
        description=description,
        canonical=canonical,
        published_iso=ed.iso_published,
        article_body=it.summary,
    )
    overrides = build_head_overrides(
        title=title, description=description,
        canonical=canonical, published_iso=ed.iso_published,
        schema_obj=schema,
    )
    page = apply_head_overrides(index_html, overrides)
    out_path = BRIEFINGS_DIR / f"{ed.date}-{ed.edition_type}" / it.slug / "index.html"
    return out_path, page


def main() -> int:
    if not INDEX.exists():
        print(f"index.html not found at {INDEX}", file=sys.stderr)
        return 1
    html = INDEX.read_text(encoding="utf-8")

    editions = parse_editions(html)
    if not editions:
        print("No editions parsed.", file=sys.stderr)
        return 1

    pages_written = 0
    for ed in editions:
        path, content = build_edition_page(html, ed)
        write_static_page(path, content)
        pages_written += 1
        for it in ed.items:
            path, content = build_item_page(html, ed, it)
            write_static_page(path, content)
            pages_written += 1

    print(
        f"Wrote {pages_written} static pages across {len(editions)} editions "
        f"to {BRIEFINGS_DIR.relative_to(ROOT)}/"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
