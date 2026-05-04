#!/usr/bin/env bash
# install-hooks.sh — wire repo's git hooks into .git/hooks
#
# Run after a fresh clone to enable the pre-commit validator.
# Idempotent: safe to run multiple times.
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
HOOK_SRC="$REPO_ROOT/scripts/git-hooks"
HOOK_DST="$REPO_ROOT/.git/hooks"

if [[ ! -d "$HOOK_SRC" ]]; then
    echo "✗ Source hooks directory not found: $HOOK_SRC"
    exit 1
fi

mkdir -p "$HOOK_DST"

for hook in "$HOOK_SRC"/*; do
    name="$(basename "$hook")"
    cp "$hook" "$HOOK_DST/$name"
    chmod +x "$HOOK_DST/$name"
    echo "✓ Installed $name"
done

echo ""
echo "Done. Hooks are active for this clone."
echo "Bypass in genuine emergencies with: git commit --no-verify"
