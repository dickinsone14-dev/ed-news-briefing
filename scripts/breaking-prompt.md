<!--
Shared breaking-news prompt — single source of truth for local cron + cloud workflow.

Substitute the {{PLACEHOLDERS}} below before passing this content to Claude.

Placeholders:
  {{INDEX_FILE}}       absolute path to ed-news-briefing/index.html
  {{BRIEFING_DIR}}     absolute path to ed-news-briefing checkout
  {{TIME_NOW}}         e.g. 14:30
  {{TZ_LABEL}}         BST | GMT
  {{TODAY}}            e.g. 7 May 2026
  {{CURRENT_BANNER}}   the current inline banner text (may be empty)
-->
You are checking for breaking news to update the banner on a news briefing site.

Current time: {{TIME_NOW}} {{TZ_LABEL}}, {{TODAY}}.
Current banner text: '{{CURRENT_BANNER}}'

SOURCING (NON-NEGOTIABLE) — read {{BRIEFING_DIR}}/SOURCES.md and use ONLY the outlets on the approved list. If a breaking development only appears on outlets not on SOURCES.md (or appears on a banned source listed there), do NOT post it — wait for an approved outlet to corroborate. Cross-reference at least 2 approved sources before adding any story. The pre-commit hook will fail any commit that breaches this; your update must already comply.

Do the following:

1. Search the web for the single most significant breaking news development RIGHT NOW — focus on major geopolitical events (Iran/Middle East war, Ukraine-Russia, major attacks, leader changes), UK political crises, or dramatic market moves. Use only outlets on SOURCES.md.

2. Read {{INDEX_FILE}} — just the breaking-banner div and a quick scan of today's edition headlines.

3. Decide:
   a) If there is a GENUINELY major breaking development that is DIFFERENT from the current banner AND different from the stories already covered in today's editions: update BOTH the inline banner text AND the breaking-stories JSON array. Remove style="display:none" if present. The headline should relate to topics covered in the briefing so click-to-scroll linking can work.
   b) If the current banner is still the biggest breaking story: leave it unchanged. Do nothing.
   c) If there is NO significant breaking news right now: add style="display:none" to the breaking-banner div to hide it AND clear the breaking-stories JSON to []. The inline banner text should also be emptied.

CRITICAL — UPDATING THE BREAKING-STORIES JSON:
When adding or updating a breaking story, you MUST update the <script id="breaking-stories" type="application/json"> block. Every JSON entry MUST include all four fields below or the pre-commit hook will reject the commit:
{"headline": "The headline text — HH:MM {{TZ_LABEL}}", "posted": "ISO_TIMESTAMP", "category": "CATEGORY", "summary": "2-3 sentence summary of the development with key context — what happened, who said what, where, and the immediate consequence.", "facts": [{"label": "Key fact 1", "value": "Data"}, {"label": "Key fact 2", "value": "Data"}, {"label": "Key fact 3", "value": "Data"}]}

Include 3-4 facts with concrete numbers, names, dates, or quoted positions. The 'posted' field must be the current ISO timestamp. Keep any still-valid existing entries in the array (not older than 8h). This JSON powers the 'Read more' modal — empty modals are a known failure mode that the pre-commit hook now prevents.

IMPORTANT RULES:
- Only update if the news is genuinely BREAKING and MAJOR — not routine developments.
- The bar is high: war escalations, major casualties, leader deaths/resignations, market crashes (>3%), terror attacks, natural disasters.
- Do NOT update just because you found recent news — it must be significantly more important than the current banner.
- Run the validator before committing: `cd {{BRIEFING_DIR}} && python3 scripts/validate-index.py`. It must pass.
- If you make a change: git add index.html, commit with message 'Breaking banner update — {{TIME_NOW}} {{TZ_LABEL}}', then run: git push origin main && git push org main.
- If no change needed: do nothing, do not commit.
- Do NOT touch anything else in the file — only the breaking-banner div and breaking-stories JSON.
