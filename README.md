# Signal Lantern

Signal Lantern is a GTK 4 + libadwaita prototype for Linux desktops that watches common network and system problems, explains them in plain English, and still exposes useful technical detail when you want it.

## What the prototype includes

- GTK 4 + libadwaita desktop app shell
- Beginner-first issue cards with expandable technical details
- Periodic background checks for:
  - no network connection
  - weak Wi-Fi signal, when NetworkManager exposes signal data
  - default gateway unreachable
  - slow DNS
  - failing DNS
  - high CPU load
  - low available memory
  - low disk space
- Desktop notifications on issue appearance or severity change
- English source strings with Swedish localization scaffolding and content
- Localized `.desktop` entry metadata in Swedish
- Unique SVG app icon
- Copy-diagnostics action for advanced troubleshooting
- First-pass accessibility improvements for screen readers and keyboard users
- Simple launch and packaging scripts

## Project layout

- `src/signallantern/app.py` GTK application and UI
- `src/signallantern/checks.py` health engine and Linux probes
- `src/signallantern/models.py` issue/snapshot data model
- `src/signallantern/i18n.py` lightweight runtime translation layer
- `data/io.github.signallantern.desktop` desktop launcher
- `data/io.github.signallantern.svg` app icon
- `po/sv.po` Swedish gettext-style catalog starter
- `scripts/run.sh` local launch helper
- `scripts/package.sh` simple source/appdir packaging helper
- `.github/workflows/transifex-sync.yml` GitHub Actions workflow for source push + translation pull
- `scripts/sync-translations.py` completion-gated sync helper for pulled PO files

## Runtime dependencies

On Ubuntu or Debian:

```bash
sudo apt install python3 python3-gi python3-gi-cairo gir1.2-gtk-4.0 gir1.2-adw-1 network-manager iproute2 iputils-ping
```

Optional helpers for action buttons:

```bash
sudo apt install gnome-control-center gnome-system-monitor baobab
```

## Run locally from source

```bash
cd /Users/bosse/.openclaw/workspace-main/projects/signal-lantern
chmod +x scripts/run.sh
./scripts/run.sh
```

Or with Python directly:

```bash
PYTHONPATH=src python3 -m signallantern
```

## Test the code without GTK

Syntax/import smoke test:

```bash
cd /Users/bosse/.openclaw/workspace-main/projects/signal-lantern
PYTHONPATH=src python3 -m compileall src
PYTHONPATH=src python3 - <<'PY'
from signallantern.checks import HealthEngine
snapshot = HealthEngine().collect()
print(snapshot.status_line)
print(snapshot.metrics)
print([issue.key for issue in snapshot.issues])
PY
```

## Desktop integration

Install the desktop entry and icon for one user:

```bash
mkdir -p ~/.local/share/applications ~/.local/share/icons/hicolor/scalable/apps
cp data/io.github.signallantern.desktop ~/.local/share/applications/
cp data/io.github.signallantern.svg ~/.local/share/icons/hicolor/scalable/apps/
update-desktop-database ~/.local/share/applications 2>/dev/null || true
gtk-update-icon-cache ~/.local/share/icons/hicolor 2>/dev/null || true
```

If you do not install the console script, adjust `Exec=` in the desktop file to point at `scripts/run.sh`.

## Simple packaging helper

```bash
chmod +x scripts/package.sh
./scripts/package.sh
```

This creates `dist/signal-lantern-appdir.tar.gz`, a lightweight appdir-style bundle containing the launcher, icon, and desktop file. It is not a polished Debian package yet, but it gives you a clean handoff artifact.

## Accessibility

The current UI now includes a first-pass a11y layer:

- focusable summary and issue cards
- accessible labels for the summary, issue list, and system detail rows
- clearer button and expander tooltips for assistive tech
- selectable technical detail rows for keyboard users

This is a pragmatic first pass, not a full accessibility audit.

## Transifex sync CI

The repository includes `.github/workflows/transifex-sync.yml`.

- pushes source updates to Transifex when `locale/signal-lantern.pot` changes on `main`
- pulls translations on a weekly schedule or manual dispatch
- only syncs languages meeting the minimum completion threshold, default `20%`
- opens a pull request instead of merging translation updates automatically

Required GitHub secret:

- `TX_TOKEN`, a Transifex API v3 token with access to the project

## Notes and limits

- Wi-Fi quality depends on NetworkManager or `nmcli` exposing signal information.
- DNS timing currently uses a real lookup of `example.com` via the system resolver.
- Gateway reachability uses `ping`, so environments that block ICMP may report false positives.
- The app is i18n-ready in structure, but the runtime still uses an in-app translation map instead of compiled gettext catalogs.
- Tray support is intentionally skipped in this first prototype because modern GTK 4 desktops do not offer a consistent cross-desktop tray API.
