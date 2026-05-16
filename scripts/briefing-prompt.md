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

The brief's credibility depends on every specific claim being traceable to approved-source reporting. This is not optional. Fabricated specifics — plausible-sounding figures, named individuals, percentages, basis-point moves, cover ratios, attendee lists, refinery names, ministerial actions — have repeatedly slipped past the validator. The validator catches banned domains; it cannot catch invented specifics. That is your job.

**The rule that prevents the failure mode is no fabrication, not no snippets.** Full-article retrieval via WebFetch is preferred but not required — search snippets that quote article text directly from an approved domain are an acceptable source. What is never acceptable is invention, extrapolation, or carrying yesterday's number forward as today's.

The rules that follow are how you prevent the failure mode.

**Rule 1 — What counts as a valid source.**
- Best: a full article retrieved via either the Firecrawl MCP (`mcp__firecrawl__firecrawl_scrape`) or WebFetch from an approved domain.
- Acceptable: a search-engine snippet that quotes article text directly from an approved domain (the snippet must contain the underlying article's words, not the search engine's paraphrase of them).
- Strongest: cross-referenced agreement across two or more approved sources.
- Not acceptable: search-engine summary paragraphs that paraphrase or aggregate; "plausible-sounding" details with no underlying article; carry-forward from yesterday without re-verification; rescaling yesterday's close to fake today's intraday.

If you only have a search-engine paraphrase (not direct article text), treat as a lead — search for a sibling article that quotes the underlying fact more directly, or omit.

**Scrape-tool selection (operationally important).** Different outlets work with different retrieval tools. Use the right one first:

| Outlet pattern | Primary tool | Notes |
|---|---|---|
| reuters.com, apnews.com, thetimes.com, thetimes.co.uk | **Firecrawl** (`mcp__firecrawl__firecrawl_scrape`) | WebFetch returns 403 on these. Firecrawl returns full article text including direct quotes. |
| wsj.com | **Firecrawl** | Returns the lead and first 2-3 paragraphs (paywall after) — usually enough for headline facts. |
| aljazeera.com, cnbc.com, timesofisrael.com, cnn.com / edition.cnn.com, npr.org | **WebFetch** | Generally reliable; faster than Firecrawl. Fall back to Firecrawl if 403. |
| bloomberg.com, ft.com, telegraph.co.uk, nytimes.com | **Search snippets only** | All three currently paywalled / blocked from both Firecrawl and WebFetch. Use direct-text search snippets per Tier 2 of this rule, or skip. |
| Think tanks, government sites, institutions (chathamhouse.org, iea.org, niesr.ac.uk, ecfr.eu, atlanticcouncil.org, crisisgroup.org, bankofengland.co.uk, gov.uk etc.) | **WebFetch** first, Firecrawl fallback | These usually allow WebFetch. |

When in doubt: try Firecrawl. It works on more domains than WebFetch and returns cleaner content. Treat a 403 from one tool as a signal to try the other before falling back to search snippets.

**Rule 2 — Cache what informed the brief.** Before writing any brief content, create the directory `{{BRIEFING_DIR}}/cache/{{TODAY}}/` and save the source material that informed each major claim. Save successfully-fetched WebFetch articles in full. Save the key direct-text search snippets as their own files (with `URL: <source-url>` as the first line and `(Search snippet content — full article 403'd on direct fetch; <outlet>'s own reporting language)` as the second line). Use the URL slug as the filename (e.g. `aljazeera-uks-keir-starmer-faces-likely-challenge.txt`). The pre-commit hook will check that any specific claim in the brief appears in at least one cached file.

**Rule 3 — Anchor-stories pre-check.** BEFORE drafting any HTML, write a short plain-text list to `{{BRIEFING_DIR}}/cache/{{TODAY}}/anchor-stories-{{EDITION}}.txt` of the top 5 stories you would expect a competent UK editor to lead with today, based on what your research confirms. Then check: are all 5 covered in your sources? Are any major stories of the day (e.g. a head-of-state visit, an oil-price shock, a UK Cabinet resignation, a market intervention) NOT on your list because you didn't search for them? If so, go back and search before writing. A brief that misses the biggest story of the day is broken, regardless of the other content.

**Rule 4 — Narrow rather than fabricate.** When sourcing is thin and a fact cannot be confirmed in any approved-source article or snippet, the correct response is to omit, not invent. Three rigorously sourced specifics beat ten plausible-sounding details with one invention. A shorter, harder brief is more valuable than a long brief with unsourced claims. Resist the instinct to fill structural slots with the type of content you remember from previous days — yesterday's gilt yield is not today's; yesterday's analyst forecast must be re-verified before reuse; yesterday's MP count cannot be extrapolated.

