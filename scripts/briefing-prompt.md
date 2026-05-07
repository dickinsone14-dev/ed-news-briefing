<!--
Shared briefing prompt — single source of truth for local cron + cloud workflow.

Substitute the {{PLACEHOLDERS}} below before passing this content to Claude.
The substituted text is the full user prompt; nothing else is needed.

Placeholders:
  {{TODAY}}            e.g. 2026-05-07
  {{EDITION}}          morning | evening
  {{TIME_DISPLAY}}     e.g. 07:55
  {{TZ_LABEL}}         BST | GMT
  {{IRAN_WAR_DAY}}     integer
  {{DATE_DISPLAY}}     e.g. Thursday 7 May 2026
  {{SEVEN_DAYS_AGO}}   e.g. 2026-04-30
  {{BRIEFING_DIR}}     absolute path to ed-news-briefing checkout

The line below this comment is the start of the prompt body. Everything from
"You are updating" to the final paragraph is what Claude sees.
-->
You are updating the Daily Briefing news page at {{BRIEFING_DIR}}/index.html.

Today is {{TODAY}}. It is the {{EDITION}} edition ({{TIME_DISPLAY}} {{TZ_LABEL}}).

IMPORTANT TIMELINE: The US-Israel war on Iran started on 28 February 2026. Today is DAY {{IRAN_WAR_DAY}} of the conflict. If you reference the war's duration in any headline or text, you MUST use 'Day {{IRAN_WAR_DAY}}' — do NOT guess or calculate the day count yourself.

SOURCING (NON-NEGOTIABLE) — read {{BRIEFING_DIR}}/SOURCES.md and use ONLY the outlets on the approved list, no exceptions. Cross-reference at least 2 approved sources before including any story. If a story only appears on outlets not on SOURCES.md (or appears on a banned source listed there), do NOT include it. The pre-commit hook will fail any commit that contains a hyperlink to a domain not in the APPROVED DOMAINS block of SOURCES.md, so source rigour is mechanically enforced — your prompt must already comply or the push will be rejected.

STRUCTURE (NON-NEGOTIABLE) — read {{BRIEFING_DIR}}/BRIEF_TEMPLATE.md and follow it exactly. The structure is summarised below for reference but BRIEF_TEMPLATE.md is canonical.

IMPORTANT: The page uses an archive system. All curated editions live inside <div id="all-editions">. Each edition has data-date and data-time attributes. JavaScript sorts them into today vs archive automatically.

Do the following:

1. Search the web for today's top geopolitical news (Iran/Middle East conflict, Ukraine-Russia, major world events, financial markets) — using ONLY outlets on SOURCES.md.

2. Search the web for today's top UK domestic politics news — using ONLY outlets on SOURCES.md.

3. Read the current index.html.

4. Inside the <div id="all-editions"> section, ADD a NEW curated-edition div for today's {{EDITION}}. Do NOT replace or remove any existing editions other than the pruning step below.

5. The new div must have these attributes: class="curated-edition {{EDITION}}" data-date="{{TODAY}}" data-time="{{TIME_DISPLAY}}" data-markets='JSON' — where JSON contains the market data you found in step 9. Include all 10 market keys: FTSE, SP, Brent, GBP, Gold, EURGBP, Gilt, VIX, BTC, UST.

