from __future__ import annotations

import os
import re
import shutil
import socket
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .models import Issue, Severity, Snapshot

APP_PUBLIC_DNS = ("1.1.1.1", 53)
CPU_HIGH_WATERMARK = 90.0
MEMORY_LOW_PERCENT = 10.0
DISK_LOW_PERCENT = 90.0
DISK_CRITICAL_PERCENT = 95.0
DNS_SLOW_MS = 750.0
WIFI_WEAK_DBM = -72


@dataclass
class HealthState:
    previous_cpu_total: int = 0
    previous_cpu_idle: int = 0
    cpu_usage_percent: float = 0.0


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
        return {
            "network": network,
            "cpu": cpu,
            "memory": memory,
            "disk": disk,
            "dns": dns,
        }

    def _build_issues(self, raw: dict[str, Any]) -> list[Issue]:
        issues: list[Issue] = []
        network = raw["network"]
        dns = raw["dns"]
        cpu = raw["cpu"]
        memory = raw["memory"]
        disk = raw["disk"]

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

        network_value = "Online" if network["connected"] else "Offline"
        wifi_value = "N/A"
        if network.get("wifi_signal_dbm") is not None:
            label = "Weak" if network["wifi_signal_dbm"] <= WIFI_WEAK_DBM else "OK"
            wifi_value = f"{label} ({network.get('wifi_signal_percent', '?')}%)"
        gateway_value = "Reachable" if network.get("gateway_reachable") else ("Unreachable" if network.get("gateway") else "Unknown")
        dns_value = f"{int(dns['latency_ms'])} ms" if dns.get("latency_ms") is not None else ("Failing" if dns.get("success") is False else "Unknown")
        return {
            "Network": network_value,
            "Wi-Fi": wifi_value,
            "Gateway": gateway_value,
            "DNS": dns_value,
            "CPU": f"{cpu['usage_percent']:.0f}%",
            "Memory": f"{memory['available_percent']:.0f}% free",
            "Disk": f"{disk['used_percent']:.0f}% used",
        }

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
        connected = bool(gateway or (nmcli_state and "connected" in nmcli_state))

        wifi_device = None
        wifi_ssid = None
        wifi_signal_percent = None
        wifi_signal_dbm = None
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

        gateway_reachable = None
        gateway_ping_ms = None
        if gateway and shutil.which("ping"):
            ping_output = self._command(["ping", "-c", "1", "-W", "1", gateway], timeout=3)
            gateway_reachable = ping_output is not None and "1 received" in ping_output
            if ping_output:
                latency_match = re.search(r"time=([0-9.]+) ms", ping_output)
                if latency_match:
                    gateway_ping_ms = float(latency_match.group(1))

        return {
            "connected": connected,
            "gateway": gateway,
            "gateway_reachable": gateway_reachable,
            "gateway_ping_ms": gateway_ping_ms,
            "active_interface": active_interface,
            "nmcli_state": nmcli_state.strip() if nmcli_state else None,
            "wifi_device": wifi_device,
            "wifi_ssid": wifi_ssid,
            "wifi_signal_percent": wifi_signal_percent,
            "wifi_signal_dbm": wifi_signal_dbm,
        }

    def _dns_state(self) -> dict[str, Any]:
        resolver = self._system_resolver()
        host = "example.com"
        started = time.perf_counter()
        try:
            socket.setdefaulttimeout(2.5)
            socket.getaddrinfo(host, 443, proto=socket.IPPROTO_TCP)
            latency_ms = (time.perf_counter() - started) * 1000
            return {
                "success": True,
                "latency_ms": latency_ms,
                "resolver": resolver,
                "probe_host": host,
            }
        except OSError as error:
            return {
                "success": False,
                "latency_ms": None,
                "resolver": resolver,
                "probe_host": host,
                "error": str(error),
            }

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
