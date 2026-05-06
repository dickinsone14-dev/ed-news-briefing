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
]


def fail(msg: str) -> None:
    print(f"\033[31m✗ FAIL:\033[0m {msg}", file=sys.stderr)


def warn(msg: str) -> None:
    print(f"\033[33m⚠ WARN:\033[0m {msg}", file=sys.stderr)


def ok(msg: str) -> None:
    print(f"\033[32m✓\033[0m {msg}")


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

    # 8. Vetoed feature markers
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

    if errors:
        print(f"\n\033[31mFAILED with {errors} error(s).\033[0m", file=sys.stderr)
        return 1
    print(f"\n\033[32mAll structural checks passed.\033[0m")
    return 0


if __name__ == "__main__":
    sys.exit(main())
