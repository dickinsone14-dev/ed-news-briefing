#!/usr/bin/env python3
"""Remove all curated-editions for a given data-date from index.html.
Usage: python3 prune_edition.py YYYY-MM-DD [--apply]
Deletes from each edition's opening HTML comment through its matching END comment.
Prints a summary only; never dumps edition content.
"""
import re, sys
from pathlib import Path
DATE = sys.argv[1]
APPLY = "--apply" in sys.argv
P = Path("/Users/ed/ed-news-briefing/index.html")
h = P.read_text(encoding="utf-8")
orig_len = len(h)

removed = []
while True:
    m = re.search(rf'<div class="curated-edition (morning|evening)" data-date="{re.escape(DATE)}"', h)
    if not m:
        break
    ed = m.group(1).upper()
    div_start = m.start()
    # opening comment immediately before the div
    pc = h.rfind('<!--', 0, div_start)
    assert pc != -1
    open_comment = h[pc:h.find('-->', pc) + 3]
    # the opening comment must belong to THIS edition, not be the previous edition's END
    start = pc if ('END' not in open_comment) else div_start
    # matching END comment for this edition
    em = re.search(rf'<!-- ── END {ed} [^-]*? ── -->', h[div_start:])
    assert em, f"no END comment found for {DATE} {ed}"
    end = div_start + em.end()
    # swallow trailing newlines
    while end < len(h) and h[end] == '\n':
        end += 1
    removed.append((ed, end - start))
    h = h[:start] + h[end:]

print(f"{DATE}: removed {len(removed)} edition(s)")
for ed, n in removed:
    print(f"  {ed}: {n:,} bytes")
print(f"index.html {orig_len:,} -> {len(h):,} bytes ({orig_len-len(h):,} removed)")
needle = 'data-date="' + DATE + '"'
print("remaining " + needle + " occurrences:", h.count(needle))
if APPLY:
    P.write_text(h, encoding="utf-8")
    print("WRITTEN")
else:
    print("(dry run — pass --apply to write)")
