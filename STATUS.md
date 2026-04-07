# Signal Lantern prototype status

## Built in this pass

- GTK 4 + libadwaita Python application shell
- Health engine with live probes for network, Wi-Fi, gateway, DNS, CPU, memory, disk, reboot state, power, and storage edge cases
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
- Summary card: explicit “changes since last check” text block so updates are readable without relying on toast timing or color.
- Issue cards: accessible label (severity + title) and description (meaning).
- Issue cards: explicit severity text shown in each card, not just icon + color.
- Severity icons: tooltip text with severity name for screen readers.
- Check button: tooltip describing the action.
- Copy diagnostics button: descriptive tooltip.
- Technical details expander: tooltip for discoverability.
- Detail labels inside expanders: selectable for keyboard users without becoming separate focus stops.
- System detail rows (ActionRow): accessible label includes both metric name and current value, updated on each refresh.
- Issue list container: accessible label for screen reader context.
- Keyboard pass: removed focus from summary/issue containers, added app-level shortcuts (`Ctrl+R`, `Ctrl+Shift+C`), and documented the intended keyboard path.
- Screen-reader pass: summary and issue list now expose clearer accessible descriptions, and material status changes are announced without stealing focus.
- High-contrast pass: severity and change state now have plain-text labels so the UI remains understandable even when colors/icons are hard to parse.

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
- Added low-battery detection for laptops running on battery power.
- Added read-only root filesystem detection.
- Added `/boot` almost-full detection so update failures are easier to explain.
- Added rolling public-DNS latency sampling to detect both slow internet response and unstable jitter.
- Added audio diagnostics for sound-service failure, missing playback/recording devices, muted output, and muted microphone states.
- All new checks include plain-language guidance aimed at non-technical users.

## Gettext pipeline (2026-04-07)

- Replaced the temporary runtime translation map with a gettext-based loader.
- Added `scripts/update-translations.sh` to extract source strings and merge `po/*.po`.
- Added `scripts/compile-translations.sh` to build `.mo` catalogs from `po/*.po`.
- Updated run/package scripts to compile and bundle locale files when gettext tools are available.

## Native packaging (2026-04-07)

- Added Debian packaging under `debian/` using debhelper + pybuild.
- Added RPM packaging under `packaging/signal-lantern.spec`.
- Added helper scripts for DEB and RPM builds.
- Package installs the app entry point, desktop file, icon, and compiled locale files.

## Desktop integration (2026-04-07)

- Added a simple autostart toggle in the app.
- Added a “changed since last check” summary so users can see what is new or resolved.

## Remaining gaps

- No tray/background service integration yet.
- No historical charting or incident log persistence yet.
- No Flatpak manifest yet.
- Native DEB/RPM packaging exists, but it still needs real Linux install testing before calling it production-ready.
- Network checks are intentionally conservative and may need tuning on real Linux hardware.
