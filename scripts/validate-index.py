#!/usr/bin/env python3
"""
validate-index.py — structural validation for index.html.

Run before pushing. Catches the kind of mistakes that hide editions or
break archive rendering on the live site.

Checks:
  1. #all-editions div balance (no stray </div> closing the container early)
  2. embedded-markets JSON validity
  3. Every data-markets='...' attribute is valid JSON with all expected keys
  4. curated-edition open count == END comment count (each edition has a close marker)
  5. data-date matches expected 7-day window (warning only)
  6. No banned-source domains anywhere in the file (hard fail)
  7. No vetoed feature markers (refFiguresBar, search overlay, per-edition market strips)

Exits 0 on pass, 1 on fail.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import date, timedelta
from pathlib import Path

INDEX = Path(__file__).resolve().parent.parent / "index.html"
SOURCES_MD = Path(__file__).resolve().parent.parent / "SOURCES.md"

EXPECTED_MARKET_KEYS = {
    "FTSE", "SP", "Brent", "GBP", "Gold", "EURGBP",
    "Gilt", "VIX", "BTC", "UST", "ts",
}

BANNED_DOMAINS = [
    "wikipedia.org",
    "en.wikipedia.org",
    "gbnews.com",
    "foxnews.com",
    "middleeasteye.net",
    "oilprice.com",
    "pravda.com",
    "newspravda",
]

VETOED_MARKERS = [
    ("refFiguresBar", "UK statistics bar"),
    ("ref-figures-bar", "UK statistics bar"),
    ("search-overlay", "search feature"),
    ("search-toggle", "search feature"),
    ("data-search-trigger", "search feature"),
    ('class="change-diff"', '"What Changed Today" diff (vetoed 2026-05-16)'),
    ('class="diff-arrow"', '"What Changed Today" diff (vetoed 2026-05-16)'),
]


def fail(msg: str) -> None:
    print(f"\033[31m✗ FAIL:\033[0m {msg}", file=sys.stderr)


def warn(msg: str) -> None:
    print(f"\033[33m⚠ WARN:\033[0m {msg}", file=sys.stderr)


def ok(msg: str) -> None:
    print(f"\033[32m✓\033[0m {msg}")


def load_approved_domains() -> set[str]:
    """Parse the BEGIN/END APPROVED DOMAINS block from SOURCES.md."""
    if not SOURCES_MD.exists():
        return set()
    text = SOURCES_MD.read_text(encoding="utf-8")
    m = re.search(
        r"<!--\s*BEGIN APPROVED DOMAINS\s*-->(.+?)<!--\s*END APPROVED DOMAINS\s*-->",
        text,
        re.S,
    )
    if not m:
        return set()
    domains: set[str] = set()
    for line in m.group(1).splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        domains.add(line.lower())
    return domains


def hostname_from_url(url: str) -> str:
    """Lower-cased hostname stripped of port and www. prefix."""
    m = re.match(r"https?://([^/\s\")\]:]+)", url, re.I)
    if not m:
        return ""
    host = m.group(1).lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def host_is_approved(host: str, approved: set[str]) -> bool:
    """A host is approved if it equals or is a subdomain of any approved domain."""
    if not host:
        return False
    if host in approved:
        return True
    for d in approved:
        if host.endswith("." + d):
            return True
    return False


def main() -> int:
    if not INDEX.exists():
        fail(f"{INDEX} not found")
        return 1

    html = INDEX.read_text(encoding="utf-8")
    errors = 0

    # 1. all-editions div balance
    m = re.search(
        r'<div id="all-editions"[^>]*>(.*?)</div><!-- /all-editions -->',
        html,
        re.S,
    )
    if not m:
        fail("Could not find #all-editions container with /all-editions close marker")
        errors += 1
    else:
        inner = m.group(1)
        opens = len(re.findall(r"<div\b", inner))
        closes = len(re.findall(r"</div>", inner))
        delta = opens - closes
        if delta != 0:
            fail(
                f"#all-editions div imbalance: {opens} opens, {closes} closes "
                f"(delta {delta:+d}). A stray </div> will collapse the archive "
                f"container early and hide past editions."
            )
            errors += 1
        else:
            ok(f"#all-editions div balance: {opens}/{closes}")

    # 2. embedded-markets JSON
    em = re.search(
        r'<script id="embedded-markets" type="application/json">(.+?)</script>',
        html,
        re.S,
    )
    if not em:
        fail("embedded-markets script tag not found")
        errors += 1
    else:
        try:
            data = json.loads(em.group(1))
            missing = EXPECTED_MARKET_KEYS - set(data.keys())
            if missing:
                fail(f"embedded-markets missing keys: {sorted(missing)}")
                errors += 1
            else:
                ok(f"embedded-markets JSON valid (ts={data.get('ts')})")
        except json.JSONDecodeError as e:
            fail(f"embedded-markets JSON invalid: {e}")
            errors += 1

    # 3. Every data-markets='...' attribute valid
    bad_attr = 0
    for i, dm in enumerate(re.finditer(r"data-markets='([^']+)'", html)):
        try:
            d = json.loads(dm.group(1))
            missing = EXPECTED_MARKET_KEYS - set(d.keys())
            if missing:
                fail(f"data-markets #{i + 1} missing keys: {sorted(missing)}")
                bad_attr += 1
        except json.JSONDecodeError as e:
            fail(f"data-markets #{i + 1} invalid JSON: {e}")
            bad_attr += 1
    if bad_attr:
        errors += bad_attr
    else:
        ok(f"All data-markets attributes valid")

    # 4. curated-edition open count vs END comments
    edition_opens = len(re.findall(r'class="curated-edition[^"]*"', html))
    end_comments = len(re.findall(r"END (MORNING|EVENING|WEEKLY|PMQS)", html))
    weekly_opens = len(re.findall(r'class="curated-edition weekly"', html))
    # Weekly editions historically don't all have END comments; allow them to be off
    expected_end = edition_opens - weekly_opens
    if end_comments < expected_end:
        warn(
            f"curated-edition opens={edition_opens} (incl. {weekly_opens} weekly), "
            f"END comments={end_comments}. At least {expected_end - end_comments} "
            f"non-weekly edition(s) missing an END comment."
        )
    else:
        ok(f"curated-edition / END comment counts: {edition_opens} editions, {end_comments} END")

    # 5. data-date 7-day window check
    dates = sorted(set(re.findall(r'data-date="([0-9-]+)"', html)))
    if dates:
        try:
            today = date.today()
            cutoff = today - timedelta(days=7)
            stale = [d for d in dates if date.fromisoformat(d) < cutoff]
            if stale:
                warn(
                    f"Editions older than 7 days present: {stale}. "
                    f"Rolling-week rule says delete only those older than 7 days from today ({today})."
                )
            future = [d for d in dates if date.fromisoformat(d) > today]
            if future:
                fail(f"Editions dated in the future: {future} (no premature editions allowed)")
                errors += 1
        except ValueError as e:
            warn(f"data-date parsing issue: {e}")

    # 6. Banned domains
    banned_hits = []
    for domain in BANNED_DOMAINS:
        for m in re.finditer(rf"https?://[^\"'\s>]*{re.escape(domain)}", html, re.I):
            banned_hits.append((domain, m.group(0)[:120]))
    if banned_hits:
        for domain, url in banned_hits:
            fail(f"Banned source link found ({domain}): {url}")
        errors += len(banned_hits)
    else:
        ok("No banned source domains found")

    # 7. Breaking-news banner / JSON consistency
    # Prevents the recurring failure mode where the inline <span class="breaking-text">
    # is updated but the breaking-stories JSON is left as [] — causing the "Read more"
    # modal to show only the headline with no summary or facts.
    bs_match = re.search(
        r'<script id="breaking-stories" type="application/json">(.*?)</script>',
        html,
        re.S,
    )
    text_match = re.search(
        r'<span class="breaking-text" id="breakingText">([^<]*)</span>',
        html,
    )
    banner_text = (text_match.group(1).strip() if text_match else "")
    if bs_match:
        try:
            stories = json.loads(bs_match.group(1).strip() or "[]")
            if not isinstance(stories, list):
                fail("breaking-stories JSON must be an array")
                errors += 1
                stories = []
        except json.JSONDecodeError as e:
            fail(f"breaking-stories JSON invalid: {e}")
            errors += 1
            stories = []
    else:
        stories = []

    if banner_text and not stories:
        fail(
            "Breaking banner has inline text but breaking-stories JSON is empty. "
            "The 'Read more' modal will show only the headline. Add a JSON entry "
            "with headline + summary + facts, or clear the inline text."
        )
        errors += 1
    for i, s in enumerate(stories):
        missing_fields = []
        if not s.get("headline", "").strip():
            missing_fields.append("headline")
        if not s.get("summary", "").strip():
            missing_fields.append("summary")
        if not isinstance(s.get("facts"), list) or not s.get("facts"):
            missing_fields.append("facts (non-empty array)")
        if not s.get("posted", "").strip():
            missing_fields.append("posted")
        if missing_fields:
            fail(
                f"breaking-stories[{i}] missing required fields: {missing_fields}. "
                f"Headline: {s.get('headline', '?')[:80]!r}"
            )
            errors += 1
    if banner_text and stories and not any(
        re.search(re.escape(s.get("headline", "")[:30]), banner_text, re.I)
        or re.search(re.escape(banner_text[:30]), s.get("headline", ""), re.I)
        for s in stories
    ):
        warn(
            "Banner inline text does not appear to match any headline in "
            "breaking-stories JSON. The modal may show a different story than "
            "the one in the banner."
        )
    if not banner_text and not stories:
        ok("Breaking banner: no active stories (clean state)")
    elif banner_text and stories:
        ok(f"Breaking banner: {len(stories)} story/stories with summary + facts")

    # 8. Source allow-list — every hyperlink inside #all-editions must point to
    # a domain in SOURCES.md's APPROVED DOMAINS block. Catches the case where a
    # briefing prompt drifts and an unapproved outlet leaks in via a one-to-read
    # URL or in-story citation hyperlink.
    approved = load_approved_domains()
    if not approved:
        warn("Could not load APPROVED DOMAINS from SOURCES.md — skipping allow-list check")
    else:
        all_eds = re.search(
            r'<div id="all-editions"[^>]*>(.*?)</div><!-- /all-editions -->',
            html,
            re.S,
        )
        if all_eds:
            inner = all_eds.group(1)
            href_re = re.compile(r'<a\s+[^>]*href="(https?://[^"]+)"', re.I)
            unapproved: list[tuple[str, str]] = []
            for m in href_re.finditer(inner):
                url = m.group(1)
                host = hostname_from_url(url)
                if not host_is_approved(host, approved):
                    unapproved.append((host, url[:120]))
            if unapproved:
                for host, url in unapproved:
                    fail(
                        f"Unapproved domain in curated content: {host} "
                        f"(not in SOURCES.md). URL: {url}"
                    )
                errors += len(unapproved)
            else:
                ok(f"All curated-content hyperlinks on SOURCES.md ({len(approved)} approved domains)")

    # 9. Vetoed feature markers
    veto_hits = []
    for marker, label in VETOED_MARKERS:
        if marker in html:
            veto_hits.append((marker, label))
    if veto_hits:
        for marker, label in veto_hits:
            fail(f"Vetoed feature marker present: '{marker}' ({label})")
        errors += len(veto_hits)
    else:
        ok("No vetoed feature markers found")

    # 10. Every curated-item must have data-slug (used for per-URL pages)
    item_opens = re.findall(
        r'<div\s+class="curated-item"[^>]*>',
        html,
    )
    items_without_slug = [t for t in item_opens if "data-slug=" not in t]
    if items_without_slug:
        fail(
            f"{len(items_without_slug)} curated-item(s) missing data-slug. "
            f"Run `python3 scripts/add-slugs.py` to backfill, or add the "
            f"attribute manually. data-slug drives per-headline deep-link URLs."
        )
        # Show one example for debugging
        example = items_without_slug[0]
        print(f"      Example: {example[:120]}", file=sys.stderr)
        errors += 1
    else:
        ok(f"All {len(item_opens)} curated-items have data-slug")

    # 11. Slug uniqueness within each edition
    # Parse each edition and check no two items share a slug
    ed_blocks = re.finditer(
        r'<div\s+class="curated-edition\s+(?:morning|evening)"\s+'
        r'data-date="(\d{4}-\d{2}-\d{2})"\s+data-time="(\d{2}:\d{2})"',
        html,
    )
    slug_conflicts = []
    for em in ed_blocks:
        # Get block by simple depth count
        start = em.end()
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
        slugs_in_ed = re.findall(r'data-slug="([^"]+)"', block)
        seen = {}
        for s in slugs_in_ed:
            if s in seen:
                slug_conflicts.append((em.group(1), em.group(2), s))
            seen[s] = True
    if slug_conflicts:
        for d, t, s in slug_conflicts:
            fail(
                f"Duplicate data-slug '{s}' within edition {d} {t}. "
                f"Slugs must be unique within an edition."
            )
        errors += len(slug_conflicts)
    else:
        ok("All data-slugs are unique within their edition")

    if errors:
        print(f"\n\033[31mFAILED with {errors} error(s).\033[0m", file=sys.stderr)
        return 1
    print(f"\n\033[32mAll structural checks passed.\033[0m")
    return 0


if __name__ == "__main__":
    sys.exit(main())
