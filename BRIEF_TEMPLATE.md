# Daily Brief — Structural Reference & Briefing Template

**Purpose:** the canonical structural rules for every morning and evening edition of The Daily Brief. Reconstructed on 2026-05-04 from the templated subagent prompts found in past session logs. The structure used to live only inside those prompts; this file is now the single source of truth in the repo.

> Pair this with `SOURCES.md` (the approved-source list) for the complete briefing playbook.

---

## 1. Site architecture

- Static HTML/CSS/JS, no build step. Hosted on GitHub Pages.
- All curated editions live inside `<div id="all-editions" style="display:none;">` in `index.html`.
- JavaScript reads each edition's `data-date` and `data-time` attributes and renders them into `#day-editions`, automatically grouping by date and showing today first.
- A separate `<script id="embedded-markets" type="application/json">` tag holds the **current** market snapshot for the global ticker. This must be updated with every push.
- Service worker (`sw.js`) caches static assets; bump `CACHE_NAME` (`daily-brief-vNN`) every push.
- Push to **both** remotes: `git push origin main && git push org main`.

## 2. Edition div: required attributes

```html
<div class="curated-edition [morning|evening|weekly]"
     data-date="YYYY-MM-DD"
     data-time="HH:MM"
     data-markets='{...JSON...}'>
```

`data-markets` is a JSON object with **all 10** market keys plus a timestamp:

| Key | Source | Example |
|---|---|---|
| `FTSE` | London close | `{"price":8310,"change":0.18}` |
| `SP` | S&P 500 close | `{"price":5232,"change":0.13}` |
| `Brent` | Brent crude | `{"price":109.96,"change":1.35}` |
| `GBP` | GBP/USD | `{"price":1.2987,"change":-0.02}` |
| `Gold` | Spot gold | `{"price":4812,"change":0.04}` |
| `EURGBP` | EUR/GBP | `{"price":0.8852,"change":0.02}` |
| `Gilt` | UK 10-year yield | `{"price":4.96,"change":0.00}` |
| `VIX` | Volatility index | `{"price":31.80,"change":0.00}` |
| `BTC` | Bitcoin | `{"price":70680,"change":0.26}` |
| `UST` | US 10-year yield | `{"price":4.52,"change":0.00}` |
| `ts` | ISO timestamp | `"2026-05-03T08:11:00+01:00"` |

`change` is **percent**, except for yields (`Gilt`, `UST`) where it is the absolute change in basis points expressed as a fraction.

## 3. Edition body structure

Order is fixed. Every edition contains, in this order:

1. **Edition header** — icon (`&#9788;` morning sun / `&#9789;` evening moon) + `<h2>Morning Briefing</h2>` or `<h2>Evening Briefing</h2>`
2. **`curated-meta`** — date in long British form (`Monday 4 May 2026 — HH:MM BST`)
3. **`impact-box`** — Feature A: "What It Means For You" — exactly **3** bullet points explaining practical personal impact for the reader
4. **`war-day-count`** — running count of the Iran war (started 28 February 2026); a single paragraph summarising the day's headline development. Use authoritative day count from the prompt; never calculate or guess.
5. **`curated-grid`** — two equal columns:
   - **Geo** column: `<h3><span class="dot geo"></span><span class="dot-label">GEO</span> Geopolitical</h3>` — exactly **5** stories
   - **UK** column: `<h3><span class="dot dom"></span><span class="dot-label">UK</span> UK Domestic Politics</h3>` — exactly **5** stories
6. **`one-to-read`** — Feature C: a single recommended long-form article. The `href` MUST be a full URL to a specific article, never a homepage. Source name appears as `<span class="otr-source">`.

For **evening editions only**: Feature D — `<div class="change-diff">` lines may be added at the end of curated-items where the position has materially changed since the morning edition. Maximum 2-3 across the edition. Each diff is one short line under 20 words. Format:

```html
<div class="change-diff">
  <span class="diff-arrow">&circlearrowright;</span>
  Friday close: Brent $109.96 &rarr; Monday close: Brent $114.44 (+6%).
</div>
```

For **Wednesday evening editions only when Parliament is sitting**: Feature E — PMQs summary section. Skip if recess.

## 4. curated-item structure

Every story (10 per edition) follows the same template:

```html
<div class="curated-item" data-time="HH:MM">
  <h4>Headline (max 12 words, declarative)</h4>
  <p>Summary, 2&ndash;4 sentences, max 80 words. Lead with the single most significant fact.</p>
  <details class="dive-deeper">
    <summary>Dive deeper</summary>
    <div class="deeper-content">3&ndash;5 sentences (max 120 words) of analysis: historical context, wider implications, specific data points, forward-looking indicator.</div>
  </details>
  <!-- Optional, evening only: -->
  <div class="change-diff"><span class="diff-arrow">&circlearrowright;</span> Before &rarr; After</div>
</div>
```

`data-time` = the time **the story actually broke or was first reported** in BST, NOT the briefing publication time. Research this for each story.

## 5. Layout consistency (critical)

Morning and evening editions **must** look identical in structure and density. The visual rhythm of every curated-item must be consistent across editions. The only permitted structural difference is the optional change-diff line in evening editions.

Hard limits:
- Headlines: **max 12 words**, declarative, direct
- Summary `<p>`: **2–4 sentences, max 80 words**, tight, factual, no padding
- Dive Deeper: **3–5 sentences, max 120 words**, analytical
- HTML entities: use `&mdash;` (—), `&ndash;` (–), `&lsquo;`/`&rsquo;` (' '), `&ldquo;`/`&rdquo;` (" "), `&pound;` (£) — never raw curly quotes or symbols

## 6. Writing style

