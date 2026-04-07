#!/usr/bin/env python3
"""Copy pulled Transifex PO files into po/, filtering by completion.

Usage:
    python3 scripts/sync-translations.py \
        --source-dir translations \
        --target-dir po \
        --min-completion 20

The script reads each .po file in --source-dir, computes the percentage of
translated (non-fuzzy, non-empty) messages, and only copies files that meet
the --min-completion threshold.  Existing files in --target-dir are
overwritten only when the incoming file differs.
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path


def completion_percent(po_path: Path) -> float:
    """Return the percentage of translated messages in a PO file."""
    text = po_path.read_text(encoding="utf-8")
    # Split into message blocks (separated by blank lines)
    blocks = re.split(r"\n{2,}", text)
    total = 0
    translated = 0
    for block in blocks:
        # Skip header block and comments-only blocks
        if "msgid" not in block or 'msgid ""' in block and "msgid_plural" not in block and block.count("msgid") == 1:
            # Could be the header (msgid "" followed by msgstr with metadata)
            if 'msgid ""' in block and "Project-Id-Version" in block:
                continue
        if "msgid" not in block:
            continue
        total += 1
        # A message is translated if msgstr is non-empty and not fuzzy
        if "#, fuzzy" in block:
            continue
        # Extract msgstr value(s)
        msgstr_match = re.findall(r'msgstr(?:\[\d+\])?\s+"((?:[^"\\]|\\.)*)"', block)
        if msgstr_match and any(s for s in msgstr_match):
            translated += 1
    return (translated / total * 100) if total > 0 else 0.0


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync PO translations above a completion threshold")
    parser.add_argument("--source-dir", type=Path, default=Path("translations"))
    parser.add_argument("--target-dir", type=Path, default=Path("po"))
    parser.add_argument("--min-completion", type=int, default=20)
    args = parser.parse_args()

    if not args.source_dir.is_dir():
        print(f"Source directory {args.source_dir} does not exist, nothing to sync.")
        return 0

    args.target_dir.mkdir(parents=True, exist_ok=True)

    copied = 0
    skipped = 0
    for po_file in sorted(args.source_dir.glob("*.po")):
        pct = completion_percent(po_file)
        lang = po_file.stem
        if pct < args.min_completion:
            print(f"  skip {lang}: {pct:.0f}% < {args.min_completion}% threshold")
            skipped += 1
            continue
        dest = args.target_dir / po_file.name
        # Only overwrite if content actually changed
        if dest.exists() and dest.read_bytes() == po_file.read_bytes():
            print(f"  unchanged {lang}: {pct:.0f}%")
            continue
        shutil.copy2(po_file, dest)
        print(f"  copied {lang}: {pct:.0f}%")
        copied += 1

    print(f"\nDone: {copied} copied, {skipped} skipped (below {args.min_completion}% threshold)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
