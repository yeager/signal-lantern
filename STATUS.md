# Signal Lantern prototype status

## Built in this pass

- GTK 4 + libadwaita Python application shell
- Health engine with live probes for network, Wi-Fi, gateway, DNS, CPU, memory, and disk
- Issue cards with beginner guidance and expandable technical details
- Desktop notifications with duplicate suppression by issue state
- English-first strings with Swedish translations included
- Desktop launcher metadata with Swedish localization
- Custom SVG icon
- README, architecture note, and basic packaging/launch scripts

## Practical status

- The source tree is usable as a first prototype.
- The diagnostics engine can run headless for smoke testing.
- GUI launch depends on Linux packages that are not present in this macOS workspace.

## Accessibility pass (2026-04-07)

- Summary card: focusable, accessible label updated dynamically with status and issue count.
- Issue cards: focusable, accessible label (severity + title) and description (meaning).
- Severity icons: tooltip text with severity name for screen readers.
- Check button: tooltip describing the action.
- Copy diagnostics button: descriptive tooltip.
- Technical details expander: tooltip for discoverability.
- Detail labels inside expanders: focusable + selectable for keyboard users.
- System detail rows (ActionRow): accessible label includes both metric name and current value, updated on each refresh.
- Issue list container: accessible label for screen reader context.

## CI pipeline (2026-04-07)

- GitHub Actions workflow for Transifex source push (on POT file changes to main).
- GitHub Actions workflow for weekly translation pull with configurable completion threshold (default 20%).
- Translations pulled into a PR for review, never merged automatically.
- Helper script (`scripts/sync-translations.py`) filters PO files by completion percentage.
- Required secret: `TX_TOKEN` (Transifex API v3 token).

## Secret scanning (2026-04-07)

- Added `.gitleaks.toml` for repo-local scan rules.
- Added `.github/workflows/secret-scan.yml` to scan pushes, PRs, and manual runs.
- Added local `.githooks/pre-commit` and `.githooks/pre-push` hooks using gitleaks.
- Added `scripts/install-git-hooks.sh` to activate repo-local hooks with `core.hooksPath`.

## Remaining gaps

- No real gettext `.mo` compilation yet, just an i18n-ready bridge plus `po/sv.po`.
- No tray/background service integration yet.
- No historical charting or incident log persistence yet.
- No formal Debian package or Flatpak manifest yet.
- Network checks are intentionally conservative and may need tuning on real Linux hardware.
