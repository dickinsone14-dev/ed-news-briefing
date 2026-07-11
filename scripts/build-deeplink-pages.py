#!/usr/bin/env python3
"""Generate per-edition and per-headline static HTML files for SEO.

Reads index.html, finds every curated-edition and every curated-item
inside, and emits a LEAN, UNIQUE static file at each of:

    /briefings/YYYY-MM-DD-{morning|evening}/index.html          (edition page)
    /briefings/YYYY-MM-DD-{morning|evening}/{slug}/index.html    (article page)

IMPORTANT (SEO): earlier versions cloned the WHOLE index.html into every
deeplink, so all ~1,250 URLs served byte-identical bodies (150 stories
each) and Google deduped them — indexing almost none. These pages are now
STANDALONE: each article page contains only its own headline (<h1>),
dateline and full text (summary + dive-deeper analysis); each edition page
lists only its own edition's stories. The <head> (self-hosted fonts, CSS
variables, theme) is reused from index.html so the pages look native, with
per-page <title>, meta description, canonical and NewsArticle JSON-LD.

The homepage (index.html) is NOT touched and does not link to these URLs —
they are standalone entry points for search engines and shared links, so
this change cannot affect on-site navigation.

Run from repo root:
    python3 scripts/build-deeplink-pages.py
"""
from __future__ import annotations

import html as html_lib
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "index.html"
BRIEFINGS_DIR = ROOT / "briefings"
SITE_URL = "https://thedailybrief.co.uk"

MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


@dataclass
class CuratedItem:
    slug: str
    headline: str           # plain text
    summary: str            # plain text (the lead <p>)
    deeper: str             # plain text (the dive-deeper analysis)
    data_time: str          # 'HH:MM'


@dataclass
class Edition:
    date: str               # YYYY-MM-DD
    edition_type: str       # 'morning' or 'evening'
    data_time: str          # 'HH:MM'
    impact_bullets: list[str] = field(default_factory=list)
    items: list[CuratedItem] = field(default_factory=list)
    iso_published: str = ""

    def url_path(self) -> str:
        return f"/briefings/{self.date}-{self.edition_type}/"


# ── HTML helpers ───────────────────────────────────────────────────

