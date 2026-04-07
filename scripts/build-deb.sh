#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
./scripts/update-translations.sh
./scripts/compile-translations.sh
dpkg-buildpackage -us -uc -b
