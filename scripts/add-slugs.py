#!/usr/bin/env python3
"""Add data-slug attributes to every curated-item in index.html.

The slug is derived from the h4 text: lowercase, alphanumeric only,
hyphen-separated, first 6 significant words. Idempotent — if a
curated-item already has data-slug, it is preserved.

Run from repo root: python3 scripts/add-slugs.py
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "index.html"

STOPWORDS = {
    "a", "an", "the", "of", "to", "and", "or", "but", "in", "on", "at",
    "for", "with", "by", "from", "as", "is", "was", "are", "were", "be",
    "been", "has", "have", "had", "this", "that", "those", "these",
    "into", "over", "under", "than", "then", "so", "such", "no", "not",
}


def slugify(text: str, max_words: int = 6) -> str:
    """Convert headline text to a URL-safe slug."""
    # Strip HTML entities and tags
    text = re.sub(r"&[a-zA-Z]+;", " ", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&#\d+;", " ", text)
    # Lowercase and keep only alphanumerics + spaces
    text = re.sub(r"[^a-zA-Z0-9\s]", " ", text.lower())
    words = [w for w in text.split() if w and w not in STOPWORDS]
    return "-".join(words[:max_words])


def add_slugs(html: str) -> tuple[str, int, int]:
    """Walk every <div class="curated-item ..."> and add data-slug from its h4 text.

    Returns (new_html, added_count, skipped_count).
    """
    added = 0
    skipped = 0
    out_parts: list[str] = []
    cursor = 0

    # Match opening tag of a curated-item (handles class with extra modifiers)
    pattern = re.compile(
        r'(<div\s+class="(?:[^"]*\s)?curated-item(?:\s[^"]*)?"[^>]*?)(>)',
        flags=re.IGNORECASE,
    )

    for m in pattern.finditer(html):
        tag_start = m.start()
        tag_open = m.group(1)
        tag_close = m.group(2)
        tag_end = m.end()

        out_parts.append(html[cursor:tag_start])

        # Skip if already has data-slug
        if re.search(r'\bdata-slug\s*=', tag_open, flags=re.IGNORECASE):
            out_parts.append(html[tag_start:tag_end])
            skipped += 1
            cursor = tag_end
            continue

        # Find the next </div> that closes this curated-item
        # Use bracket counting because curated-items may contain nested divs
        depth = 1
        scan = tag_end
        item_end = -1
        nested_re = re.compile(r"<div\b|</div>", flags=re.IGNORECASE)
        for nm in nested_re.finditer(html, scan):
            token = nm.group(0).lower()
            if token == "</div>":
                depth -= 1
                if depth == 0:
                    item_end = nm.end()
                    break
            else:
                depth += 1
        if item_end < 0:
            # Unbalanced; bail out
            out_parts.append(html[tag_start:tag_end])
            skipped += 1
            cursor = tag_end
            continue

        item_html = html[tag_end:item_end]
        h4_match = re.search(
            r"<h4[^>]*>(.*?)</h4>", item_html, flags=re.IGNORECASE | re.DOTALL
        )
        if not h4_match:
            out_parts.append(html[tag_start:tag_end])
            skipped += 1
            cursor = tag_end
            continue

        slug = slugify(h4_match.group(1))
        if not slug:
            out_parts.append(html[tag_start:tag_end])
            skipped += 1
            cursor = tag_end
            continue

        # Insert data-slug just before the closing >
        new_tag = tag_open + f' data-slug="{slug}"' + tag_close
        out_parts.append(new_tag)
        added += 1
        cursor = tag_end

    out_parts.append(html[cursor:])
    return "".join(out_parts), added, skipped


def main() -> int:
    if not INDEX.exists():
        print(f"index.html not found at {INDEX}", file=sys.stderr)
        return 1
    html = INDEX.read_text(encoding="utf-8")
    new_html, added, skipped = add_slugs(html)
    INDEX.write_text(new_html, encoding="utf-8")
    print(f"data-slug added to {added} curated-items, skipped {skipped} pre-existing")
    return 0


if __name__ == "__main__":
    sys.exit(main())
