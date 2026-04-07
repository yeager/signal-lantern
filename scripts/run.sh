#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if command -v msgfmt >/dev/null 2>&1; then
  "$ROOT/scripts/compile-translations.sh" >/dev/null 2>&1 || true
fi
export SIGNAL_LANTERN_LOCALE_DIR="$ROOT/locale"
export PYTHONPATH="$ROOT/src:${PYTHONPATH:-}"
exec python3 -m signallantern "$@"