**Rule 5 — Sources-used appendix.** At the END of your brief, immediately before the closing `</div><!-- ── END {{EDITION}} ... -->` comment, add an HTML comment block listing every article or snippet that informed the brief and what it supported. Format:
```
<!-- SOURCES USED
- https://www.aljazeera.com/news/2026/5/14/... — BRICS attendees, Araghchi quote, Jaishankar quote
- https://www.cnbc.com/2026/05/13/... (search snippet — full article 403) — Brent close, WTI close
- https://www.bloomberg.com/news/... — Streeting resignation context
END SOURCES USED -->
```
This is the audit trail. The validator will parse it.

**Rule 6 — Direct quotes are anchors.** If you have a direct quote from a primary speaker (Trump, Starmer, an FM, a CEO) in either a retrieved article or a direct-text search snippet, use it. Direct quotes are the most defensible facts because they come straight from the article. Lean on them. Paraphrase when no quote exists but never invent attribution.

**Rule 7 — Market numbers especially.** Specific market levels (FTSE close, gilt yields, Brent settle, sterling cross) cause more sourcing failures than any other category because they are easily plausible-extrapolated. Either (a) cite a number from an approved-source article or direct snippet, in which case quote it precisely with a publication time, or (b) describe market behaviour narratively ("gilts extended their slide", "oil held near Tuesday's elevated close") without inventing a number. Do NOT rescale yesterday's close to fabricate today's open or close. Do NOT carry forward an analyst forecast without re-confirming it in today's sources.

**Rule 8 — Source list.** Read `{{BRIEFING_DIR}}/SOURCES.md` and use ONLY the outlets in its APPROVED DOMAINS block, no exceptions. Cross-reference at least 2 approved sources before including any story. The pre-commit hook fails any commit with a hyperlink outside that block.

**Rule 9 — Direct-quote density.** Each edition must contain a minimum of **3 direct quotes** from named primary speakers — for example: a head of state, a Cabinet minister, a foreign minister, a central-bank governor, a CEO, an officially-named analyst. A direct quote means an unbroken span of speech inside &ldquo;&hellip;&rdquo; that is attributed to a named individual and traceable to an approved-source article or direct-text snippet. Paraphrase does not count. Anonymous-source quotes (e.g. &ldquo;a Number 10 spokesman said&hellip;&rdquo;) count only when the source is identified to that level (named role at named institution). Direct quotes are the most defensible facts in the brief — lean on them. If you cannot find three direct quotes across your retrievals, the brief is under-sourced; search again before drafting.

**Rule 10 — Source breadth.** Each edition must draw information from **at least 10 distinct approved-source outlets** across its 10 curated-items, tracked in the SOURCES USED appendix. The goal is a more complete picture of each story, not more text — paraphrase is fine, sources do not need to be cited inline, and the **writing style stays the same** (authoritative, measured British English; no &ldquo;per Bloomberg&rdquo;-style attribution littered through the prose). What changes is research breadth, not prose. If your retrievals at the anchor-stories stage produce fewer than 10 outlets, search wider before drafting. Outlet variety is itself a quality signal &mdash; a brief that quietly draws on Reuters, AP, Al Jazeera, Bloomberg, CNBC, Times of Israel, the IAEA, the IEA, Chatham House and RUSI is structurally more complete than one that triples-down on two outlets.

**Rule 11 — Topic-triggered specialist checklist.** Specialist outlets exist on `SOURCES.md` because they are the canonical primary or analytic source for their topic. Bypassing them when their topic is in scope is structural under-sourcing. Before drafting, identify which themes the brief covers and consult the matching specialist outlets. Include at least one outlet from each triggered theme in the SOURCES USED appendix wherever the story content reasonably permits.

| Theme triggered by the brief | Outlets to consult |
|---|---|
| Energy / oil / Hormuz | iea.org, eia.gov, opec.org |
| UK fiscal / monetary policy | bankofengland.co.uk, obr.uk, ifs.org.uk, niesr.ac.uk, nao.org.uk, resolutionfoundation.org, hmrc.gov.uk, ons.gov.uk |
| Nuclear / IAEA proceedings | iaea.org, bellingcat.com |
| UK polling / electoral data | yougov.com, opinium.com, ipsos.com, moreincommon.com, survation.com, electoralcalculus.co.uk |
| Military operations / defence | janes.com, understandingwar.org, rusi.org, bellingcat.com, defensenews.com |
| EU / foreign-policy analysis | ecfr.eu, chathamhouse.org, atlanticcouncil.org, carnegieendowment.org, crisisgroup.org |
| International institutions / multilateral diplomacy | imf.org, worldbank.org, oecd.org, nato.int, ecb.europa.eu, consilium.europa.eu |
| European national coverage | lemonde.fr (FR), faz.net (DE), elpais.com (ES), irishtimes.com (IE) |
| Health / NHS clinical data | bma.org.uk |
| Cost of living / food poverty / motoring | trusselltrust.org.uk, theaa.com, rac.co.uk |

