#!/usr/bin/env python3
"""Apply a Daily Brief edition to index.html + sw.js.
Usage: python3 apply_brief.py YYYY-MM-DD morning|evening HH:MM
Reads from this script's directory:
  edition_<edition>_<date>.html   (with __TIME__ / __MARKETS__ placeholders)
  markets_<edition>_<date>.json   ({"FTSE":{...},...}, 10 keys, no ts)
  drivers_<edition>_<date>.json   ({"FTSE":{"up":[..],"down":[..]},...})
Refuses if an edition of that date+type already exists.
"""
import json, re, sys
from pathlib import Path

DATE, EDITION, TIME = sys.argv[1], sys.argv[2], sys.argv[3]
assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", DATE)
assert EDITION in ("morning", "evening")
assert re.fullmatch(r"\d\d:\d\d", TIME)

ROOT = Path("/Users/ed/ed-news-briefing")
INDEX, SW = ROOT / "index.html", ROOT / "sw.js"
S = Path(__file__).parent
suffix = f"{EDITION}_{DATE}"

html = INDEX.read_text(encoding="utf-8")
if f'class="curated-edition {EDITION}" data-date="{DATE}"' in html:
    sys.exit(f"ABORT: {DATE} {EDITION} edition already present")

KEYS = {"FTSE","SP","Brent","GBP","Gold","EURGBP","Gilt","VIX","BTC","UST"}
markets = json.loads((S / f"markets_{suffix}.json").read_text())
assert set(markets) == KEYS, set(markets) ^ KEYS
offset = "+01:00"  # BST — valid until the last Sunday of October
markets["ts"] = f"{DATE}T{TIME}:00{offset}"
markets_json = json.dumps(markets, separators=(",", ":"))
assert "'" not in markets_json

edition = (S / f"edition_{suffix}.html").read_text(encoding="utf-8")
edition = edition.replace("__TIME__", TIME).replace("__MARKETS__", markets_json)
assert "__TIME__" not in edition and "__MARKETS__" not in edition

anchor = ' <div id="all-editions" style="display:none;">\n'
assert html.count(anchor) == 1
html = html.replace(anchor, anchor + edition, 1)

html, n = re.subn(r'(<script id="embedded-markets" type="application/json">)\s*.*?\s*(</script>)',
                  lambda m: m.group(1) + "\n" + markets_json + "\n" + m.group(2), html, count=1, flags=re.DOTALL)
assert n == 1, "embedded-markets not replaced"

UPDATED = f"{DATE} {TIME} (reviewed at publication)"
drivers = json.loads((S / f"drivers_{suffix}.json").read_text())
m = re.search(r'(<script id="market-descriptions" type="application/json">)\s*\n(.*?)\n(</script>)', html, re.DOTALL)
desc = json.loads(m.group(2))
assert set(desc) == set(drivers), set(desc) ^ set(drivers)
for k, d in drivers.items():
    desc[k]["drivers_up"], desc[k]["drivers_down"], desc[k]["updated"] = d["up"], d["down"], d.get("updated", UPDATED)
html = html[: m.start(2)] + json.dumps(desc, ensure_ascii=False, indent=2) + html[m.end(2):]

INDEX.write_text(html, encoding="utf-8")

sw = SW.read_text()
mm = re.search(r"const CACHE_NAME = 'daily-brief-v(\d+)';", sw)
new = int(mm.group(1)) + 1
SW.write_text(sw.replace(mm.group(0), f"const CACHE_NAME = 'daily-brief-v{new}';"), encoding="utf-8")

check = INDEX.read_text(encoding="utf-8")
for sid in ("embedded-markets", "market-descriptions", "breaking-stories"):
    json.loads(re.search(rf'<script id="{sid}"[^>]*>(.*?)</script>', check, re.DOTALL).group(1))
print(f"OK: {DATE} {EDITION} inserted at {TIME}; sw -> v{new}; JSON blocks parse")
