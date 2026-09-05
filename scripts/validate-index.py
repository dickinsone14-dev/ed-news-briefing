#!/usr/bin/env python3
"""
validate-index.py — structural and editorial validation for index.html.

Run before pushing. Catches the kind of mistakes that hide editions or
break archive rendering on the live site, AND enforces the editorial
rules Ed has locked in over time.

Structural checks (all editions):
  1. #all-editions div balance (no stray </div> closing the container early)
  2. embedded-markets JSON validity
  3. Every data-markets='...' attribute is valid JSON with all expected keys
  4. curated-edition open count == END comment count
  5. data-date matches expected 7-day window (warning only)
  6. No banned-source domains anywhere in the file (hard fail)
  7. Breaking-news banner / JSON consistency
  8. Source allow-list (every hyperlink in #all-editions on SOURCES.md)
  9. No vetoed feature markers
 10. Every curated-item has data-slug
 11. Slug uniqueness within each edition

Editorial checks (12-17 — locked-in rules from memory):
 12. No <h4> outlet prefix (no "Reuters:", "BBC:", "Guardian:", etc.)
 13. No <em> tags inside any <h4> (plain-text headlines only)
 14. No <div class="war-day-count"> blocks anywhere (removed 2026-05-23)
 15. JS integrity (function reveal(), function attempt(), function computeOffset()
     intact; no capitalised JS keywords from accidental regex damage)
 16. Newest edition: 5 GEO + 5 UK curated-items per column (5+5 rule)
 17. Newest edition: ≥10 distinct outlets in SOURCES USED block
 18. Newest edition: GEO column max 3/5 stories on any single theme

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
            # Site runs on UK time. The machine's local timezone has drifted before
            # (e.g. set to US Central), so never trust the system-local date here.
            from datetime import datetime
            from zoneinfo import ZoneInfo
            today = datetime.now(ZoneInfo("Europe/London")).date()
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

    # ───────────────────────────────────────────────────────────────────
    # EDITORIAL CHECKS — locked-in rules from memory.
    # These check the latest edition by data-date + data-time (the one
    # being added on this push). Older editions are not re-validated
    # because rules were added incrementally over time.
    # ───────────────────────────────────────────────────────────────────

    # 12. No <h4> outlet prefix in any edition
    OUTLET_PREFIXES = (
        "Reuters", "BBC", "Guardian", "ISW", "Al Jazeera", "Independent",
        "Times", "AP", "CNBC", "Bloomberg", "NYT", "CNN", "CBS", "FT",
        "Telegraph", "Sky News", "Channel 4", "ITV", "Mirror", "Sun",
        "Daily Mail", "Express", "Financial Times", "New York Times",
        "Washington Post", "WSJ", "Observer", "i Paper", "Times Editorial",
    )
    h4_prefix_pat = re.compile(
        r"<h4>\s*(" + "|".join(re.escape(o) for o in OUTLET_PREFIXES) + r")\s*:",
        re.I,
    )
    prefix_hits = h4_prefix_pat.findall(html)
    if prefix_hits:
        fail(
            f"{len(prefix_hits)} <h4> headline(s) start with an outlet prefix "
            f"(e.g. 'Reuters:', 'BBC:'). Headlines must not name outlets. "
            f"Examples: {sorted(set(prefix_hits))[:5]}"
        )
        errors += 1
    else:
        ok("No outlet-prefixed <h4> headlines")

    # 13. No <em> tags inside any <h4>
    em_in_h4 = re.findall(r"<h4>[^<]*<em\b", html)
    if em_in_h4:
        fail(
            f"{len(em_in_h4)} <h4> headline(s) contain <em> tags. "
            f"Headlines must be plain text only."
        )
        errors += 1
    else:
        ok("No <em> tags in <h4> headlines")

    # 14. No <div class="war-day-count"> blocks
    war_day_count_hits = len(re.findall(r'<div class="war-day-count"', html))
    if war_day_count_hits:
        fail(
            f"{war_day_count_hits} <div class=\"war-day-count\"> block(s) found. "
            f"The Iran-war summary block was removed permanently on 2026-05-23 "
            f"and must not be reintroduced."
        )
        errors += 1
    else:
        ok("No war-day-count blocks (removed 2026-05-23)")

    # 15. JS integrity — critical inline-script function signatures and identifiers
    JS_REQUIRED = ["function reveal()", "function attempt()", "function computeOffset()"]
    missing_js = [j for j in JS_REQUIRED if j not in html]
    if missing_js:
        fail(
            f"Inline JS missing required function definitions: {missing_js}. "
            f"Regex over the whole file probably damaged a <script> block — "
            f"restore from a known-good commit and re-apply edits with "
            f"<script>/<style> segments protected."
        )
        errors += 1
    # Look for accidentally capitalised JS keywords inside <script> blocks
    js_blocks = re.findall(r"<script[^>]*>(.*?)</script>", html, re.S)
    bad_caps = []
    for block in js_blocks:
        # Skip JSON-only script blocks (type="application/json")
        if 'type="application/json"' in block[:200]:
            continue
        for bad in (r"\bVar\s+\w", r"\bReturn\s+\w", r"\bFor\s+\(", r"\bIf\s+\("):
            for m in re.finditer(bad, block):
                bad_caps.append(m.group(0))
    if bad_caps:
        fail(
            f"Capitalised JS keywords found in inline scripts (likely regex "
            f"damage): {list(set(bad_caps))[:5]}. Restore JS from a known-good commit."
        )
        errors += 1
    if not missing_js and not bad_caps:
        ok("JS integrity intact (function signatures + lowercase keywords)")

    # Identify the newest edition (top of #all-editions by date+time)
    edition_blocks = []
    for m in re.finditer(
        r'<div\s+class="curated-edition\s+(?:morning|evening)"\s+'
        r'data-date="(\d{4}-\d{2}-\d{2})"\s+data-time="(\d{2}:\d{2})"',
        html,
    ):
        # Find end of this edition by div-depth count
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
        edition_blocks.append({
            "date": m.group(1),
            "time": m.group(2),
            "block": block,
        })
    edition_blocks.sort(key=lambda e: (e["date"], e["time"]), reverse=True)

    if not edition_blocks:
        warn("No editions found — skipping editorial checks 16-18")
    else:
        newest = edition_blocks[0]
        label = f"{newest['date']} {newest['time']}"

        # 16. 5+5 columns in newest edition
        columns = re.findall(
            r'<div\s+class="curated-column">(.*?)(?=<div\s+class="curated-column">|<div\s+class="one-to-read"|</div>\s*</div>)',
            newest["block"],
            re.S,
        )
        col_counts = []
        for col in columns:
            items = len(re.findall(r'<div\s+class="curated-item"', col))
            col_counts.append(items)
        if len(col_counts) != 2:
            fail(
                f"Newest edition ({label}): expected 2 curated-columns, "
                f"found {len(col_counts)}."
            )
            errors += 1
        elif col_counts != [5, 5]:
            fail(
                f"Newest edition ({label}): column item counts are {col_counts}, "
                f"expected [5, 5]. Both GEO and UK columns must have exactly "
                f"5 stories each."
            )
            errors += 1
        else:
            ok(f"Newest edition ({label}): 5 GEO + 5 UK curated-items")

        # 17. ≥10 distinct outlets in SOURCES USED block of newest edition
        src_match = re.search(
            r"SOURCES USED(.*?)END SOURCES USED",
            newest["block"],
            re.S,
        )
        if not src_match:
            warn(
                f"Newest edition ({label}): no SOURCES USED block found — "
                f"cannot check outlet count rule."
            )
        else:
            src_text = src_match.group(1)
            OUTLET_PATTERNS = [
                ("Reuters", r"\bReuters\b"),
                ("AP", r"\bAP\b"),
                ("AFP", r"\bAFP\b"),
                ("Bloomberg", r"\bBloomberg\b"),
                ("BBC", r"\bBBC\b"),
                ("CNN", r"\bCNN\b"),
                ("CBS", r"\bCBS\b"),
                ("CNBC", r"\bCNBC\b"),
                ("NBC", r"\bNBC\b"),
                ("ABC", r"\bABC\b"),
                ("NPR", r"\bNPR\b"),
                ("FT/Financial Times", r"\b(FT|Financial Times)\b"),
                ("Guardian", r"\bGuardian\b"),
                ("Independent", r"\bIndependent\b"),
                ("The Times", r"\bThe Times\b|\bTimes\b(?! of)"),
                ("Telegraph", r"\bTelegraph\b"),
                ("Sky News", r"\bSky News\b"),
                ("Channel 4", r"\bChannel 4\b"),
                ("ITV", r"\bITV\b"),
                ("ISW", r"\bISW\b|Institute for the Study of War"),
                ("NYT/New York Times", r"\bNYT\b|\bNew York Times\b"),
                ("WSJ/Wall Street Journal", r"\bWSJ\b|\bWall Street Journal\b"),
                ("Washington Post", r"\bWashington Post\b|\bWaPo\b"),
                ("Al Jazeera", r"\bAl Jazeera\b"),
                ("Times of Israel", r"Times of Israel"),
                ("Iran International", r"Iran International|iranintl"),
                ("France 24", r"\bFrance 24\b"),
                ("LBC", r"\bLBC\b"),
                ("City AM", r"\bCity AM\b"),
                ("The Argus", r"\bArgus\b"),
                ("Economist", r"\bEconomist\b"),
                ("Spectator", r"\bSpectator\b"),
                ("Alliance News", r"\bAlliance News\b"),
                ("Sharecast", r"\bSharecast\b"),
                ("RUSI", r"\bRUSI\b"),
                ("Defense News", r"\bDefense News\b"),
                ("Bellingcat", r"\bBellingcat\b"),
                ("Janes", r"\bJanes\b|\bJane's\b"),
                ("PBS", r"\bPBS\b"),
                ("Politico", r"\bPolitico\b"),
                ("Axios", r"\bAxios\b"),
                ("AAP", r"\bAAP\b"),
            ]
            outlets_found = set()
            for name, pat in OUTLET_PATTERNS:
                if re.search(pat, src_text):
                    outlets_found.add(name)
            if len(outlets_found) < 10:
                fail(
                    f"Newest edition ({label}): only {len(outlets_found)} distinct "
                    f"outlets in SOURCES USED ({sorted(outlets_found)}). "
                    f"Hard requirement is ≥10. Expand sourcing before pushing."
                )
                errors += 1
            else:
                ok(
                    f"Newest edition ({label}): {len(outlets_found)} distinct "
                    f"outlets in SOURCES USED (≥10 ✓)"
                )

        # 18. GEO theme concentration max 3/5 in newest edition
        # Extract GEO column slugs (first curated-column)
        if len(columns) >= 1:
            geo_col = columns[0]
            geo_slugs = re.findall(r'data-slug="([^"]+)"', geo_col)
            THEME_KEYWORDS = {
                "Iran/Hormuz": [
                    "iran", "iranian", "hormuz", "baghaei", "qalibaf",
                    "araghchi", "pezeshkian", "khamenei", "irgc", "tehran",
                    "mojtaba", "rezaei", "aliabadi", "bandar-abbas",
                    "centcom-strikes-irgc", "doha", "qatar-prime-minister",
                ],
                "Ukraine/Russia": [
                    "ukraine", "ukrainian", "russia", "russian", "kyiv",
                    "moscow", "putin", "zelensky", "kremlin", "donbas",
                    "sumy", "kharkiv",
                ],
                "China/Taiwan": [
                    "china", "chinese", "beijing", "xi-jinping", "taiwan",
                    "taipei", "pla-",
                ],
                "Gaza/Israel": [
                    "gaza", "hamas", "israeli", "idf-", "netanyahu",
                    "palestinian", "west-bank",
                ],
                "Hezbollah/Lebanon": [
                    "hezbollah", "lebanon", "lebanese", "beirut",
                ],
            }
            theme_counts = {theme: 0 for theme in THEME_KEYWORDS}
            for slug in geo_slugs:
                slug_l = slug.lower()
                for theme, keywords in THEME_KEYWORDS.items():
                    if any(kw in slug_l for kw in keywords):
                        theme_counts[theme] += 1
                        break  # one slug counts toward one theme only
            over_threshold = [
                (t, c) for t, c in theme_counts.items() if c > 3
            ]
            if over_threshold:
                for t, c in over_threshold:
                    fail(
                        f"Newest edition ({label}): GEO column has {c} of "
                        f"{len(geo_slugs)} stories on the '{t}' theme. "
                        f"Hard ceiling is 3 of 5. Swap a story for non-{t} content "
                        f"(Ukraine/Russia, China/Taiwan, US politics, EU, Africa, "
                        f"Latin America, etc.)."
                    )
                errors += 1
            else:
                top = max(theme_counts.items(), key=lambda x: x[1])
                ok(
                    f"Newest edition ({label}): GEO theme concentration OK "
                    f"(max single-theme count: {top[1]}/5 on '{top[0]}')"
                )

    if errors:
        print(f"\n\033[31mFAILED with {errors} error(s).\033[0m", file=sys.stderr)
        return 1
    print(f"\n\033[32mAll structural and editorial checks passed.\033[0m")
    return 0


if __name__ == "__main__":
    sys.exit(main())
