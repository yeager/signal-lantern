#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOMAIN="signal-lantern"
POT="$ROOT/locale/$DOMAIN.pot"
PO_DIR="$ROOT/po"

mkdir -p "$ROOT/locale"

xgettext \
  --from-code=UTF-8 \
  --language=Python \
  --keyword=_ \
  --output="$POT" \
  "$ROOT/src/signallantern/app.py" \
  "$ROOT/src/signallantern/checks.py"

for po in "$PO_DIR"/*.po; do
  [ -e "$po" ] || continue
  msgmerge --update --backup=none "$po" "$POT"
done

echo "Updated $POT and merged translations in $PO_DIR"