Proper **British English** throughout. Tone mirrors the *Telegraph* news pages: authoritative, precise, measured, serious.

- British spellings: defence, programme, centre, organisation, analyse
- Declarative headlines, no clickbait, no questions
- Lead summaries with the single most significant fact
- Use semicolons and dashes confidently
- Never: Americanisms, casual language, exclamation marks, hedging adverbs ("arguably", "clearly", "obviously")

## 7. Sourcing

**Use only sources on `SOURCES.md`.** Cross-reference at least 2 approved sources before including a story. Banned domains are mechanically blocked by the pre-commit hook.

## 8. Rolling-week rule

Always show **7 full days of past editions** plus today. After every push, prune any edition whose `data-date` is more than 7 days before today. Never delete editions less than 7 days old — this has been broken multiple times historically.

## 9. Vetoed features (NEVER add)

- `refFiguresBar` or any UK statistics bar (Base Rate, CPI, Unemployment, GDP) below the markets ticker
- Search feature, search overlay, search button, keyboard shortcut
- Per-edition market strips (FTSE/Brent/GBP/Gold mini-bars) below individual edition headers — the global ticker is enough
- Premature future-dated editions

The pre-commit hook (`scripts/validate-index.py`) checks for these markers.

## 10. Breaking news banner

Banner is driven by JSON in `<script id="breaking-stories" type="application/json">`. The "Read more" modal reads ONLY from this JSON — if the JSON is empty, the modal shows just the headline with no further information. **Every breaking story MUST have a complete JSON entry; never update the inline `<span class="breaking-text">` alone.**

Required entry shape — all four fields are mandatory and validated by the pre-commit hook:
```json
{
  "posted": "ISO_TIMESTAMP",
  "headline": "Text — HH:MM BST",
  "category": "CATEGORY",
  "summary": "2-3 sentence description with the key context — what happened, who said what, where, and the immediate consequence. Minimum 1 sentence.",
  "facts": [
    {"label": "Key fact 1", "value": "Data"},
    {"label": "Key fact 2", "value": "Data"},
    {"label": "Key fact 3", "value": "Data"},
    {"label": "Key fact 4", "value": "Data"}
  ]
}
```

Aim for **3–4 facts** with concrete numbers, names, dates, or quoted positions — the modal renders these as a grid. Examples that work: `{"label": "Vote", "value": "335 against, 223 for (maj 112)"}`, `{"label": "Brent crude", "value": "$114.44 (+5.96%)"}`.

To clear: set the array to `[]` AND clear the inline `<span class="breaking-text">` text. The banner is `display:none` by default; JavaScript shows it when the array is non-empty. Do **not** add inline `display` styles to the banner element.

Rotation rule: each breaking story stays up for **3 hours**. Replace if a newer one arrives. If no replacement, leave for **up to 8 hours total**, then remove.

The pre-commit hook **fails the commit** if:
- Inline banner text is present but `breaking-stories` is empty
- Any story in the JSON is missing `headline`, `summary`, `facts`, or `posted`
- `facts` is not a non-empty array

## 11. Push checklist (every edition)

Before pushing:

1. ✅ New edition div added inside `#all-editions`
2. ✅ All 10 stories present (5 geo + 5 UK)
3. ✅ Each story has h4 + p + dive-deeper details
4. ✅ Evening editions: at most 2–3 change-diff lines
5. ✅ `data-markets` JSON has all 10 keys + ts
6. ✅ Embedded-markets script tag updated to current snapshot
7. ✅ Editions older than 7 days pruned
8. ✅ SW `CACHE_NAME` bumped (`daily-brief-vNN+1`)
9. ✅ One-To-Read present with full article URL (not homepage)
10. ✅ Pre-commit hook passes (`python3 scripts/validate-index.py`)
11. ✅ Push to **both** remotes: `git push origin main && git push org main`
12. ✅ Hard-refresh live URL and verify the new edition renders correctly

## 12. Reference: edition file size

A correctly structured edition is roughly **130 lines** of HTML and **5–6 KB** of source. Significantly smaller may indicate missing items or dive-deeper sections; significantly larger may indicate run-on summaries.

## 13. Templated subagent prompt

For autonomous briefing runs, dispatch a subagent with the prompt below (substituting today's date, edition type, and war-day count):

```
You are updating the Daily Briefing news page at /Users/ed/ed-news-briefing/index.html.

Today is YYYY-MM-DD. It is the {morning|evening} edition (HH:MM BST).

IMPORTANT TIMELINE: The US-Israel war on Iran started on 28 February 2026.
Today is DAY {N} of the conflict. If you reference the war's duration, you
MUST use 'Day {N}' — do NOT calculate or guess.

Read SOURCES.md and use only those outlets. Cross-reference at least 2
approved sources before including a story.

Read BRIEF_TEMPLATE.md and follow the structure exactly. In particular:
  - Add a new <div class="curated-edition {type}"> inside #all-editions
  - data-markets must include all 10 keys plus ts
  - 5 geo + 5 UK stories, each with h4 + p + dive-deeper details
  - data-time on each curated-item = when the story actually broke
  - Evening: include 2-3 change-diff lines on the most material movements
  - One-To-Read must be a full article URL, never a homepage
  - Bump sw.js CACHE_NAME by 1
  - Update embedded-markets script tag to current snapshot
  - Prune editions older than 7 days from today
  - Do NOT add any vetoed features (refFiguresBar, search, market strips)

Run `python3 scripts/validate-index.py` before staging. Push to BOTH
remotes: `git push origin main && git push org main`.
```

---

*This file should be updated whenever the structure changes. The pre-commit hook only catches what it knows to check; new conventions need to be added to both this file and `validate-index.py`.*
