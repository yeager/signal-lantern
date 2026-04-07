# Signal Lantern architecture note

## Design goals

Signal Lantern is built to be calm, readable, and honest. Beginners should get a short explanation plus practical next steps. Advanced users should be able to inspect the raw signals behind the advice without switching tools.

## Prototype architecture

### 1. Health engine
`src/signallantern/checks.py`

- Pulls low-level Linux state from `ip`, `nmcli`, `ping`, `/proc/*`, `df`, and resolver lookups.
- Normalizes that data into a raw state dictionary.
- Maps raw signals to issue cards with severity, plain-language guidance, technical details, and optional desktop actions.

### 2. Shared data model
`src/signallantern/models.py`

- `Issue` carries user-visible diagnosis data plus optional action and notification copy.
- `Snapshot` groups issues, timestamp, quick metrics, and raw probe state for the current cycle.

### 3. UI layer
`src/signallantern/app.py`

- `Adw.Application` owns the polling loop and notification throttling.
- `SignalLanternWindow` renders:
  - top summary card
  - central issue cards
  - right-side health strip and about panel
- Each issue card keeps beginner text first, then hides technical details inside an expander.

### 4. Localization layer
`src/signallantern/i18n.py`, `po/sv.po`

- Source strings stay English.
- Runtime translation currently uses a lightweight in-process catalog so the app can ship working Swedish immediately.
- A `po/` catalog is included so the next step can move to compiled gettext catalogs without restructuring the app.

## Important tradeoffs

- Python + PyGObject was chosen for speed and Linux-native behavior, not peak performance.
- The app favors safe read-only diagnostics. It suggests fixes and opens desktop tools, but it does not run privileged repair actions itself.
- Some signals are best-effort. For example, ICMP-blocked gateways and unusual resolver setups can produce noisy results.

## Good next steps

1. Replace the in-app translation map with real gettext `.mo` loading.
2. Add richer system-details history and incident retention.
3. Detect captive portal, packet loss, and low-battery conditions.
4. Add Flatpak or Debian packaging proper.
5. Add integration tests around the rules layer using mocked probe outputs.