**Rule 12 — Rotate, don&rsquo;t recycle.** Before drafting, scan the SOURCES USED appendices of the last 3-5 published editions in `index.html`. Identify the outlets that appeared in three or more of those editions (typically Al Jazeera, CNBC, Bloomberg, Times of Israel — the "habitual" outlets). For today's brief, deliberately favour outlets that have appeared in zero or one of the last 3-5 editions where the story content permits. Habitual outlets are still allowed; they must not dominate. The goal is genuine rotation through the 97-outlet pool over time, not just diversity within a single edition. Habit is the failure mode &mdash; if today's brief draws from the same 10 outlets as yesterday's, the rotation is broken even if Rule 10 is technically satisfied.

═══════════════════════════════════════════════════════════════
STRUCTURE (NON-NEGOTIABLE)
═══════════════════════════════════════════════════════════════

Read `{{BRIEFING_DIR}}/BRIEF_TEMPLATE.md` and follow it exactly. The structure is summarised below for reference but BRIEF_TEMPLATE.md is canonical.

IMPORTANT: The page uses an archive system. All curated editions live inside `<div id="all-editions">`. Each edition has data-date and data-time attributes. JavaScript sorts them into today vs archive automatically.

═══════════════════════════════════════════════════════════════
ORDER OF OPERATIONS
═══════════════════════════════════════════════════════════════

1. **Research.** Search the web for today's top geopolitical news (Iran/Middle East, Ukraine-Russia, head-of-state diplomacy, market shocks) AND today's top UK domestic politics — using ONLY outlets on SOURCES.md.

2. **Retrieve.** For each lead, fetch the full article using the right tool for the domain — see the **Scrape-tool selection** table under Rule 1. Use Firecrawl (`mcp__firecrawl__firecrawl_scrape`) as primary for Reuters, AP, Times of London and WSJ; WebFetch as primary for Al Jazeera, CNBC, Times of Israel, CNN, NPR; try the other tool as fallback before treating as failed. Save each successful fetch to `{{BRIEFING_DIR}}/cache/{{TODAY}}/<slug>.txt`. If both tools return 403/404/redirects/truncation, fall back to the search-engine snippet — but only if that snippet quotes article text directly (not a search-engine summary). Save direct-text snippets to the same cache directory with a header noting they are snippet-sourced.

3. **Anchor-stories pre-check.** Write `{{BRIEFING_DIR}}/cache/{{TODAY}}/anchor-stories-{{EDITION}}.txt` listing the top 5 stories you would expect to lead with. If any major story you should have covered isn't in your retrievals, go back to step 1 and search again.

4. **Read** the current `index.html`.

5. **Add edition.** Inside `<div id="all-editions">`, ADD a NEW curated-edition div for today's {{EDITION}}. Do NOT replace or remove any existing editions other than the pruning step below. The new div must have these attributes: `class="curated-edition {{EDITION}}" data-date="{{TODAY}}" data-time="{{TIME_DISPLAY}}" data-markets='JSON'` — where JSON contains the market data you have actually sourced. Include all 10 market keys: FTSE, SP, Brent, GBP, Gold, EURGBP, Gilt, VIX, BTC, UST. For any key where you cannot source a today-of-publication figure, use the most recent figure you can source and timestamp it to that article's publication time (the live ticker pulls real values from an API; the data-markets attribute is a fallback).

**TIME-STAMP DISCIPLINE — NEVER APPROXIMATE.** `{{TIME_DISPLAY}}` is the actual current local time at the moment the brief is being produced — auto-substituted from the LaunchAgent script. When producing a brief manually, you MUST use the actual current time (`date "+%H:%M"`), not a fixed convention like "10:00" or "18:00". The same time must appear in three places consistently: the curated-edition `data-time` attribute, the `data-markets` `ts` ISO timestamp, and the `<div class="curated-meta">…— HH:MM BST</div>` text. The edition's opening and closing HTML comments (`<!-- ── MORNING DD MMM (HH:MM) ── -->`) should match. Edition timestamps are the live record of when the brief was published; approximating them is a quiet form of fabrication.

