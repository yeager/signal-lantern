#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="$ROOT/dist/signal-lantern-appdir"
TAR="$ROOT/dist/signal-lantern-appdir.tar.gz"

mkdir -p "$ROOT/dist"
rm -rf "$OUT"
mkdir -p "$OUT/usr/bin" "$OUT/usr/share/applications" "$OUT/usr/share/icons/hicolor/scalable/apps" "$OUT/usr/share/locale"

if command -v msgfmt >/dev/null 2>&1; then
  "$ROOT/scripts/compile-translations.sh"
fi

cp "$ROOT/scripts/run.sh" "$OUT/usr/bin/signal-lantern"
cp -R "$ROOT/src" "$OUT/usr/"
cp "$ROOT/data/io.github.signallantern.desktop" "$OUT/usr/share/applications/"
cp "$ROOT/data/io.github.signallantern.svg" "$OUT/usr/share/icons/hicolor/scalable/apps/"
if [ -d "$ROOT/locale" ]; then
  cp -R "$ROOT/locale"/* "$OUT/usr/share/locale/" 2>/dev/null || true
fi

tar -czf "$TAR" -C "$ROOT/dist" "signal-lantern-appdir"
echo "Created $TAR"
