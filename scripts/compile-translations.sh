#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PO_DIR="$ROOT/po"
LOCALE_DIR="$ROOT/locale"
DOMAIN="signal-lantern"

mkdir -p "$LOCALE_DIR"

if ! command -v msgfmt >/dev/null 2>&1; then
  echo "msgfmt not found. Install gettext to compile translations." >&2
  exit 1
fi

for po in "$PO_DIR"/*.po; do
  [ -e "$po" ] || continue
  lang="$(basename "$po" .po)"
  target="$LOCALE_DIR/$lang/LC_MESSAGES"
  mkdir -p "$target"
  msgfmt "$po" -o "$target/$DOMAIN.mo"
  echo "Compiled $po -> $target/$DOMAIN.mo"
done
