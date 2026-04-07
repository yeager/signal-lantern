#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SPEC="$ROOT/packaging/signal-lantern.spec"
VERSION="$(python3 - <<'PY'
from pathlib import Path
import tomllib
with Path('pyproject.toml').open('rb') as f:
    data = tomllib.load(f)
print(data['project']['version'])
PY
)"
NAME="signal-lantern"
TOPDIR="${HOME}/rpmbuild"
SOURCEDIR="$TOPDIR/SOURCES/${NAME}-${VERSION}"
TARBALL="$TOPDIR/SOURCES/${NAME}-${VERSION}.tar.gz"

mkdir -p "$TOPDIR"/{BUILD,BUILDROOT,RPMS,SOURCES,SPECS,SRPMS}
rm -rf "$SOURCEDIR"
mkdir -p "$SOURCEDIR"

rsync -a --delete \
  --exclude '.git' \
  --exclude 'dist' \
  --exclude '.venv' \
  --exclude '__pycache__' \
  "$ROOT/" "$SOURCEDIR/"

( cd "$TOPDIR/SOURCES" && tar -czf "$TARBALL" "${NAME}-${VERSION}" )
cp "$SPEC" "$TOPDIR/SPECS/"
rpmbuild -ba "$TOPDIR/SPECS/$(basename "$SPEC")"
