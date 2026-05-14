<!--
Shared briefing prompt — single source of truth for local cron + cloud workflow.

Substitute the {{PLACEHOLDERS}} below before passing this content to Claude.
The substituted text is the full user prompt; nothing else is needed.

Placeholders:
  {{TODAY}}            e.g. 2026-05-14
  {{EDITION}}          morning | evening
  {{TIME_DISPLAY}}     e.g. 07:55
  {{TZ_LABEL}}         BST | GMT
  {{IRAN_WAR_DAY}}     integer
  {{DATE_DISPLAY}}     e.g. Thursday 14 May 2026
  {{SEVEN_DAYS_AGO}}   e.g. 2026-05-07
  {{BRIEFING_DIR}}     absolute path to ed-news-briefing checkout

The line below this comment is the start of the prompt body. Everything from
"You are updating" to the final paragraph is what Claude sees.
-->
You are updating the Daily Briefing news page at {{BRIEFING_DIR}}/index.html.

Today is {{TODAY}}. It is the {{EDITION}} edition ({{TIME_DISPLAY}} {{TZ_LABEL}}).

IMPORTANT TIMELINE: The US-Israel war on Iran started on 28 February 2026. Today is DAY {{IRAN_WAR_DAY}} of the conflict. If you reference the war's duration in any headline or text, you MUST use 'Day {{IRAN_WAR_DAY}}' — do NOT guess or calculate the day count yourself.

═══════════════════════════════════════════════════════════════
SOURCING DISCIPLINE — NON-NEGOTIABLE, READ BEFORE ANYTHING ELSE
═══════════════════════════════════════════════════════════════

The brief's credibility depends on every specific claim being traceable to an article you actually retrieved from the approved-sources list. This is not optional. Fabricated specifics — plausible-sounding figures, named individuals, percentages, basis-point moves, cover ratios, attendee lists, refinery names, ministerial actions — have repeatedly slipped past the validator. The validator catches banned domains; it cannot catch invented specifics. That is your job.

The rules that follow are how you prevent that failure mode.

**Rule 1 — Full articles, not snippets.** Search results give you LEADS. They do NOT give you FACTS. Before any specific claim enters the brief, you must successfully fetch (via WebFetch) the full article that supports it. If WebFetch returns 403, 404, redirect-loops, or a truncated page, that source has not been retrieved — try a sibling article, switch outlets, or OMIT the dependent claim. Never carry a fact across the search-snippet/article-content boundary on the assumption it will be true.

**Rule 2 — Cache every retrieved article.** Before writing any brief content, create the directory `{{BRIEFING_DIR}}/cache/{{TODAY}}/` and save every successfully-fetched article to a file inside it. Use the URL slug as the filename (e.g. `aljazeera-uks-keir-starmer-faces-likely-challenge.txt`). Each file's first line must be `URL: <full-url>`; the rest is the article text you extracted. The pre-commit hook will check that any specific claim in the brief appears in at least one cached file.

**Rule 3 — Anchor-stories pre-check.** BEFORE drafting any HTML, write a short plain-text list to `{{BRIEFING_DIR}}/cache/{{TODAY}}/anchor-stories-{{EDITION}}.txt` of the top 5 stories you would expect a competent UK editor to lead with today, based on what your retrievals confirm. Then check: are all 5 covered in your retrieved sources? Are any major stories of the day (e.g. a head-of-state visit, an oil-price shock, a UK Cabinet resignation, a market intervention) NOT on your list because you didn't search for them? If so, go back and search before writing. A brief that misses the biggest story of the day is broken, regardless of the other content.

**Rule 4 — Narrow rather than fabricate.** When fetches fail and a fact cannot be confirmed, the correct response is to omit, not invent. Three rigorously sourced specifics beat ten plausible-sounding details with one invention. A shorter, harder brief is more valuable than a long brief with unsourced claims. Resist the instinct to fill structural slots with the type of content you remember from previous days — yesterday's gilt yield is not today's; yesterday's analyst forecast must be re-verified before reuse; yesterday's MP count cannot be extrapolated.

**Rule 5 — Sources-used appendix.** At the END of your brief, immediately before the closing `</div><!-- ── END {{EDITION}} ... -->` comment, add an HTML comment block listing every article you successfully retrieved and what it supported. Format:
```
<!-- SOURCES USED
- https://www.aljazeera.com/news/2026/5/14/... — BRICS attendees, Araghchi quote, Jaishankar quote
- https://www.cnbc.com/2026/05/13/... — Brent close, WTI close
- https://www.bloomberg.com/news/... — Streeting resignation context
END SOURCES USED -->
```
This is the audit trail. The validator will parse it.

