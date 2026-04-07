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

- Summary card: accessible label updated dynamically with status and issue count.
- Issue cards: accessible label (severity + title) and description (meaning).
- Severity icons: tooltip text with severity name for screen readers.
- Check button: tooltip describing the action.
- Copy diagnostics button: descriptive tooltip.
- Technical details expander: tooltip for discoverability.
- Detail labels inside expanders: selectable for keyboard users without becoming separate focus stops.
- System detail rows (ActionRow): accessible label includes both metric name and current value, updated on each refresh.
- Issue list container: accessible label for screen reader context.
- Keyboard pass: removed focus from summary/issue containers, added app-level shortcuts (`Ctrl+R`, `Ctrl+Shift+C`), and documented the intended keyboard path.
- Screen-reader pass: summary and issue list now expose clearer accessible descriptions, and material status changes are announced without stealing focus.

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

## Diagnostics expansion (2026-04-07)

- Added captive portal detection for sign-in-required networks.
- Added detection for Wi-Fi turned off in software.
- Added detection for Wi-Fi hardware blocked states.
- Added a conservative warning for likely missing Wi-Fi adapter / driver situations.
- Added reboot-required detection using standard Linux reboot markers.
- All new checks include plain-language guidance aimed at non-technical users.

## Remaining gaps

- No real gettext `.mo` compilation yet, just an i18n-ready bridge plus `po/sv.po`.
- No tray/background service integration yet.
- No historical charting or incident log persistence yet.
- No formal Debian package or Flatpak manifest yet.
- Network checks are intentionally conservative and may need tuning on real Linux hardware.