6. Use this structure: edition-header with icon (&#9788; for morning / &#9789; for evening), h2, curated-meta with '{{DATE_DISPLAY}} — {{TIME_DISPLAY}} {{TZ_LABEL}}', then curated-grid with two curated-columns (geo + dom). The geo column heading must be 'Geopolitical' and the dom column heading must be 'UK Domestic Politics'. Each column has 5 curated-items. Each curated-item must have a data-time attribute set to the approximate time (in {{TZ_LABEL}}) when that story actually broke or was first reported — NOT the briefing publication time. Research when each event occurred. Each curated-item must have: h4 (headline), p (summary), then a <details class="dive-deeper"><summary>Dive deeper</summary><div class="deeper-content">EXTENDED ANALYSIS</div></details>. The extended analysis should add 3-5 sentences of deeper context.

LAYOUT CONSISTENCY — This is critical. Morning and evening editions MUST look identical in structure and density. Every edition must follow the same uniform layout:
- Headlines (h4): Maximum 12 words. Declarative and direct.
- Summary paragraphs (p): 2-4 sentences, maximum 80 words. Tight, factual, no padding. Lead with the single most significant fact.
- Dive Deeper sections: 3-5 sentences of analysis, maximum 120 words.
- The visual rhythm of every curated-item must be consistent.
- Evening editions must NOT look different from morning editions. The only permitted structural addition is the optional change-diff line (Feature D).

WRITING STYLE — Write in proper British English throughout. The tone should mirror The Daily Telegraph's news pages: authoritative, precise, measured, and serious. Use British spellings (defence, programme, centre). Headlines should be declarative. Summaries should lead with the most significant fact. Use semicolons and dashes confidently. Never use Americanisms, casual language, or exclamation marks.

ADDITIONAL CONTENT FEATURES:

FEATURE A: 'What It Means For You' box — After curated-meta, BEFORE curated-grid, add: <div class="impact-box"><h3 class="impact-heading">What It Means For You</h3><ul class="impact-list"><li>ITEM 1</li><li>ITEM 2</li><li>ITEM 3</li></ul></div>. 3 bullet points explaining practical personal impact.

FEATURE B: 'Iran War — Day N' summary — After impact-box, before curated-grid, add: <div class="war-day-count"><p><strong>Iran War — Day {{IRAN_WAR_DAY}}.</strong> The war started 28 February 2026. ONE PARAGRAPH summarising today's headline development.</p></div>.

FEATURE C: 'One To Read' recommendation — At the END of the edition div (after curated-grid), add a one-to-read div. Pick a genuinely excellent long-form article from an outlet on SOURCES.md. The href MUST be a full URL to the specific article — NEVER a homepage URL. NEVER use an outlet not on SOURCES.md.

FEATURE D: 'What Changed Today' diffs (EVENING ONLY) — Maximum 2-3 items with the most significant developments. Each diff must be ONE short line (under 20 words). Format: <div class="change-diff"><span class="diff-arrow">&circlearrowright;</span> Before &rarr; After</div>.

FEATURE E: PMQs Summary (WEDNESDAY EVENING ONLY) — If today is a Wednesday and this is the evening edition, add a PMQs summary section. Only if Parliament is sitting — skip if in recess.

VETOED FEATURES — DO NOT ADD ANY OF THESE:
- Do NOT add a refFiguresBar or any UK statistics bar (Base Rate, CPI, Unemployment, GDP)
- Do NOT add a search feature
- Do NOT add per-edition market strips below edition headers

7. Remove any curated-edition divs where data-date is before {{SEVEN_DAYS_AGO}}. The site MUST show 7 full days of past editions plus today.

8. Update the embedded market data: find the <script id="embedded-markets" type="application/json"> tag and replace its JSON content with the same fresh data used in the new edition's data-markets attribute.

9. BREAKING NEWS BANNER — The banner uses a JSON array in <script id="breaking-stories" type="application/json">. To add a breaking story, add an object with: {"posted":"ISO_TIMESTAMP","headline":"Text — HH:MM {{TZ_LABEL}}","category":"CATEGORY","summary":"2-3 sentence description","facts":[{"label":"Key","value":"Data"}]}. Every entry MUST include headline + posted + summary + non-empty facts array — the pre-commit hook fails commits with incomplete entries. To clear breaking news, set the array to []. The banner CSS is display:none by default — JavaScript shows it when stories exist. Do NOT add inline display styles to the banner HTML element.

10. Bump the service worker version: in {{BRIEFING_DIR}}/sw.js, increment the integer in `const CACHE_NAME = 'daily-brief-vN';` by 1.

11. Run the validator: `cd {{BRIEFING_DIR}} && python3 scripts/validate-index.py`. It must pass before the commit. The validator checks: div balance inside #all-editions, embedded-markets JSON, all data-markets attributes, edition open/close counts, banned domains, breaking-news JSON completeness, hyperlinks against the SOURCES.md allow-list, and absence of vetoed feature markers.

12. git add index.html sw.js, commit with message 'Update {{EDITION}} briefing — {{DATE_DISPLAY}}', then run: git push origin main && git push org main.

Do NOT change the live RSS feed section, styling, JavaScript, or any other part of the page. Only add the new edition, remove old ones, update embedded-markets, and update breaking stories JSON.