**Rule 6 — Direct quotes are anchors.** If you have a direct quote from a primary speaker (Trump, Starmer, an FM, a CEO), use it. Direct quotes are the most defensible facts because they come straight from the article. Lean on them. Paraphrase when no quote exists but never invent attribution.

**Rule 7 — Market numbers especially.** Specific market levels (FTSE close, gilt yields, Brent settle, sterling cross) cause more sourcing failures than any other category because they are easily plausible-extrapolated. Either (a) cite a number from an article you fetched, in which case quote it precisely with a publication time, or (b) describe market behaviour narratively ("gilts extended their slide", "oil held near Tuesday's elevated close") without inventing a number. Do NOT rescale yesterday's close to fabricate today's open or close. Do NOT carry forward an analyst forecast without re-fetching its source today.

**Rule 8 — Source list.** Read `{{BRIEFING_DIR}}/SOURCES.md` and use ONLY the outlets in its APPROVED DOMAINS block, no exceptions. Cross-reference at least 2 approved sources before including any story. The pre-commit hook fails any commit with a hyperlink outside that block.

═══════════════════════════════════════════════════════════════
STRUCTURE (NON-NEGOTIABLE)
═══════════════════════════════════════════════════════════════

Read `{{BRIEFING_DIR}}/BRIEF_TEMPLATE.md` and follow it exactly. The structure is summarised below for reference but BRIEF_TEMPLATE.md is canonical.

IMPORTANT: The page uses an archive system. All curated editions live inside `<div id="all-editions">`. Each edition has data-date and data-time attributes. JavaScript sorts them into today vs archive automatically.

═══════════════════════════════════════════════════════════════
ORDER OF OPERATIONS
═══════════════════════════════════════════════════════════════

1. **Research.** Search the web for today's top geopolitical news (Iran/Middle East, Ukraine-Russia, head-of-state diplomacy, market shocks) AND today's top UK domestic politics — using ONLY outlets on SOURCES.md.

2. **Retrieve.** For each lead, WebFetch the full article. Save each successful fetch to `{{BRIEFING_DIR}}/cache/{{TODAY}}/<slug>.txt`. Treat 403/404/redirects/truncation as fetch failures — do not use those articles as sources.

3. **Anchor-stories pre-check.** Write `{{BRIEFING_DIR}}/cache/{{TODAY}}/anchor-stories-{{EDITION}}.txt` listing the top 5 stories you would expect to lead with. If any major story you should have covered isn't in your retrievals, go back to step 1 and search again.

4. **Read** the current `index.html`.

5. **Add edition.** Inside `<div id="all-editions">`, ADD a NEW curated-edition div for today's {{EDITION}}. Do NOT replace or remove any existing editions other than the pruning step below. The new div must have these attributes: `class="curated-edition {{EDITION}}" data-date="{{TODAY}}" data-time="{{TIME_DISPLAY}}" data-markets='JSON'` — where JSON contains the market data you have actually sourced. Include all 10 market keys: FTSE, SP, Brent, GBP, Gold, EURGBP, Gilt, VIX, BTC, UST. For any key where you cannot source a today-of-publication figure, use the most recent figure you can source and timestamp it to that article's publication time (the live ticker pulls real values from an API; the data-markets attribute is a fallback).

6. **Use this internal structure.** edition-header with icon (`&#9788;` for morning / `&#9789;` for evening), h2, curated-meta with `'{{DATE_DISPLAY}} — {{TIME_DISPLAY}} {{TZ_LABEL}}'`, then curated-grid with two curated-columns (geo + dom). The geo column heading must be 'Geopolitical' and the dom column heading must be 'UK Domestic Politics'. Each column has 5 curated-items. Each curated-item must have a `data-time` attribute set to the approximate time (in {{TZ_LABEL}}) when that story actually broke or was first reported — NOT the briefing publication time. Each curated-item must have: h4 (headline), p (summary), then `<details class="dive-deeper"><summary>Dive deeper</summary><div class="deeper-content">EXTENDED ANALYSIS</div></details>`. The extended analysis should add 3-5 sentences of deeper context.

7. **Sources-used appendix.** Add the HTML comment block specified in Rule 5 above immediately before the edition's closing `</div>`.

LAYOUT CONSISTENCY — Critical. Morning and evening editions MUST look identical in structure and density:
- Headlines (h4): Maximum 12 words. Declarative and direct.
- Summary paragraphs (p): 2-4 sentences, maximum 80 words. Tight, factual, no padding. Lead with the single most significant fact.
- Dive Deeper sections: 3-5 sentences of analysis, maximum 120 words.
- Visual rhythm consistent across all curated-items.
- Evening editions must NOT look different from morning editions. The only permitted structural addition is the optional change-diff line (Feature D).