def strip_tags(s: str) -> str:
    """Strip HTML tags and decode entities → clean plain text."""
    s = re.sub(r"<[^>]+>", "", s)
    s = html_lib.unescape(s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def esc(s: str) -> str:
    """Escape plain text for safe insertion into HTML."""
    return html_lib.escape(s, quote=True)


def truncate(s: str, n: int) -> str:
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"


def format_date_long(date_iso: str) -> str:
    import datetime as dt
    d = dt.date.fromisoformat(date_iso)
    return f"{DAYS[d.weekday()]} {d.day} {MONTHS[d.month - 1]} {d.year}"


# ── Parser ─────────────────────────────────────────────────────────

def parse_editions(html: str) -> list[Edition]:
    editions: list[Edition] = []
    ed_pattern = re.compile(
        r'<div\s+class="curated-edition\s+(morning|evening|weekly)"\s+'
        r'data-date="(\d{4}-\d{2}-\d{2})"\s+data-time="(\d{2}:\d{2})"[^>]*?>',
        flags=re.IGNORECASE,
    )
    nest_re = re.compile(r"<div\b|</div>", flags=re.IGNORECASE)

    for m in ed_pattern.finditer(html):
        if m.group(1).lower() == "weekly":
            continue
        date = m.group(2)
        data_time = m.group(3)
        edition_type = "morning" if int(data_time.split(":")[0]) < 14 else "evening"

        start = m.end()
        depth = 1
        end = -1
        for nm in nest_re.finditer(html, start):
            if nm.group(0).lower() == "</div>":
                depth -= 1
                if depth == 0:
                    end = nm.end()
                    break
            else:
                depth += 1
        if end < 0:
            continue
        block = html[start:end]

        impact_bullets: list[str] = []
        impact_m = re.search(
            r'<ul\s+class="impact-list">(.*?)</ul>',
            block, flags=re.IGNORECASE | re.DOTALL,
        )
        if impact_m:
            for li in re.finditer(r"<li[^>]*>(.*?)</li>", impact_m.group(1),
                                  flags=re.IGNORECASE | re.DOTALL):
                impact_bullets.append(strip_tags(li.group(1)))

        items: list[CuratedItem] = []
        for im in re.finditer(
            r'<div\s+class="curated-item"\s+data-time="(\d{2}:\d{2})"\s+data-slug="([^"]+)"[^>]*>',
            block, flags=re.IGNORECASE,
        ):
            i_time = im.group(1)
            slug = im.group(2)
            i_start = im.end()
            i_depth = 1
            i_end = -1
            for jm in nest_re.finditer(block, i_start):
                if jm.group(0).lower() == "</div>":
                    i_depth -= 1
                    if i_depth == 0:
                        i_end = jm.end()
                        break
                else:
                    i_depth += 1
            if i_end < 0:
                continue
            body = block[i_start:i_end]

            h4_m = re.search(r"<h4[^>]*>(.*?)</h4>", body, flags=re.IGNORECASE | re.DOTALL)
            p_m = re.search(r"<p[^>]*>(.*?)</p>", body, flags=re.IGNORECASE | re.DOTALL)
            deep_m = re.search(r'<div\s+class="deeper-content">(.*?)</div>', body,
                               flags=re.IGNORECASE | re.DOTALL)
            headline = strip_tags(h4_m.group(1)) if h4_m else ""
            summary = strip_tags(p_m.group(1)) if p_m else ""
            deeper = strip_tags(deep_m.group(1)) if deep_m else ""
            if not headline or not slug:
                continue
            items.append(CuratedItem(slug=slug, headline=headline,
                                     summary=summary, deeper=deeper, data_time=i_time))

        editions.append(Edition(
            date=date, edition_type=edition_type, data_time=data_time,
            impact_bullets=impact_bullets, items=items,
            iso_published=f"{date}T{data_time}:00+01:00",
        ))
    return editions


# ── Head reuse ─────────────────────────────────────────────────────

ARTICLE_STYLE = """
<style id="deeplink-style">
.dl-body{background:var(--bg,#f5f2eb);color:var(--text-primary,#1a1a2e);margin:0;
  font-family:'Inter',-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
  -webkit-font-smoothing:antialiased;}
.dl-mast{border-bottom:1px solid var(--border-light,#e4ddd0);padding:1.15rem 1.25rem;text-align:center;}
.dl-mast a{color:var(--text-primary,#1a1a2e);text-decoration:none;
  font-family:'Playfair Display',Georgia,serif;font-weight:700;font-size:1.35rem;letter-spacing:-.01em;}
.dl-mast .dl-tag{display:block;margin-top:.3rem;font-size:.72rem;letter-spacing:.08em;
  text-transform:uppercase;color:var(--text-secondary,#6b6455);}
.dl-wrap{max-width:720px;margin:0 auto;padding:2.4rem 1.25rem 4rem;}
.dl-kicker{font-size:.74rem;letter-spacing:.09em;text-transform:uppercase;
  color:#9a7b3f;margin-bottom:.55rem;font-weight:600;}
.dl-article h1{font-family:'Playfair Display',Georgia,serif;font-weight:700;
  font-size:2.05rem;line-height:1.16;margin:.15rem 0 1.2rem;color:var(--text-primary,#1a1a2e);}
.dl-article p{font-size:1.05rem;line-height:1.66;margin:0 0 1.1rem;color:var(--text-primary,#1a1a2e);}
.dl-analysis{border-top:1px solid var(--border-light,#e4ddd0);margin-top:1.7rem;padding-top:1.35rem;}
.dl-analysis .dl-label{font-size:.72rem;letter-spacing:.09em;text-transform:uppercase;
  color:#9a7b3f;margin-bottom:.55rem;font-weight:600;}
.dl-list{list-style:none;padding:0;margin:1.5rem 0 0;}
.dl-list li{border-top:1px solid var(--border-light,#e4ddd0);padding:1.15rem 0;}
.dl-list h2{font-family:'Playfair Display',Georgia,serif;font-size:1.35rem;line-height:1.2;margin:0 0 .5rem;}
.dl-list h2 a{color:var(--text-primary,#1a1a2e);text-decoration:none;}
.dl-list h2 a:hover{text-decoration:underline;}
.dl-list p{font-size:1rem;line-height:1.6;margin:0;color:var(--text-secondary,#4a4436);}
.dl-impact{background:var(--bg-card,#faf9f6);border:1px solid var(--border-light,#e4ddd0);
  border-radius:2px;padding:1.1rem 1.25rem;margin:1.5rem 0;}
.dl-impact .dl-label{font-size:.72rem;letter-spacing:.09em;text-transform:uppercase;color:#9a7b3f;font-weight:600;margin-bottom:.6rem;}
.dl-impact ul{margin:0;padding-left:1.1rem;}
.dl-impact li{font-size:.98rem;line-height:1.55;margin-bottom:.5rem;}
.dl-back{display:inline-block;margin-top:2.25rem;font-weight:600;
  color:var(--text-primary,#1a1a2e);text-decoration:none;border-bottom:2px solid #9a7b3f;padding-bottom:2px;}
.dl-foot{border-top:1px solid var(--border-light,#e4ddd0);text-align:center;
  padding:1.5rem;font-size:.78rem;color:var(--text-secondary,#6b6455);margin-top:2.5rem;}
.dl-foot a{color:var(--text-secondary,#6b6455);}
</style>
"""


def extract_head(index_html: str) -> str:
    """Return the inner <head> of index.html with the homepage's own
    title / description / canonical / og:* stripped so per-page ones win."""
    m = re.search(r"<head>(.*?)</head>", index_html, flags=re.DOTALL | re.IGNORECASE)
    head = m.group(1) if m else ""
    head = re.sub(r"<title>[^<]*</title>", "", head, count=1, flags=re.IGNORECASE)
    head = re.sub(r'<meta\s+name="description"[^>]*/?>', "", head, count=1, flags=re.IGNORECASE)
    head = re.sub(r'<link\s+rel="canonical"[^>]*/?>', "", head, count=1, flags=re.IGNORECASE)
    head = re.sub(r'<meta\s+property="og:(?:title|description|url|type)"[^>]*/?>', "", head, flags=re.IGNORECASE)
    return head


def head_overrides(*, title: str, description: str, canonical: str,
                   published_iso: str, schema_obj: dict) -> str:
    d = esc(truncate(description, 280))
    t = esc(title)
    c = esc(canonical)
    return (
        f"<title>{t}</title>\n"
        f'<meta name="description" content="{d}"/>\n'
        f'<link rel="canonical" href="{c}"/>\n'
        f'<meta property="og:type" content="article"/>\n'
        f'<meta property="og:title" content="{t}"/>\n'
        f'<meta property="og:description" content="{d}"/>\n'
        f'<meta property="og:url" content="{c}"/>\n'
        f'<meta property="article:published_time" content="{esc(published_iso)}"/>\n'
        f'<meta name="twitter:title" content="{t}"/>\n'
        f'<meta name="twitter:description" content="{d}"/>\n'
        f'<script type="application/ld+json">{json.dumps(schema_obj, ensure_ascii=False)}</script>'
    )


def make_news_article_schema(*, headline, description, canonical, published_iso, body=None) -> dict:
    schema = {
        "@context": "https://schema.org",
        "@type": "NewsArticle",
        "headline": headline[:110],
        "description": description,
        "image": [f"{SITE_URL}/og-image.png"],
        "datePublished": published_iso,
        "dateModified": published_iso,
        "author": {"@type": "Organization", "name": "The Daily Brief", "url": SITE_URL},
        "publisher": {
            "@type": "Organization", "name": "The Daily Brief", "url": SITE_URL,
            "logo": {"@type": "ImageObject", "url": f"{SITE_URL}/icon-512.png",
                     "width": 512, "height": 512},
        },
        "mainEntityOfPage": {"@type": "WebPage", "@id": canonical},
    }
    if body:
        schema["articleBody"] = body
    return schema


def page_shell(head_inner: str, overrides: str, body_inner: str) -> str:
    return (
        "<!DOCTYPE html>\n<html lang=\"en-GB\">\n<head>"
        + head_inner + overrides + ARTICLE_STYLE
        + "</head>\n<body class=\"dl-body\">\n" + body_inner + "\n</body>\n</html>\n"
    )


def masthead(edition_label: str, date_human: str, time_bst: str) -> str:
    return (
        '<header class="dl-mast">'
        '<a href="/">The Daily Brief</a>'
        f'<span class="dl-tag">{esc(edition_label)} &middot; {esc(date_human)} &middot; {esc(time_bst)} BST</span>'
        '</header>'
    )


def footer() -> str:
    return (
        '<footer class="dl-foot">'
        '&copy; The Daily Brief &middot; '
        '<a href="/">Home</a> &middot; '
        '<a href="/#curated">Today&rsquo;s briefing</a> &middot; '
        '<a href="/#live-feeds">Live updates</a>'
        '</footer>'
    )


# ── Page builders ──────────────────────────────────────────────────

def write_static_page(out_path: Path, content: str) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(content, encoding="utf-8")


def build_edition_page(head_inner: str, ed: Edition) -> tuple[Path, str]:
    date_human = format_date_long(ed.date)
    label = "Morning Briefing" if ed.edition_type == "morning" else "Evening Briefing"
    title = f"{label} — {date_human} — The Daily Brief"
    description = " ".join(ed.impact_bullets)[:280] or (
        f"{label} for {date_human}: curated geopolitical and UK domestic stories from The Daily Brief."
    )
    canonical = SITE_URL + ed.url_path()
    schema = make_news_article_schema(
        headline=f"{label} — {date_human}", description=description,
        canonical=canonical, published_iso=ed.iso_published,
        body=" • ".join(it.headline for it in ed.items),
    )
    overrides = head_overrides(title=title, description=description, canonical=canonical,
                               published_iso=ed.iso_published, schema_obj=schema)

    impact_html = ""
    if ed.impact_bullets:
        lis = "".join(f"<li>{esc(b)}</li>" for b in ed.impact_bullets)
        impact_html = (
            '<div class="dl-impact"><div class="dl-label">What It Means For You</div>'
            f'<ul>{lis}</ul></div>'
        )

    items_html = []
    for it in ed.items:
        art_url = f"/briefings/{ed.date}-{ed.edition_type}/{it.slug}/"
        items_html.append(
            f'<li><h2><a href="{esc(art_url)}">{esc(it.headline)}</a></h2>'
            f'<p>{esc(truncate(it.summary, 240))}</p></li>'
        )

    body = (
        masthead(label, date_human, ed.data_time)
        + '<main class="dl-wrap">'
        + f'<div class="dl-kicker">{esc(label)} &middot; {esc(date_human)}</div>'
        + f'<h1 style="font-family:\'Playfair Display\',Georgia,serif;font-size:1.9rem;line-height:1.15;margin:.15rem 0 1rem;">{esc(label)}: {esc(date_human)}</h1>'
        + impact_html
        + '<ul class="dl-list">' + "".join(items_html) + '</ul>'
        + '<a class="dl-back" href="/#curated">Read the full interactive briefing &rarr;</a>'
        + '</main>' + footer()
    )
    out = BRIEFINGS_DIR / f"{ed.date}-{ed.edition_type}" / "index.html"
    return out, page_shell(head_inner, overrides, body)


def build_item_page(head_inner: str, ed: Edition, it: CuratedItem) -> tuple[Path, str]:
    date_human = format_date_long(ed.date)
    label = "Morning Briefing" if ed.edition_type == "morning" else "Evening Briefing"
    title = f"{it.headline} — The Daily Brief"
    description = it.summary or it.headline
    canonical = SITE_URL + f"/briefings/{ed.date}-{ed.edition_type}/{it.slug}/"
    body_text = (it.summary + " " + it.deeper).strip()
    schema = make_news_article_schema(
        headline=it.headline, description=description, canonical=canonical,
        published_iso=ed.iso_published, body=body_text,
    )
    overrides = head_overrides(title=title, description=description, canonical=canonical,
                               published_iso=ed.iso_published, schema_obj=schema)

    analysis_html = ""
    if it.deeper:
        analysis_html = (
            '<div class="dl-analysis"><div class="dl-label">Dive deeper</div>'
            f'<p>{esc(it.deeper)}</p></div>'
        )

    body = (
        masthead(label, date_human, it.data_time)
        + '<main class="dl-wrap"><article class="dl-article">'
        + f'<div class="dl-kicker">{esc(label)} &middot; {esc(date_human)}</div>'
        + f'<h1>{esc(it.headline)}</h1>'
        + f'<p>{esc(it.summary)}</p>'
        + analysis_html
        + f'<a class="dl-back" href="{esc(ed.url_path())}">More from this briefing &rarr;</a>'
        + '</article></main>' + footer()
    )
    out = BRIEFINGS_DIR / f"{ed.date}-{ed.edition_type}" / it.slug / "index.html"
    return out, page_shell(head_inner, overrides, body)


def main() -> int:
    if not INDEX.exists():
        print(f"index.html not found at {INDEX}", file=sys.stderr)
        return 1
    html = INDEX.read_text(encoding="utf-8")
    head_inner = extract_head(html)
    editions = parse_editions(html)
    if not editions:
        print("No editions parsed.", file=sys.stderr)
        return 1

    pages = 0
    for ed in editions:
        p, c = build_edition_page(head_inner, ed)
        write_static_page(p, c)
        pages += 1
        for it in ed.items:
            p, c = build_item_page(head_inner, ed, it)
            write_static_page(p, c)
            pages += 1

    print(f"Wrote {pages} lean static pages across {len(editions)} editions "
          f"to {BRIEFINGS_DIR.relative_to(ROOT)}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
