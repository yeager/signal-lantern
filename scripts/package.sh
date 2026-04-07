#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST="$ROOT/dist"
APPDIR="$DIST/signal-lantern-appdir"
rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/share/applications" "$APPDIR/usr/share/icons/hicolor/scalable/apps" "$APPDIR/usr/bin"
cp "$ROOT/data/io.github.signallantern.desktop" "$APPDIR/usr/share/applications/"
cp "$ROOT/data/io.github.signallantern.svg" "$APPDIR/usr/share/icons/hicolor/scalable/apps/io.github.signallantern.svg"
cp "$ROOT/scripts/run.sh" "$APPDIR/usr/bin/signal-lantern"
chmod +x "$APPDIR/usr/bin/signal-lantern"
python3 -m build "$ROOT" >/dev/null 2>&1 || true
tar -C "$DIST" -czf "$DIST/signal-lantern-appdir.tar.gz" signal-lantern-appdir
printf 'Created %s\n' "$DIST/signal-lantern-appdir.tar.gz"