WRITING STYLE — Proper British English throughout. Tone mirrors The Daily Telegraph's news pages: authoritative, precise, measured, serious. British spellings (defence, programme, centre). Headlines declarative. Summaries lead with the most significant fact. Use semicolons and dashes confidently. Never use Americanisms, casual language, or exclamation marks.

═══════════════════════════════════════════════════════════════
ADDITIONAL CONTENT FEATURES
═══════════════════════════════════════════════════════════════

**FEATURE A: 'What It Means For You' box** — After curated-meta, BEFORE curated-grid, add: `<div class="impact-box"><h3 class="impact-heading">What It Means For You</h3><ul class="impact-list"><li>ITEM 1</li><li>ITEM 2</li><li>ITEM 3</li></ul></div>`. 3 bullet points explaining practical personal impact. Each bullet must itself be traceable to retrieved sources.

**FEATURE B: 'Iran War — Day N' summary** — After impact-box, before curated-grid, add: `<div class="war-day-count"><p><strong>Iran War — Day {{IRAN_WAR_DAY}}.</strong> The war started 28 February 2026. ONE PARAGRAPH summarising today's headline development.</p></div>`. The paragraph must summarise facts from retrieved articles only.

**FEATURE C: 'One To Read' recommendation** — At the END of the edition div (after curated-grid, before the sources-used comment), add a one-to-read div. Pick a genuinely excellent long-form article from an outlet on SOURCES.md that you successfully fetched. The href MUST be a full URL to the specific article — NEVER a homepage URL.

**FEATURE D: 'What Changed Today' diffs (EVENING ONLY)** — Maximum 2-3 items with the most significant developments. Each diff must be ONE short line (under 20 words). Format: `<div class="change-diff"><span class="diff-arrow">&circlearrowright;</span> Before &rarr; After</div>`.

**FEATURE E: PMQs Summary (WEDNESDAY EVENING ONLY)** — If today is a Wednesday and this is the evening edition, add a PMQs summary section. Only if Parliament is sitting — skip if in recess.

VETOED FEATURES — DO NOT ADD ANY OF THESE:
- Do NOT add a refFiguresBar or any UK statistics bar (Base Rate, CPI, Unemployment, GDP)
- Do NOT add a search feature
- Do NOT add per-edition market strips below edition headers

═══════════════════════════════════════════════════════════════
PRUNING, MARKETS, BREAKING, COMMIT
═══════════════════════════════════════════════════════════════

8. **Prune.** Remove any curated-edition divs where data-date is before {{SEVEN_DAYS_AGO}}. The site MUST show 7 full days of past editions plus today.

9. **Update embedded markets.** Find the `<script id="embedded-markets" type="application/json">` tag and replace its JSON content with the same fresh data used in the new edition's data-markets attribute. Same sourcing rule: numbers must come from retrieved articles, not extrapolation.

10. **Breaking news banner.** The banner uses a JSON array in `<script id="breaking-stories" type="application/json">`. To add a breaking story, add an object with: `{"posted":"ISO_TIMESTAMP","headline":"Text — HH:MM {{TZ_LABEL}}","category":"CATEGORY","summary":"2-3 sentence description","facts":[{"label":"Key","value":"Data"}]}`. Every entry MUST include headline + posted + summary + non-empty facts array — the pre-commit hook fails commits with incomplete entries. To clear breaking news, set the array to `[]`. Do NOT add inline display styles to the banner HTML element.

11. **Bump service worker.** In `{{BRIEFING_DIR}}/sw.js`, increment the integer in `const CACHE_NAME = 'daily-brief-vN';` by 1.

12. **Validate.** Run `cd {{BRIEFING_DIR}} && python3 scripts/validate-index.py`. It must pass before the commit. The validator checks: div balance inside #all-editions, embedded-markets JSON, all data-markets attributes, edition open/close counts, banned domains, breaking-news JSON completeness, hyperlinks against the SOURCES.md allow-list, absence of vetoed feature markers, and (when extended) sources-used appendix presence + fact-trace coverage.

13. **Commit.** `git add index.html sw.js cache/{{TODAY}}/`, commit with message `Update {{EDITION}} briefing — {{DATE_DISPLAY}}`, then run: `git push origin main && git push org main`.

Do NOT change the live RSS feed section, styling, JavaScript, or any other part of the page. Only add the new edition, remove old ones, update embedded-markets, update breaking stories JSON, and write the cache files.