6. **Use this internal structure.** edition-header with icon (`&#9788;` for morning / `&#9789;` for evening), h2, curated-meta with `'{{DATE_DISPLAY}} — {{TIME_DISPLAY}} {{TZ_LABEL}}'`, then curated-grid with two curated-columns (geo + dom). The geo column heading must be 'Geopolitical' and the dom column heading must be 'UK Domestic Politics'. Each column has 5 curated-items. Each curated-item must have: (a) a `data-time` attribute set to the approximate time (in {{TZ_LABEL}}) when that story actually broke or was first reported — NOT the briefing publication time; and (b) a `data-slug` attribute, the URL-safe stable identifier for that headline (lowercase, alphanumeric and hyphens only, ~4–6 significant words from the h4, e.g. `streeting-resigns` or `trump-xi-summit-closes`). Each curated-item's content: h4 (headline), p (summary), then `<details class="dive-deeper"><summary>Dive deeper</summary><div class="deeper-content">EXTENDED ANALYSIS</div></details>`. The extended analysis should add 3-5 sentences of deeper context. The `data-slug` is what per-headline deep-link URLs reference (e.g. `/briefings/2026-05-14-morning/streeting-resigns/`) — once published, never edit a slug without redirects.

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

**FEATURE E: PMQs Summary (WEDNESDAY EVENING ONLY)** — If today is a Wednesday and this is the evening edition, add a PMQs summary section. Only if Parliament is sitting — skip if in recess.

VETOED FEATURES — DO NOT ADD ANY OF THESE:
- Do NOT add a refFiguresBar or any UK statistics bar (Base Rate, CPI, Unemployment, GDP)
- Do NOT add `change-diff` &ldquo;What Changed Today&rdquo; lines &mdash; the former Feature D is vetoed (Ed 2026-05-16: visually attached to the last headline and confusing). No <div class="change-diff"> elements in any edition.
- Do NOT add a search feature
- Do NOT add per-edition market strips below edition headers

═══════════════════════════════════════════════════════════════
PRUNING, MARKETS, BREAKING, COMMIT
═══════════════════════════════════════════════════════════════

8. **Prune (AUTOMATIC, NEVER SKIP).** Remove any curated-edition divs where data-date is before {{SEVEN_DAYS_AGO}}. The site MUST show 7 full days of past editions plus today. This is not optional and is not something to flag to the user — it happens silently as part of every briefing run. If the validator emits a warning about editions older than the rolling window, your brief is not done until those editions have been deleted.

9. **Update embedded markets.** Find the `<script id="embedded-markets" type="application/json">` tag and replace its JSON content with the same fresh data used in the new edition's data-markets attribute. Same sourcing rule: numbers must come from retrieved articles, not extrapolation.

10. **Breaking news banner.** The banner uses a JSON array in `<script id="breaking-stories" type="application/json">`. To add a breaking story, add an object with: `{"posted":"ISO_TIMESTAMP","headline":"Text — HH:MM {{TZ_LABEL}}","category":"CATEGORY","summary":"2-3 sentence description","facts":[{"label":"Key","value":"Data"}]}`. Every entry MUST include headline + posted + summary + non-empty facts array — the pre-commit hook fails commits with incomplete entries. To clear breaking news, set the array to `[]`. Do NOT add inline display styles to the banner HTML element.

11. **Bump service worker.** In `{{BRIEFING_DIR}}/sw.js`, increment the integer in `const CACHE_NAME = 'daily-brief-vN';` by 1.

12. **Validate.** Run `cd {{BRIEFING_DIR}} && python3 scripts/validate-index.py`. It must pass before the commit. The validator checks: div balance inside #all-editions, embedded-markets JSON, all data-markets attributes, edition open/close counts, banned domains, breaking-news JSON completeness, hyperlinks against the SOURCES.md allow-list, absence of vetoed feature markers, and (when extended) sources-used appendix presence + fact-trace coverage.

13. **Regenerate deep-link pages and sitemaps.** Run `cd {{BRIEFING_DIR}} && python3 scripts/build-deeplink-pages.py && python3 scripts/build-sitemap.py && python3 scripts/build-news-sitemap.py`. This regenerates the static `/briefings/YYYY-MM-DD-{edition}/index.html` and per-headline pages for SEO, refreshes `sitemap.xml` (full list of URLs), and refreshes `news-sitemap.xml` (Google News sitemap with only articles from the last 48 hours). Required after any edition is added or pruned.

14. **Commit.** `git add index.html sw.js cache/{{TODAY}}/ briefings/ sitemap.xml news-sitemap.xml`, commit with message `Update {{EDITION}} briefing — {{DATE_DISPLAY}}`, then run: `git push origin main && git push org main`.

Do NOT change the live RSS feed section, styling, JavaScript, or any other part of the page. Only add the new edition, remove old ones, update embedded-markets, update breaking stories JSON, write the cache files, and regenerate the per-URL pages + sitemap.
