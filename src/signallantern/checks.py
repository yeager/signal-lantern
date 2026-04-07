from __future__ import annotations

import os
import re
import shutil
import socket
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .models import Issue, Severity, Snapshot

APP_PUBLIC_DNS = ("1.1.1.1", 53)
CPU_HIGH_WATERMARK = 90.0
MEMORY_LOW_PERCENT = 10.0
DISK_LOW_PERCENT = 90.0
DISK_CRITICAL_PERCENT = 95.0
DNS_SLOW_MS = 750.0
PUBLIC_DNS_LATENCY_SLOW_MS = 120.0
PUBLIC_DNS_JITTER_WARN_MS = 35.0
PUBLIC_DNS_TARGETS = ["1.1.1.1", "8.8.8.8"]
LATENCY_SAMPLE_WINDOW = 6
WIFI_WEAK_DBM = -72
CAPTIVE_PORTAL_PROBE_URL = "http://connectivitycheck.gstatic.com/generate_204"
CAPTIVE_PORTAL_SUCCESS_HTTP = 204


@dataclass
class HealthState:
    previous_cpu_total: int = 0
    previous_cpu_idle: int = 0
    cpu_usage_percent: float = 0.0
    public_dns_latency_samples: list[float] = field(default_factory=list)


class HealthEngine:
    def __init__(self) -> None:
        self.state = HealthState()

    def collect(self) -> Snapshot:
        raw = self._raw_system_state()
        issues = self._build_issues(raw)
        checked_at = time.strftime("%Y-%m-%d %H:%M:%S")
        metrics = self._metrics(raw)
        status_line = self._status_line(issues)
        return Snapshot(issues=issues, status_line=status_line, checked_at=checked_at, metrics=metrics, raw=raw)

    def _raw_system_state(self) -> dict[str, Any]:
        network = self._network_state()
        cpu = self._cpu_state()
        memory = self._memory_state()
        disk = self._disk_state()
        dns = self._dns_state()
        reboot = self._reboot_state()
        battery = self._battery_state()
        storage = self._storage_state()
        audio = self._audio_state()
        return {
            "network": network,
            "cpu": cpu,
            "memory": memory,
            "disk": disk,
            "dns": dns,
            "reboot": reboot,
            "battery": battery,
            "storage": storage,
            "audio": audio,
        }

    def _build_issues(self, raw: dict[str, Any]) -> list[Issue]:
        issues: list[Issue] = []
        network = raw["network"]
        dns = raw["dns"]
        cpu = raw["cpu"]
        memory = raw["memory"]
        disk = raw["disk"]
        reboot = raw["reboot"]
        battery = raw["battery"]
        storage = raw["storage"]
        audio = raw["audio"]

        if not network["connected"]:
            issues.append(
                Issue(
                    key="network_disconnected",
                    severity=Severity.CRITICAL,
                    title="No network connection",
                    meaning="Your computer does not seem to be connected to Wi-Fi or wired Ethernet right now.",
                    suggestions=[
                        "Check that Wi-Fi is turned on.",
                        "Reconnect to your wireless network.",
                        "Plug in the network cable if you use wired internet.",
                    ],
                    details={
                        "active_interface": network.get("active_interface") or "none",
                        "default_gateway": network.get("gateway") or "none",
                        "nmcli_state": network.get("nmcli_state") or "unknown",
                    },
                    source="network",
                    action="network-settings",
                    notification_body="Open network settings and reconnect to get back online.",
                )
            )

        if network.get("captive_portal"):
            issues.append(
                Issue(
                    key="captive_portal",
                    severity=Severity.WARNING,
                    title="Sign-in required on this network",
                    meaning="This network likely wants you to open a browser and sign in before the internet works normally.",
                    suggestions=[
                        "Open a web browser and wait a moment for a sign-in page.",
                        "If nothing appears, try visiting a simple website that starts with http://.",
                        "After signing in, run the checks again.",
                    ],
                    details={
                        "connectivity": network.get("connectivity") or "unknown",
                        "interface": network.get("active_interface") or "unknown",
                        "probe_url": CAPTIVE_PORTAL_PROBE_URL,
                    },
                    source="network",
                    action="network-settings",
                    notification_body="Open a browser and complete the network sign-in page.",
                )
            )

        if network.get("wifi_radio") == "disabled":
            issues.append(
                Issue(
                    key="wifi_disabled",
                    severity=Severity.WARNING,
                    title="Wi-Fi is turned off",
                    meaning="Your computer has Wi-Fi hardware, but wireless networking is currently switched off.",
                    suggestions=[
                        "Turn Wi-Fi on from the system menu or network settings.",
                        "If airplane mode is enabled, turn it off.",
                        "Run the checks again after reconnecting.",
                    ],
                    details={
                        "wifi_hardware": network.get("wifi_hardware") or "unknown",
                        "wifi_radio": network.get("wifi_radio") or "unknown",
                        "nmcli_state": network.get("nmcli_state") or "unknown",
                    },
                    source="network",
                    action="network-settings",
                    notification_body="Turn Wi-Fi back on to reconnect wirelessly.",
                )
            )

        if network.get("wifi_hardware") == "disabled":
            issues.append(
                Issue(
                    key="wifi_hardware_blocked",
                    severity=Severity.WARNING,
                    title="Wi-Fi hardware is blocked",
                    meaning="Linux can see the Wi-Fi adapter, but the hardware itself looks switched off or blocked.",
                    suggestions=[
                        "Check for a laptop Wi-Fi switch or airplane-mode key.",
                        "Turn off airplane mode in the system menu.",
                        "Restart once if the hardware switch state looks wrong.",
                    ],
                    details={
                        "wifi_hardware": network.get("wifi_hardware") or "unknown",
                        "wifi_radio": network.get("wifi_radio") or "unknown",
                    },
                    source="network",
                    action="network-settings",
                    notification_body="Turn the Wi-Fi hardware back on to use wireless networking.",
                )
            )

        if network.get("wifi_hardware") == "missing":
            issues.append(
                Issue(
                    key="wifi_adapter_missing",
                    severity=Severity.WARNING,
                    title="Wi-Fi adapter may be missing",
                    meaning="Linux does not currently see a working Wi-Fi adapter, so wireless networking may need a driver or a reconnected adapter.",
                    suggestions=[
                        "If you use a USB Wi-Fi adapter, unplug it and plug it in again.",
                        "Open Additional Drivers and check whether Linux offers a Wi-Fi driver.",
                        "If this is a laptop, restart once and see if Wi-Fi returns.",
                    ],
                    details={
                        "wifi_hardware": network.get("wifi_hardware") or "unknown",
                        "wifi_devices": ", ".join(network.get("wifi_devices") or []) or "none",
                        "ethernet_devices": ", ".join(network.get("ethernet_devices") or []) or "none",
                    },
                    source="network",
                    action="network-settings",
                    notification_body="Linux cannot find a working Wi-Fi adapter right now.",
                )
            )

        wifi_signal = network.get("wifi_signal_dbm")
        if wifi_signal is not None and wifi_signal <= WIFI_WEAK_DBM:
            issues.append(
                Issue(
                    key="weak_wifi",
                    severity=Severity.WARNING,
                    title="Weak Wi-Fi signal",
                    meaning="Your wireless connection is active, but the signal is weak and may cause slow speeds or dropouts.",
                    suggestions=[
                        "Move closer to the router or access point.",
                        "Reduce obstacles between your device and the router.",
                        "Use Ethernet for a more stable connection if possible.",
                    ],
                    details={
                        "ssid": network.get("wifi_ssid") or "unknown",
                        "signal_dbm": wifi_signal,
                        "signal_percent": network.get("wifi_signal_percent"),
                        "device": network.get("wifi_device") or "unknown",
                    },
                    source="network",
                    action="network-settings",
                    notification_body="Move closer to the router or switch to a stronger connection.",
                )
            )

        if network["connected"] and network.get("gateway") and network.get("gateway_reachable") is False:
            issues.append(
                Issue(
                    key="gateway_unreachable",
                    severity=Severity.CRITICAL,
                    title="Router is not responding",
                    meaning="Your computer is connected to the local network, but the default gateway is not replying.",
                    suggestions=[
                        "Restart the router if you can.",
                        "Reconnect to your network connection.",
                        "Try another device on the same network to compare.",
                    ],
                    details={
                        "gateway": network.get("gateway"),
                        "ping_ms": network.get("gateway_ping_ms"),
                        "interface": network.get("active_interface") or "unknown",
                    },
                    source="network",
                    action="network-settings",
                    notification_body="Reconnect or troubleshoot the local network hardware.",
                )
            )

        if dns.get("latency_ms") is not None and dns["latency_ms"] > DNS_SLOW_MS and dns.get("success"):
            issues.append(
                Issue(
                    key="dns_slow",
                    severity=Severity.WARNING,
                    title="DNS lookups are slow",
                    meaning="The DNS server is answering, but lookups are slower than normal.",
                    suggestions=[
                        "Wait a minute and try again in case the problem is temporary.",
                        "Switch DNS server in network settings if you know a better one.",
                        "Restart the network connection or router.",
                    ],
                    details={
                        "resolver": dns.get("resolver") or "system-default",
                        "latency_ms": dns.get("latency_ms"),
                        "probe_host": dns.get("probe_host"),
                    },
                    source="dns",
                    action="network-settings",
                    notification_body="Name lookups are slow, so websites may feel sluggish.",
                )
            )

        if network["connected"] and dns.get("success") is False:
            issues.append(
                Issue(
                    key="dns_failed",
                    severity=Severity.CRITICAL,
                    title="DNS is failing",
                    meaning="The DNS server does not appear to be answering reliably.",
                    suggestions=[
                        "Restart the network connection or router.",
                        "Switch DNS server in network settings if you know a better one.",
                        "Try another network if websites still do not load.",
                    ],
                    details={
                        "resolver": dns.get("resolver") or "system-default",
                        "error": dns.get("error") or "lookup failed",
                        "probe_host": dns.get("probe_host"),
                    },
                    source="dns",
                    action="network-settings",
                    notification_body="Websites may fail to load until name resolution works again.",
                )
            )

        if dns.get("public_latency_ms") is not None and dns["public_latency_ms"] >= PUBLIC_DNS_LATENCY_SLOW_MS:
            issues.append(
                Issue(
                    key="internet_latency_high",
                    severity=Severity.WARNING,
                    title="Internet connection looks slow",
                    meaning="Latency to a stable public target is higher than normal, so browsing, calls, or gaming may feel sluggish.",
                    suggestions=[
                        "If you are on Wi-Fi, move closer to the router or try Ethernet.",
                        "Pause downloads, cloud sync, or streaming on this network.",
                        "Run the checks again in a minute to see if the slowdown is temporary.",
                    ],
                    details={
                        "target": dns.get("public_target") or "unknown",
                        "latency_ms": dns.get("public_latency_ms"),
                        "jitter_ms": dns.get("public_jitter_ms"),
                        "samples": dns.get("public_samples"),
                    },
                    source="dns",
                    action="network-settings",
                    notification_body="The internet connection looks slow right now.",
                )
            )

        if dns.get("public_jitter_ms") is not None and dns["public_jitter_ms"] >= PUBLIC_DNS_JITTER_WARN_MS:
            issues.append(
                Issue(
                    key="internet_jitter_high",
                    severity=Severity.WARNING,
                    title="Connection stability is uneven",
                    meaning="Latency is jumping around more than usual, which can cause choppy calls, buffering, or lag spikes.",
                    suggestions=[
                        "If you are on Wi-Fi, reduce distance and interference if you can.",
                        "Pause other network-heavy activity on this connection.",
                        "If the problem keeps happening, restart the router or try another network.",
                    ],
                    details={
                        "target": dns.get("public_target") or "unknown",
                        "latency_ms": dns.get("public_latency_ms"),
                        "jitter_ms": dns.get("public_jitter_ms"),
                        "samples": dns.get("public_samples"),
                    },
                    source="dns",
                    action="network-settings",
                    notification_body="The connection is unstable and latency is bouncing around.",
                )
            )

        if cpu["usage_percent"] >= CPU_HIGH_WATERMARK:
            issues.append(
                Issue(
                    key="high_cpu",
                    severity=Severity.WARNING,
                    title="High processor load",
                    meaning="Your system has been under heavy CPU load for a while. Apps may feel slow or unresponsive.",
                    suggestions=[
                        "Close apps you do not need.",
                        "Check which process is using the CPU in System Monitor.",
                        "Restart the system if the load does not drop.",
                    ],
                    details={
                        "usage_percent": round(cpu["usage_percent"], 1),
                        "load_average": cpu.get("load_average"),
                        "top_processes": cpu.get("top_processes"),
                    },
                    source="cpu",
                    action="system-monitor",
                    notification_body="Close a few heavy apps or inspect System Monitor.",
                )
            )

        if memory["available_percent"] <= MEMORY_LOW_PERCENT:
            issues.append(
                Issue(
                    key="low_memory",
                    severity=Severity.CRITICAL if memory["available_percent"] <= 5 else Severity.WARNING,
                    title="System is low on memory",
                    meaning="Available memory is running low. Apps may freeze or swap heavily.",
                    suggestions=[
                        "Close large apps or browser tabs you do not need.",
                        "Restart heavy apps that may be leaking memory.",
                        "Reboot if memory pressure stays high.",
                    ],
                    details={
                        "available_percent": round(memory["available_percent"], 1),
                        "available_gib": round(memory["available_gib"], 2),
                        "total_gib": round(memory["total_gib"], 2),
                        "swap_free_gib": round(memory["swap_free_gib"], 2),
                    },
                    source="memory",
                    action="system-monitor",
                    notification_body="Close a few large apps to keep the system responsive.",
                )
            )

        if disk["used_percent"] >= DISK_LOW_PERCENT:
            issues.append(
                Issue(
                    key="low_disk",
                    severity=Severity.CRITICAL if disk["used_percent"] >= DISK_CRITICAL_PERCENT else Severity.WARNING,
                    title="Disk space is running low",
                    meaning="Your main disk is almost full. Downloads, updates, and apps may start failing.",
                    suggestions=[
                        "Delete large files you no longer need.",
                        "Empty the trash.",
                        "Move files to external or cloud storage.",
                    ],
                    details={
                        "mount": disk["mount"],
                        "used_percent": round(disk["used_percent"], 1),
                        "free_gib": round(disk["free_gib"], 2),
                        "total_gib": round(disk["total_gib"], 2),
                    },
                    source="disk",
                    action="disk-usage",
                    notification_body="Free some space so updates and downloads do not fail.",
                )
            )

        if reboot["required"]:
            issues.append(
                Issue(
                    key="reboot_required",
                    severity=Severity.WARNING,
                    title="A restart is required",
                    meaning="Linux has pending updates or driver changes that will not fully apply until you restart the computer.",
                    suggestions=[
                        "Save your work and restart the computer when convenient.",
                        "After restarting, run the checks again.",
                        "If a device still does not work, check updates or Additional Drivers.",
                    ],
                    details={
                        "reason": reboot.get("reason") or "system updates or driver changes",
                    },
                    source="system",
                    notification_body="Restart the computer to finish applying updates or driver changes.",
                )
            )

        if battery.get("present") and battery.get("percent") is not None and battery.get("charging") is False and battery["percent"] <= 15:
            issues.append(
                Issue(
                    key="battery_low",
                    severity=Severity.CRITICAL if battery["percent"] <= 8 else Severity.WARNING,
                    title="Battery is running low",
                    meaning="Your computer is on battery power and may shut down soon if you do not plug it in.",
                    suggestions=[
                        "Plug in the charger as soon as you can.",
                        "Save your work in case the battery runs out.",
                        "Lower screen brightness or close heavy apps to stretch the battery a bit longer.",
                    ],
                    details={
                        "battery_percent": battery.get("percent"),
                        "charging": battery.get("charging"),
                        "status": battery.get("status") or "unknown",
                    },
                    source="power",
                    notification_body="Plug in the charger soon to avoid an unexpected shutdown.",
                )
            )

        if storage.get("root_read_only"):
            issues.append(
                Issue(
                    key="root_read_only",
                    severity=Severity.CRITICAL,
                    title="System disk is read-only",
                    meaning="Linux mounted the main filesystem as read-only, so saving files, updates, or app changes may fail.",
                    suggestions=[
                        "Save any work you still can to another location.",
                        "Restart the computer and check whether the disk becomes writable again.",
                        "If the problem returns, check the disk for errors or ask for technical help.",
                    ],
                    details={
                        "mount": storage.get("root_mount") or "/",
                        "mode": "read-only",
                    },
                    source="storage",
                    notification_body="The main filesystem is read-only and may block saving or updates.",
                )
            )

        if storage.get("boot_used_percent") is not None and storage["boot_used_percent"] >= 90:
            issues.append(
                Issue(
                    key="boot_partition_low",
                    severity=Severity.WARNING,
                    title="Boot partition is almost full",
                    meaning="The small boot partition is nearly full, so kernel or system updates may fail.",
                    suggestions=[
                        "Install any pending updates fully, then restart the computer.",
                        "Remove old kernels or packages only if you know how, or ask for help.",
                        "If updates keep failing, check disk usage in /boot specifically.",
                    ],
                    details={
                        "mount": storage.get("boot_mount") or "/boot",
                        "used_percent": storage.get("boot_used_percent"),
                    },
                    source="storage",
                    notification_body="The boot partition is nearly full and updates may fail.",
                )
            )

        if audio.get("backend_available") and not audio.get("server_running"):
            issues.append(
                Issue(
                    key="audio_server_down",
                    severity=Severity.WARNING,
                    title="Sound service is not responding",
                    meaning="Linux audio services are not responding, so speakers and microphones may stop working until the sound stack comes back.",
                    suggestions=[
                        "Log out and back in, or restart the computer if sound disappeared suddenly.",
                        "If you know how, restart PipeWire or PulseAudio from system settings or a terminal.",
                        "Check whether another app is holding the sound device in a broken state.",
                    ],
                    details={
                        "backend": audio.get("backend") or "unknown",
                        "error": audio.get("error") or "no response",
                    },
                    source="audio",
                    notification_body="The Linux sound service is not responding.",
                )
            )

        if audio.get("server_running") and not audio.get("has_sinks"):
            issues.append(
                Issue(
                    key="audio_output_missing",
                    severity=Severity.WARNING,
                    title="No sound output device found",
                    meaning="Linux cannot currently find any speaker, headset, or other playback device.",
                    suggestions=[
                        "Make sure speakers, headphones, or HDMI audio are connected and powered on.",
                        "Open sound settings and check whether the output device appears there.",
                        "If audio hardware vanished after an update, restart the computer and check again.",
                    ],
                    details={
                        "backend": audio.get("backend") or "unknown",
                        "default_sink": audio.get("default_sink") or "none",
                    },
                    source="audio",
                    notification_body="No sound output device is available.",
                )
            )

        if audio.get("server_running") and not audio.get("has_sources"):
            issues.append(
                Issue(
                    key="audio_input_missing",
                    severity=Severity.WARNING,
                    title="No microphone found",
                    meaning="Linux cannot currently find any microphone or other recording device.",
                    suggestions=[
                        "Reconnect the microphone, headset, or USB audio device if you use one.",
                        "Open sound settings and check whether an input device appears there.",
                        "If the microphone disappeared after docking or undocking, restart audio apps and try again.",
                    ],
                    details={
                        "backend": audio.get("backend") or "unknown",
                        "default_source": audio.get("default_source") or "none",
                    },
                    source="audio",
                    notification_body="No microphone or recording device is available.",
                )
            )

        if audio.get("server_running") and audio.get("output_muted"):
            issues.append(
                Issue(
                    key="audio_output_muted",
                    severity=Severity.WARNING,
                    title="Sound output is muted",
                    meaning="The current playback device is muted, so apps may look fine but still make no sound.",
                    suggestions=[
                        "Unmute sound from the system menu or sound settings.",
                        "Check that the correct output device is selected.",
                        "Raise the output volume if it is still set extremely low.",
                    ],
                    details={
                        "default_sink": audio.get("default_sink") or "none",
                        "output_volume_percent": audio.get("output_volume_percent"),
                    },
                    source="audio",
                    notification_body="Sound output is muted.",
                )
            )
        elif audio.get("server_running") and audio.get("output_volume_percent") == 0:
            issues.append(
                Issue(
                    key="audio_output_silent",
                    severity=Severity.WARNING,
                    title="Sound volume is set to zero",
                    meaning="The playback device is active, but the output volume is currently zero.",
                    suggestions=[
                        "Raise the volume from the system menu or sound settings.",
                        "Check the app itself is not muted separately.",
                        "Verify the correct output device is selected.",
                    ],
                    details={
                        "default_sink": audio.get("default_sink") or "none",
                        "output_volume_percent": audio.get("output_volume_percent"),
                    },
                    source="audio",
                    notification_body="The active sound output volume is set to zero.",
                )
            )

        if audio.get("server_running") and audio.get("input_muted"):
            issues.append(
                Issue(
                    key="audio_input_muted",
                    severity=Severity.WARNING,
                    title="Microphone is muted",
                    meaning="The current recording device is muted, so calls or recordings may not hear you.",
                    suggestions=[
                        "Unmute the microphone in the system sound settings.",
                        "Check whether your headset or keyboard has a hardware mute switch.",
                        "Test the microphone again after unmuting it.",
                    ],
                    details={
                        "default_source": audio.get("default_source") or "none",
                        "input_volume_percent": audio.get("input_volume_percent"),
                    },
                    source="audio",
                    notification_body="The microphone is muted.",
                )
            )

        severity_order = {Severity.CRITICAL: 0, Severity.WARNING: 1, Severity.HEALTHY: 2}
        return sorted(issues, key=lambda issue: severity_order[issue.severity])

    def _status_line(self, issues: list[Issue]) -> str:
        if not issues:
            return "Your system looks healthy."
        critical_count = sum(1 for issue in issues if issue.severity == Severity.CRITICAL)
        if critical_count:
            return "Critical issue detected" if len(issues) == 1 else f"{len(issues)} issues need attention, including {critical_count} critical."
        return "Needs attention" if len(issues) == 1 else f"{len(issues)} issues need attention."

    def _metrics(self, raw: dict[str, Any]) -> dict[str, str]:
        network = raw["network"]
        dns = raw["dns"]
        cpu = raw["cpu"]
        memory = raw["memory"]
        disk = raw["disk"]
        battery = raw["battery"]
        storage = raw["storage"]
        audio = raw["audio"]

        network_value = "Captive portal" if network.get("captive_portal") else ("Online" if network["connected"] else "Offline")
        wifi_value = "N/A"
        if network.get("wifi_hardware") == "missing":
            wifi_value = "Adapter missing"
        elif network.get("wifi_hardware") == "disabled":
            wifi_value = "Hardware blocked"
        elif network.get("wifi_radio") == "disabled":
            wifi_value = "Off"
        elif network.get("wifi_signal_dbm") is not None:
            label = "Weak" if network["wifi_signal_dbm"] <= WIFI_WEAK_DBM else "OK"
            wifi_value = f"{label} ({network.get('wifi_signal_percent', '?')}%)"
        gateway_value = "Reachable" if network.get("gateway_reachable") else ("Unreachable" if network.get("gateway") else "Unknown")
        dns_value = f"{int(dns['latency_ms'])} ms" if dns.get("latency_ms") is not None else ("Failing" if dns.get("success") is False else "Unknown")
        if dns.get("public_latency_ms") is not None:
            dns_value = f"{int(dns['public_latency_ms'])} ms"
            if dns.get("public_jitter_ms") is not None and dns["public_jitter_ms"] >= PUBLIC_DNS_JITTER_WARN_MS:
                dns_value += f" ±{int(dns['public_jitter_ms'])}"
        if storage.get("root_read_only"):
            disk_value = "Read-only"
        elif storage.get("boot_used_percent") is not None and storage["boot_used_percent"] >= 90:
            disk_value = f"/boot {storage['boot_used_percent']:.0f}% used"
        else:
            disk_value = f"{disk['used_percent']:.0f}% used"

        metrics = {
            "Network": network_value,
            "Wi-Fi": wifi_value,
            "Gateway": gateway_value,
            "DNS": dns_value,
            "CPU": f"{cpu['usage_percent']:.0f}%",
            "Memory": f"{memory['available_percent']:.0f}% free",
            "Disk": disk_value,
        }
        if audio.get("backend_available"):
            if not audio.get("server_running"):
                metrics["Audio"] = "Service down"
            elif not audio.get("has_sinks"):
                metrics["Audio"] = "No output"
            elif audio.get("output_muted"):
                metrics["Audio"] = "Muted"
            else:
                metrics["Audio"] = f"{audio.get('output_volume_percent', 0):.0f}%"
        if battery.get("present") and battery.get("percent") is not None:
            suffix = "charging" if battery.get("charging") else "battery"
            metrics["Power"] = f"{battery['percent']:.0f}% {suffix}"
        return metrics

    def _network_state(self) -> dict[str, Any]:
        route_output = self._command(["ip", "route", "show", "default"])
        gateway = None
        active_interface = None
        if route_output:
            match = re.search(r"default via ([^ ]+) dev ([^ ]+)", route_output)
            if match:
                gateway = match.group(1)
                active_interface = match.group(2)

        nmcli_state = self._command(["nmcli", "-t", "-f", "STATE", "general"], timeout=4)
        connectivity = self._command(["nmcli", "-t", "-f", "CONNECTIVITY", "general"], timeout=4)
        wifi_caps = self._command(["nmcli", "-t", "-f", "WIFI-HW,WIFI", "general"], timeout=4)
        connected = bool(gateway or (nmcli_state and "connected" in nmcli_state))

        wifi_device = None
        wifi_ssid = None
        wifi_signal_percent = None
        wifi_signal_dbm = None
        wifi_devices: list[str] = []
        ethernet_devices: list[str] = []

        device_status = self._command(["nmcli", "-t", "-f", "DEVICE,TYPE,STATE", "device", "status"], timeout=4)
        if device_status:
            for line in device_status.splitlines():
                parts = line.split(":")
                if len(parts) < 3:
                    continue
                if parts[1] == "wifi":
                    wifi_devices.append(parts[0])
                elif parts[1] == "ethernet":
                    ethernet_devices.append(parts[0])

        wifi_list = self._command(["nmcli", "-t", "-f", "IN-USE,SSID,SIGNAL,DEVICE", "dev", "wifi"], timeout=4)
        if wifi_list:
            for line in wifi_list.splitlines():
                parts = line.split(":")
                if parts and parts[0] == "*":
                    wifi_ssid = parts[1] if len(parts) > 1 else None
                    wifi_signal_percent = self._safe_int(parts[2]) if len(parts) > 2 else None
                    wifi_device = parts[3] if len(parts) > 3 else None
                    break

        if wifi_signal_percent is not None:
            wifi_signal_dbm = int((wifi_signal_percent / 2) - 100)
            connected = True

        wifi_hardware = "unknown"
        wifi_radio = "unknown"
        if wifi_caps:
            values = wifi_caps.split(":", 1)
            if values:
                wifi_hardware = values[0].strip().lower() or "unknown"
            if len(values) > 1:
                wifi_radio = values[1].strip().lower() or "unknown"
        if wifi_hardware == "enabled" and not wifi_devices and not wifi_device:
            wifi_hardware = "missing"

        gateway_reachable = None
        gateway_ping_ms = None
        if gateway and shutil.which("ping"):
            ping_output = self._command(["ping", "-c", "1", "-W", "1", gateway], timeout=3)
            gateway_reachable = ping_output is not None and "1 received" in ping_output
            if ping_output:
                latency_match = re.search(r"time=([0-9.]+) ms", ping_output)
                if latency_match:
                    gateway_ping_ms = float(latency_match.group(1))

        captive_portal = False
        if connectivity and connectivity.strip().lower() == "portal":
            captive_portal = True
        elif connected and connectivity and connectivity.strip().lower() in {"limited", "unknown"}:
            try:
                request = urllib.request.Request(CAPTIVE_PORTAL_PROBE_URL, headers={"User-Agent": "Signal Lantern/0.1"})
                with urllib.request.urlopen(request, timeout=4) as response:
                    captive_portal = response.status != CAPTIVE_PORTAL_SUCCESS_HTTP
            except urllib.error.HTTPError as error:
                captive_portal = error.code != CAPTIVE_PORTAL_SUCCESS_HTTP
            except Exception:
                captive_portal = False

        return {
            "connected": connected,
            "gateway": gateway,
            "gateway_reachable": gateway_reachable,
            "gateway_ping_ms": gateway_ping_ms,
            "active_interface": active_interface,
            "nmcli_state": nmcli_state.strip() if nmcli_state else None,
            "connectivity": connectivity.strip().lower() if connectivity else None,
            "captive_portal": captive_portal,
            "wifi_device": wifi_device,
            "wifi_devices": wifi_devices,
            "ethernet_devices": ethernet_devices,
            "wifi_hardware": wifi_hardware,
            "wifi_radio": wifi_radio,
            "wifi_ssid": wifi_ssid,
            "wifi_signal_percent": wifi_signal_percent,
            "wifi_signal_dbm": wifi_signal_dbm,
        }

    def _reboot_state(self) -> dict[str, Any]:
        marker = Path("/var/run/reboot-required")
        reason_file = Path("/var/run/reboot-required.pkgs")
        reason = ""
        if reason_file.exists():
            try:
                lines = [line.strip() for line in reason_file.read_text(encoding="utf-8").splitlines() if line.strip()]
                reason = ", ".join(lines[:5])
            except OSError:
                reason = ""
        return {
            "required": marker.exists(),
            "reason": reason,
        }

    def _dns_state(self) -> dict[str, Any]:
        resolver = self._system_resolver()
        host = "example.com"
        started = time.perf_counter()
        try:
            socket.setdefaulttimeout(2.5)
            socket.getaddrinfo(host, 443, proto=socket.IPPROTO_TCP)
            latency_ms = (time.perf_counter() - started) * 1000
        except OSError as error:
            return {
                "success": False,
                "latency_ms": None,
                "resolver": resolver,
                "probe_host": host,
                "error": str(error),
                "public_target": None,
                "public_latency_ms": None,
                "public_jitter_ms": None,
                "public_samples": [],
            }

        public_probe = self._public_dns_probe()
        samples = list(self.state.public_dns_latency_samples)
        if public_probe["latency_ms"] is not None:
            samples.append(public_probe["latency_ms"])
            samples = samples[-LATENCY_SAMPLE_WINDOW:]
            self.state.public_dns_latency_samples = samples
        jitter_ms = None
        if len(samples) >= 3:
            mean = sum(samples) / len(samples)
            jitter_ms = sum(abs(sample - mean) for sample in samples) / len(samples)

        return {
            "success": True,
            "latency_ms": latency_ms,
            "resolver": resolver,
            "probe_host": host,
            "public_target": public_probe["target"],
            "public_latency_ms": public_probe["latency_ms"],
            "public_jitter_ms": jitter_ms,
            "public_samples": samples,
            "public_error": public_probe.get("error"),
        }

    def _public_dns_probe(self) -> dict[str, Any]:
        if not shutil.which("ping"):
            return {"target": None, "latency_ms": None, "error": "ping unavailable"}
        for target in PUBLIC_DNS_TARGETS:
            started = time.perf_counter()
            output = self._command(["ping", "-c", "1", "-W", "2", target], timeout=4)
            if not output:
                continue
            latency_match = re.search(r"time=([0-9.]+) ms", output)
            if latency_match:
                return {
                    "target": target,
                    "latency_ms": float(latency_match.group(1)),
                    "elapsed_ms": (time.perf_counter() - started) * 1000,
                }
        return {"target": PUBLIC_DNS_TARGETS[0], "latency_ms": None, "error": "public DNS ping failed"}

    def _cpu_state(self) -> dict[str, Any]:
        usage_percent = self._cpu_usage_percent()
        load_average = os.getloadavg()
        top_processes = self._command(["ps", "-eo", "pid,comm,%cpu", "--sort=-%cpu"], timeout=4)
        top_rows = []
        if top_processes:
            for line in top_processes.splitlines()[1:4]:
                if line.strip():
                    top_rows.append(" ".join(line.split()))
        return {
            "usage_percent": usage_percent,
            "load_average": [round(value, 2) for value in load_average],
            "top_processes": top_rows,
        }

    def _cpu_usage_percent(self) -> float:
        proc_stat = Path("/proc/stat")
        if not proc_stat.exists():
            load = os.getloadavg()[0]
            cpu_count = os.cpu_count() or 1
            return max(0.0, min(100.0, (load / cpu_count) * 100.0))
        with proc_stat.open("r", encoding="utf-8") as handle:
            line = handle.readline()
        values = [int(value) for value in line.split()[1:]]
        idle = values[3] + values[4]
        total = sum(values)

        if self.state.previous_cpu_total == 0:
            self.state.previous_cpu_total = total
            self.state.previous_cpu_idle = idle
            return 0.0

        total_delta = total - self.state.previous_cpu_total
        idle_delta = idle - self.state.previous_cpu_idle
        self.state.previous_cpu_total = total
        self.state.previous_cpu_idle = idle
        if total_delta <= 0:
            return self.state.cpu_usage_percent
        self.state.cpu_usage_percent = max(0.0, min(100.0, 100.0 * (1.0 - idle_delta / total_delta)))
        return self.state.cpu_usage_percent

    def _memory_state(self) -> dict[str, float]:
        meminfo = Path("/proc/meminfo")
        if not meminfo.exists():
            total_bytes = os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") if hasattr(os, "sysconf") else 1
            available_bytes = total_bytes * 0.5
            return {
                "total_gib": total_bytes / (1024 ** 3),
                "available_gib": available_bytes / (1024 ** 3),
                "available_percent": 50.0,
                "swap_free_gib": 0.0,
            }
        values: dict[str, int] = {}
        with meminfo.open("r", encoding="utf-8") as handle:
            for line in handle:
                key, raw = line.split(":", 1)
                values[key] = int(raw.strip().split()[0])
        total_kib = values.get("MemTotal", 1)
        available_kib = values.get("MemAvailable", values.get("MemFree", 0))
        swap_free_kib = values.get("SwapFree", 0)
        return {
            "total_gib": total_kib / (1024 * 1024),
            "available_gib": available_kib / (1024 * 1024),
            "available_percent": (available_kib / total_kib) * 100,
            "swap_free_gib": swap_free_kib / (1024 * 1024),
        }

    def _disk_state(self) -> dict[str, float | str]:
        usage = shutil.disk_usage("/")
        used_percent = (usage.used / usage.total) * 100 if usage.total else 0.0
        return {
            "mount": "/",
            "used_percent": used_percent,
            "free_gib": usage.free / (1024 ** 3),
            "total_gib": usage.total / (1024 ** 3),
        }

    def _battery_state(self) -> dict[str, Any]:
        power_dir = Path("/sys/class/power_supply")
        if not power_dir.exists():
            return {"present": False, "percent": None, "charging": None, "status": None}
        for candidate in sorted(power_dir.iterdir()):
            if not candidate.name.startswith("BAT"):
                continue
            status = self._read_text(candidate / "status")
            percent_raw = self._read_text(candidate / "capacity")
            percent = self._safe_int(percent_raw)
            charging = None
            if status:
                normalized = status.lower()
                charging = normalized in {"charging", "full"}
            return {"present": True, "percent": percent, "charging": charging, "status": status}
        return {"present": False, "percent": None, "charging": None, "status": None}

    def _storage_state(self) -> dict[str, Any]:
        root_read_only = False
        mounts = Path("/proc/mounts")
        if mounts.exists():
            for line in mounts.read_text(encoding="utf-8").splitlines():
                parts = line.split()
                if len(parts) >= 4 and parts[1] == "/":
                    root_read_only = "ro" in parts[3].split(",")
                    break
        boot_mount = "/boot" if Path("/boot").exists() else None
        boot_used_percent = None
        if boot_mount:
            try:
                boot_usage = shutil.disk_usage(boot_mount)
                boot_used_percent = (boot_usage.used / boot_usage.total) * 100 if boot_usage.total else 0.0
            except OSError:
                boot_used_percent = None
        return {
            "root_mount": "/",
            "root_read_only": root_read_only,
            "boot_mount": boot_mount,
            "boot_used_percent": boot_used_percent,
        }

    def _audio_state(self) -> dict[str, Any]:
        backend = None
        info = ""
        error = None
        pactl = shutil.which("pactl")
        wpctl = shutil.which("wpctl")
        if pactl:
            backend = "pactl"
            info = self._command(["pactl", "info"], timeout=4) or ""
        elif wpctl:
            backend = "wpctl"
            info = self._command(["wpctl", "status"], timeout=4) or ""
        else:
            return {
                "backend_available": False,
                "backend": None,
                "server_running": False,
                "has_sinks": False,
                "has_sources": False,
                "default_sink": None,
                "default_source": None,
                "output_muted": None,
                "input_muted": None,
                "output_volume_percent": None,
                "input_volume_percent": None,
                "error": None,
            }

        server_running = bool(info)
        if not server_running:
            error = "audio backend returned no status"

        sinks = self._command(["pactl", "list", "short", "sinks"], timeout=4) if pactl else ""
        sources = self._command(["pactl", "list", "short", "sources"], timeout=4) if pactl else ""
        default_sink = self._command(["pactl", "get-default-sink"], timeout=4) if pactl else ""
        default_source = self._command(["pactl", "get-default-source"], timeout=4) if pactl else ""
        sink_mute = self._command(["pactl", "get-sink-mute", "@DEFAULT_SINK@"], timeout=4) if pactl else ""
        source_mute = self._command(["pactl", "get-source-mute", "@DEFAULT_SOURCE@"], timeout=4) if pactl else ""
        sink_volume = self._command(["pactl", "get-sink-volume", "@DEFAULT_SINK@"], timeout=4) if pactl else ""
        source_volume = self._command(["pactl", "get-source-volume", "@DEFAULT_SOURCE@"], timeout=4) if pactl else ""

        return {
            "backend_available": True,
            "backend": backend,
            "server_running": server_running,
            "has_sinks": bool(sinks.strip()) if isinstance(sinks, str) else False,
            "has_sources": bool(sources.strip()) if isinstance(sources, str) else False,
            "default_sink": default_sink.strip() or None,
            "default_source": default_source.strip() or None,
            "output_muted": sink_mute.strip().endswith("yes") if sink_mute else None,
            "input_muted": source_mute.strip().endswith("yes") if source_mute else None,
            "output_volume_percent": self._extract_percent(sink_volume),
            "input_volume_percent": self._extract_percent(source_volume),
            "error": error,
        }

    def _system_resolver(self) -> str:
        path = Path("/etc/resolv.conf")
        if not path.exists():
            return "unknown"
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("nameserver "):
                return line.split()[1]
        return "system-default"

    def _safe_int(self, value: str | None) -> int | None:
        if value is None or value == "":
            return None
        try:
            return int(value)
        except ValueError:
            return None

    def _extract_percent(self, text: str | None) -> int | None:
        if not text:
            return None
        match = re.search(r"(\d+)%", text)
        if not match:
            return None
        return self._safe_int(match.group(1))

    def _command(self, command: list[str], timeout: int = 3) -> str | None:
        if not shutil.which(command[0]):
            return None
        try:
            completed = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except (OSError, subprocess.SubprocessError):
            return None
        if completed.returncode != 0 and not completed.stdout:
            return None
        return completed.stdout.strip() or completed.stderr.strip() or None
