#!/usr/bin/env python3
"""Fetch the site's RSS feeds server-side and write feeds.json (same-origin).

The "Live Updates" section fetches RSS client-side through public CORS proxies
(rss2json / allorigins / corsproxy), which are unreliable and were failing —
leaving the section empty. This script pre-fetches the feeds server-side (no
CORS problem off a server) and writes feeds.json, which the site reads
same-origin as its FIRST, reliable strategy; if feeds.json is missing or a
given feed is absent, the page falls back to the existing proxy chain.

The feed list is parsed from index.html so there is a single source of truth.
Keyed by feed URL (feed names repeat across sections). Run on a schedule by
.github/workflows/update-feeds.yml.

    python3 scripts/build-feeds.py
"""
from __future__ import annotations
import datetime, html, json, re, sys, urllib.request
from pathlib import Path

try:
    import feedparser
except ImportError:
    print("feedparser required: pip install feedparser", file=sys.stderr)
    sys.exit(1)

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "index.html"
OUT = ROOT / "feeds.json"
UA = "Mozilla/5.0 (compatible; TheDailyBriefBot/1.0; +https://thedailybrief.co.uk)"
PER_FEED = 6
TIMEOUT = 15


def parse_feed_list(html_text: str) -> dict[str, int]:
    """Extract {url: top} from the JS feed-source objects in index.html.
    Feed objects look like: { name: 'BBC News', url: 'https://…', top: 3 }."""
    feeds: dict[str, int] = {}
    for m in re.finditer(r"\{[^{}]*?url:\s*'(https?://[^']+)'[^{}]*\}", html_text):
        obj, url = m.group(0), m.group(1)
        if "name:" not in obj or "thedailybrief.co.uk" in url:
            continue  # only genuine feed-source objects, never the own domain
        tm = re.search(r"top:\s*(\d+)", obj)
        top = int(tm.group(1)) if tm else 4
        feeds[url] = max(feeds.get(url, 0), top)
    return feeds


def strip_html(s: str, n: int = 180) -> str:
    s = re.sub(r"<[^>]+>", "", s or "")
    s = html.unescape(s)
    s = re.sub(r"\s+", " ", s).strip()
    return (s[:n].rstrip() + "...") if len(s) > n else s


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*",
    })
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return r.read()


def main() -> int:
    html_text = INDEX.read_text(encoding="utf-8")
    feed_urls = parse_feed_list(html_text)
    if not feed_urls:
        print("no feeds parsed from index.html", file=sys.stderr)
        return 1

    out: dict[str, list] = {}
    ok = fail = 0
    for url, top in feed_urls.items():
        cap = max(PER_FEED, top)
        try:
            fp = feedparser.parse(fetch(url))
            items = []
            for e in fp.entries[:cap]:
                title = (e.get("title") or "").strip()
                link = e.get("link") or ""
                if not (title and link):
                    continue
                items.append({
                    "title": title,
                    "description": strip_html(e.get("summary") or e.get("description") or ""),
                    "link": link,
                    "pubDate": e.get("published") or e.get("updated") or "",
                })
            if items:
                out[url] = items[:cap]
                ok += 1
            else:
                fail += 1
                print(f"  no items: {url}", file=sys.stderr)
        except Exception as ex:  # noqa: BLE001 — skip any bad feed, keep going
            fail += 1
            print(f"  skip {url}: {ex}", file=sys.stderr)

    data = {
        "generated": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "feeds": out,
    }
    OUT.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    total = sum(len(v) for v in out.values())
    print(f"feeds.json: {ok} feeds OK, {fail} failed, {total} items, {OUT.stat().st_size // 1024} KB")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
