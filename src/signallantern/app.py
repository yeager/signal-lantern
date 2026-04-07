from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import traceback

from .checks import HealthEngine
from .i18n import get_i18n

APP_ID = "io.github.signallantern"
POLL_SECONDS = 30

try:
    import gi

    gi.require_version("Gtk", "4.0")
    gi.require_version("Adw", "1")
    gi.require_version("Gio", "2.0")
    from gi.repository import Adw, Gio, GLib, Gtk
except Exception:  # pragma: no cover
    gi = None
    Adw = Gio = GLib = Gtk = None


if gi is not None:
    from .models import Issue, Severity, Snapshot

    class SignalLanternApplication(Adw.Application):
        def __init__(self) -> None:
            super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.HANDLES_OPEN)
            self.i18n = get_i18n()
            self._ = self.i18n.gettext
            self.engine = HealthEngine()
            self.window: SignalLanternWindow | None = None
            self.snapshot: Snapshot | None = None
            self.notification_state: dict[str, str] = {}
            self.last_status_signature: tuple[str, tuple[str, ...]] | None = None
            self.last_change_summary: dict[str, list[str]] = {"new": [], "resolved": []}

            check_action = Gio.SimpleAction.new("check-now", None)
            check_action.connect("activate", self.on_check_now)
            self.add_action(check_action)

            copy_action = Gio.SimpleAction.new("copy-diagnostics", None)
            copy_action.connect("activate", self.on_copy_diagnostics)
            self.add_action(copy_action)

            enable_autostart_action = Gio.SimpleAction.new("enable-autostart", None)
            enable_autostart_action.connect("activate", self.on_enable_autostart)
            self.add_action(enable_autostart_action)

            disable_autostart_action = Gio.SimpleAction.new("disable-autostart", None)
            disable_autostart_action.connect("activate", self.on_disable_autostart)
            self.add_action(disable_autostart_action)

            self.set_accels_for_action("app.check-now", ["<Primary>r"])
            self.set_accels_for_action("app.copy-diagnostics", ["<Primary><Shift>c"])

        def do_activate(self) -> None:
            if self.window is None:
                self.window = SignalLanternWindow(self)
            self.window.present()
            if self.snapshot is None:
                self.refresh()
                GLib.timeout_add_seconds(POLL_SECONDS, self._on_timeout)

        def _on_timeout(self) -> bool:
            self.refresh()
            return True

        def on_check_now(self, *_args) -> None:
            self.refresh()

        def on_copy_diagnostics(self, *_args) -> None:
            if not self.snapshot or not self.window:
                return
            payload = {
                "checked_at": self.snapshot.checked_at,
                "status_line": self.snapshot.status_line,
                "metrics": self.snapshot.metrics,
                "issues": [
                    {
                        "key": issue.key,
                        "severity": issue.severity.value,
                        "title": issue.title,
                        "details": issue.details,
                    }
                    for issue in self.snapshot.issues
                ],
                "raw": self.snapshot.raw,
            }
            clipboard = self.window.get_clipboard()
            clipboard.set(json.dumps(payload, indent=2, ensure_ascii=False))
            self.window.show_toast(self._("Diagnostics copied to the clipboard."))

        def on_enable_autostart(self, *_args) -> None:
            target = self._autostart_path()
            target.parent.mkdir(parents=True, exist_ok=True)
            source = Path(__file__).resolve().parents[2] / "data" / "io.github.signallantern.desktop"
            text = source.read_text(encoding="utf-8")
            if "X-GNOME-Autostart-enabled" not in text:
                text += "\nX-GNOME-Autostart-enabled=true\n"
            target.write_text(text, encoding="utf-8")
            if self.window:
                self.window.refresh_autostart_state()
                self.window.show_toast(self._("Autostart enabled."))

        def on_disable_autostart(self, *_args) -> None:
            target = self._autostart_path()
            if target.exists():
                target.unlink()
            if self.window:
                self.window.refresh_autostart_state()
                self.window.show_toast(self._("Autostart disabled."))

        def _autostart_path(self) -> Path:
            return Path(GLib.get_user_config_dir()) / "autostart" / "io.github.signallantern.desktop"

        def autostart_enabled(self) -> bool:
            return self._autostart_path().exists()

        def refresh(self) -> None:
            previous_snapshot = self.snapshot
            snapshot = self.engine.collect()
            self.snapshot = snapshot
            self.last_change_summary = self._summarize_changes(previous_snapshot, snapshot)
            self._announce_status_change(snapshot)
            if self.window:
                self.window.update_snapshot(snapshot, self.last_change_summary)
            self._notify(snapshot)

        def _announce_status_change(self, snapshot: Snapshot) -> None:
            status_signature = (
                snapshot.status_line,
                tuple(issue.key for issue in snapshot.issues),
            )
            if self.last_status_signature is None:
                self.last_status_signature = status_signature
                return
            if self.last_status_signature == status_signature:
                return
            if self.window:
                parts = []
                if self.last_change_summary["new"]:
                    parts.append(self._("New issues") + f": {len(self.last_change_summary['new'])}")
                if self.last_change_summary["resolved"]:
                    parts.append(self._("Resolved issues") + f": {len(self.last_change_summary['resolved'])}")
                toast = self._(snapshot.status_line)
                if parts:
                    toast += " • " + ", ".join(parts)
                self.window.show_toast(toast)
            self.last_status_signature = status_signature

        def _summarize_changes(
            self,
            previous_snapshot: Snapshot | None,
            snapshot: Snapshot,
        ) -> dict[str, list[str]]:
            if previous_snapshot is None:
                return {"new": [], "resolved": []}
            previous = {issue.key: self._(issue.title) for issue in previous_snapshot.issues}
            current = {issue.key: self._(issue.title) for issue in snapshot.issues}
            return {
                "new": [current[key] for key in current.keys() - previous.keys()],
                "resolved": [previous[key] for key in previous.keys() - current.keys()],
            }

        def _notify(self, snapshot: Snapshot) -> None:
            active_keys = {issue.key for issue in snapshot.issues}
            for stale_key in list(self.notification_state):
                if stale_key not in active_keys:
                    del self.notification_state[stale_key]

            for issue in snapshot.issues:
                state = f"{issue.severity.value}:{issue.meaning}"
                if self.notification_state.get(issue.key) == state:
                    continue
                notification = Gio.Notification.new(f"Signal Lantern: {self._(issue.title)}")
                notification.set_body(self._(issue.notification_body or issue.meaning))
                notification.set_priority(
                    Gio.NotificationPriority.URGENT if issue.severity == Severity.CRITICAL else Gio.NotificationPriority.NORMAL
                )
                notification.set_default_action("app.activate")
                self.send_notification(issue.key, notification)
                self.notification_state[issue.key] = state

    class SignalLanternWindow(Adw.ApplicationWindow):
        def __init__(self, app: SignalLanternApplication) -> None:
            super().__init__(application=app, title=app._("Signal Lantern"), default_width=1080, default_height=760)
            self.app = app
            self._ = app._
            self.toast_overlay = Adw.ToastOverlay()
            self.set_content(self.toast_overlay)

            header = Adw.HeaderBar()
            check_button = Gtk.Button(label=self._("Check again now"))
            check_button.set_tooltip_text(self._("Run all health checks immediately"))
            check_button.set_can_focus(True)
            check_button.set_receives_default(True)
            check_button.connect("clicked", lambda *_: self.app.refresh())
            header.pack_end(check_button)

            toolbar = Adw.ToolbarView()
            toolbar.add_top_bar(header)
            self.toast_overlay.set_child(toolbar)

            split = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=18)
            split.set_margin_top(18)
            split.set_margin_bottom(18)
            split.set_margin_start(18)
            split.set_margin_end(18)
            toolbar.set_content(split)

            left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
            left.set_hexpand(True)
            split.append(left)

            self.summary_card = Adw.Bin()
            self.summary_card.add_css_class("card")
            self.summary_card.update_property(
                [Gtk.AccessibleProperty.LABEL, Gtk.AccessibleProperty.DESCRIPTION],
                [self._("System health summary"), self._("Current system health and the most important active problems.")],
            )
            left.append(self.summary_card)
            summary_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
            summary_box.set_margin_top(18)
            summary_box.set_margin_bottom(18)
            summary_box.set_margin_start(18)
            summary_box.set_margin_end(18)
            self.summary_card.set_child(summary_box)

            self.summary_title = Gtk.Label(xalign=0)
            self.summary_title.add_css_class("title-2")
            summary_box.append(self.summary_title)

            self.summary_subtitle = Gtk.Label(xalign=0, wrap=True)
            self.summary_subtitle.add_css_class("dim-label")
            summary_box.append(self.summary_subtitle)

            self.summary_checked = Gtk.Label(xalign=0)
            self.summary_checked.add_css_class("caption")
            summary_box.append(self.summary_checked)

            self.changes_heading = Gtk.Label(xalign=0)
            self.changes_heading.add_css_class("heading")
            self.changes_heading.set_text(self._("Changes since last check"))
            self.changes_heading.set_visible(False)
            summary_box.append(self.changes_heading)

            self.changes_label = Gtk.Label(xalign=0, wrap=True)
            self.changes_label.add_css_class("caption")
            self.changes_label.set_selectable(True)
            self.changes_label.set_visible(False)
            summary_box.append(self.changes_label)

            issues_frame = Adw.PreferencesGroup(
                title=self._("Overview"),
                description=self._("Beginner-friendly issue explanations with advanced details when you want them."),
            )
            left.append(issues_frame)

            self.issue_list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
            self.issue_list.update_property(
                [Gtk.AccessibleProperty.LABEL, Gtk.AccessibleProperty.DESCRIPTION],
                [self._("Active issues"), self._("Problem cards with plain-language explanations and suggested fixes.")],
            )
            issues_frame.add(self.issue_list)

            right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
            right.set_size_request(360, -1)
            split.append(right)

            self.metrics_group = Adw.PreferencesGroup(
                title=self._("System details"),
                description=self._("Quick health strip for advanced users."),
            )
            right.append(self.metrics_group)
            self.metric_rows: dict[str, Adw.ActionRow] = {}
            for key in ["Network", "Wi-Fi", "Gateway", "DNS", "CPU", "Memory", "Disk", "Power"]:
                row = Adw.ActionRow(title=self._(key))
                row.update_property(
                    [Gtk.AccessibleProperty.LABEL],
                    [f"{self._(key)}: {self._('Unknown')}"],
                )
                self.metric_rows[key] = row
                self.metrics_group.add(row)

            about_group = Adw.PreferencesGroup(title=self._("About"))
            right.append(about_group)
            about_group.add(
                Adw.ActionRow(
                    title=self._("Signal Lantern"),
                    subtitle=self._("Explains common network and system problems in plain language"),
                )
            )
            about_group.add(
                Adw.ActionRow(
                    title=self._("Keyboard shortcuts"),
                    subtitle=self._("Ctrl+R checks again, Ctrl+Shift+C copies diagnostics"),
                )
            )
            self.autostart_row = Adw.ActionRow(
                title=self._("Start automatically after login"),
                subtitle="",
            )
            enable_button = Gtk.Button(label=self._("Enable"))
            enable_button.connect("clicked", lambda *_: self.app.on_enable_autostart())
            disable_button = Gtk.Button(label=self._("Disable"))
            disable_button.connect("clicked", lambda *_: self.app.on_disable_autostart())
            self.autostart_row.add_suffix(enable_button)
            self.autostart_row.add_suffix(disable_button)
            about_group.add(self.autostart_row)
            self.refresh_autostart_state()

        def show_toast(self, message: str) -> None:
            self.toast_overlay.add_toast(Adw.Toast.new(message))

        def update_snapshot(self, snapshot: Snapshot, changes: dict[str, list[str]]) -> None:
            if not snapshot.issues:
                summary_text = self._("Everything looks fine")
                self.summary_title.set_text(summary_text)
                self.summary_subtitle.set_text(self._("Signal Lantern will let you know if it spots a network or system problem."))
            else:
                top = snapshot.issues[0]
                summary_text = self._("Critical issue detected") if top.severity == Severity.CRITICAL else self._("Needs attention")
                self.summary_title.set_text(summary_text)
                self.summary_subtitle.set_text(self._(snapshot.status_line))
            checked_text = f"{self._('Last checked')}: {snapshot.checked_at}"
            self.summary_checked.set_text(checked_text)

            # Update the summary card accessible label so screen readers announce changes
            n_issues = len(snapshot.issues)
            issue_count = f"{n_issues} {'issue' if n_issues == 1 else 'issues'}" if n_issues else self._("No active issues")
            self.summary_card.update_property(
                [Gtk.AccessibleProperty.LABEL, Gtk.AccessibleProperty.DESCRIPTION],
                [f"{summary_text}. {issue_count}. {checked_text}", self._(snapshot.status_line)],
            )

            while child := self.issue_list.get_first_child():
                self.issue_list.remove(child)

            if not snapshot.issues:
                self.issue_list.append(
                    Adw.StatusPage(
                        title=self._("No active issues"),
                        description=self._("Your system looks healthy."),
                        icon_name="emblem-ok-symbolic",
                    )
                )
            else:
                for issue in snapshot.issues:
                    self.issue_list.append(self._issue_card(issue, snapshot.checked_at))

            change_lines: list[str] = []
            if changes["new"]:
                change_lines.append(self._("New issues") + ": " + ", ".join(changes["new"][:4]))
            if changes["resolved"]:
                change_lines.append(self._("Resolved issues") + ": " + ", ".join(changes["resolved"][:4]))
            if change_lines:
                self.changes_heading.set_visible(True)
                self.changes_label.set_visible(True)
                self.changes_label.set_text("\n".join(change_lines))
            else:
                self.changes_heading.set_visible(False)
                self.changes_label.set_visible(False)
                self.changes_label.set_text("")

            for key, row in self.metric_rows.items():
                value = self._(snapshot.metrics.get(key, "Unknown"))
                row.set_subtitle(value)
                row.update_property(
                    [Gtk.AccessibleProperty.LABEL],
                    [f"{self._(key)}: {value}"],
                )

        def refresh_autostart_state(self) -> None:
            enabled = self.app.autostart_enabled()
            self.autostart_row.set_subtitle(self._("Enabled") if enabled else self._("Disabled"))

        def _issue_card(self, issue: Issue, checked_at: str) -> Gtk.Widget:
            severity_label = self._severity_label(issue.severity)
            translated_title = self._(issue.title)

            card = Adw.Bin()
            card.add_css_class("card")
            card.update_property(
                [Gtk.AccessibleProperty.LABEL, Gtk.AccessibleProperty.DESCRIPTION],
                [
                    f"{severity_label}: {translated_title}",
                    f"{self._(issue.meaning)} {self._('What you can try')}: {' '.join(self._(suggestion) for suggestion in issue.suggestions[:2])}",
                ],
            )
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
            box.set_margin_top(18)
            box.set_margin_bottom(18)
            box.set_margin_start(18)
            box.set_margin_end(18)
            card.set_child(box)

            title_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            box.append(title_box)
            severity_icon = Gtk.Image.new_from_icon_name(self._severity_icon(issue.severity))
            severity_icon.set_tooltip_text(severity_label)
            title_box.append(severity_icon)

            title = Gtk.Label(xalign=0)
            title.set_hexpand(True)
            title.add_css_class("title-4")
            title.set_text(translated_title)
            title_box.append(title)

            chip = Gtk.Label(label=severity_label)
            chip.add_css_class(self._severity_css(issue.severity))
            chip.add_css_class("pill")
            title_box.append(chip)

            severity_summary = Gtk.Label(xalign=0)
            severity_summary.add_css_class("caption")
            severity_summary.set_text(f"{self._('Severity')}: {severity_label}")
            box.append(severity_summary)

            meaning = Gtk.Label(xalign=0, wrap=True)
            meaning.set_text(self._(issue.meaning))
            box.append(meaning)

            suggestion_heading = Gtk.Label(xalign=0)
            suggestion_heading.add_css_class("heading")
            suggestion_heading.set_text(self._("What you can try"))
            box.append(suggestion_heading)

            suggestions = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            box.append(suggestions)
            for suggestion in issue.suggestions:
                row = Gtk.Label(xalign=0, wrap=True)
                row.set_text(f"• {self._(suggestion)}")
                suggestions.append(row)

            actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            box.append(actions)
            if issue.action:
                action_label = self._(self._action_label(issue.action))
                primary = Gtk.Button(label=action_label)
                primary.set_tooltip_text(action_label)
                primary.set_can_focus(True)
                primary.connect("clicked", self._launch_action, issue.action)
                actions.append(primary)

            copy_button = Gtk.Button(label=self._("Copy diagnostics"))
            copy_button.set_tooltip_text(self._("Copy full diagnostic report to clipboard"))
            copy_button.set_can_focus(True)
            copy_button.connect("clicked", lambda *_: self.app.on_copy_diagnostics())
            actions.append(copy_button)

            expander = Gtk.Expander(label=self._("Show technical details"))
            expander.set_tooltip_text(self._("Show technical details (press Enter or Space)"))
            expander.set_can_focus(True)
            box.append(expander)
            details_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            expander.set_child(details_box)
            for key, value in issue.details.items():
                detail = Gtk.Label(xalign=0, wrap=True)
                detail.set_selectable(True)
                detail.set_text(f"{key}: {value}")
                details_box.append(detail)

            seen = Gtk.Label(xalign=0)
            seen.add_css_class("caption")
            seen.set_text(f"{self._('Seen')}: {checked_at}")
            box.append(seen)
            return card

        def _severity_icon(self, severity: Severity) -> str:
            return {
                Severity.HEALTHY: "emblem-ok-symbolic",
                Severity.WARNING: "dialog-warning-symbolic",
                Severity.CRITICAL: "dialog-error-symbolic",
            }[severity]

        def _severity_label(self, severity: Severity) -> str:
            return {Severity.HEALTHY: "Healthy", Severity.WARNING: "Warning", Severity.CRITICAL: "Critical"}[severity]

        def _severity_css(self, severity: Severity) -> str:
            return {Severity.HEALTHY: "success", Severity.WARNING: "warning", Severity.CRITICAL: "error"}[severity]

        def _action_label(self, action: str) -> str:
            return {
                "network-settings": "Open Network Settings",
                "system-monitor": "Open System Monitor",
                "disk-usage": "Open Disk Usage Analyzer",
            }.get(action, "Re-run checks")

        def _launch_action(self, _button: Gtk.Button, action: str) -> None:
            import shutil

            commands = {
                "network-settings": [["gnome-control-center", "network"], ["nm-connection-editor"]],
                "system-monitor": [["gnome-system-monitor"], ["mate-system-monitor"]],
                "disk-usage": [["baobab"]],
            }
            for command in commands.get(action, []):
                if shutil.which(command[0]):
                    subprocess.Popen(command)
                    return
            self.show_toast(self._("No suitable desktop helper was found for this action."))


def main() -> int:
    if gi is None:
        print(
            "Signal Lantern needs PyGObject, GTK 4, and libadwaita installed.\n"
            "Ubuntu/Debian: sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-4.0 gir1.2-adw-1"
        )
        return 2

    try:
        return SignalLanternApplication().run(sys.argv)
    except Exception:  # pragma: no cover
        traceback.print_exc()
        return 1
