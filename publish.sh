#!/usr/bin/env bash
# Build vault.dconn.dev. Boundary = ~/Obsidian/.export-ignore (folders) + frontmatter/inline #private.
set -euo pipefail
SITE="/home/dev/vault-site"; VAULT="/home/dev/Obsidian"; WWW="/var/www/vault.dconn.dev"
STAGING="$SITE/staging"; EXPORT="$SITE/export"; OE="$HOME/.cargo/bin/obsidian-export"; HUGO="/usr/local/bin/hugo"
SKIPLIST="$SITE/skip-notes.txt"
cd "$SITE"

# 0. hardlink mirror; normalize frontmatter (vault never modified)
rm -rf "$STAGING"; cp -alT "$VAULT" "$STAGING"
python3 "$SITE/frontmatter-normalize.py" "$STAGING"

# pre-remove notes already known to be unparseable (fast path)
if [ -f "$SKIPLIST" ]; then while IFS= read -r rel; do [ -n "$rel" ] && rm -f "$STAGING/$rel"; done < "$SKIPLIST"; fi

# 1. export, self-healing: drop any note obsidian-export still can't parse and remember it
rm -rf "$EXPORT"; mkdir -p "$EXPORT"; rm -rf "$SITE/content"/* "$SITE/static"/*
for _ in $(seq 1 80); do
  if "$OE" "$STAGING" "$EXPORT" 2> "$SITE/export.log"; then break; fi
  bad=$(grep -oP "(?:Failed to export|frontmatter in) '\K[^']+\.md" "$SITE/export.log" | head -1 || true)
  if [ -n "$bad" ] && [ -f "$bad" ]; then
    rel="${bad#$STAGING/}"; echo "  skip unparseable: $rel"; echo "$rel" >> "$SKIPLIST"
    rm -f "$bad"; rm -rf "$EXPORT"; mkdir -p "$EXPORT"
  else echo "EXPORT FAILED:"; tail -5 "$SITE/export.log"; exit 1; fi
done

# 2. per-note override: drop notes carrying an inline #private tag
grep -rlZ --include='*.md' '#private' "$EXPORT" 2>/dev/null | xargs -0 -r rm -f || true

# 3. split: markdown -> content/, attachments -> static/
rsync -a --prune-empty-dirs --include='*/' --include='*.md' --exclude='*' "$EXPORT/" "$SITE/content/"
rsync -a --prune-empty-dirs --exclude='*.md' "$EXPORT/" "$SITE/static/"
python3 "$SITE/fix-callouts.py" "$SITE/content"
python3 "$SITE/make-sections.py" "$SITE/content"

# 4. build + deploy
"$HUGO" --minify --cleanDestinationDir --destination "$SITE/public"
rsync -a --delete "$SITE/public/" "$WWW/"
echo "PUBLISHED: $(find "$WWW" -name '*.html' | wc -l) html pages, $(du -sh "$WWW" | cut -f1); skiplist=$([ -f "$SKIPLIST" ] && wc -l < "$SKIPLIST" | tr -d " " || echo 0)"
