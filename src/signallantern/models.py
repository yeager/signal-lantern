from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Severity(str, Enum):
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class Issue:
    key: str
    severity: Severity
    title: str
    meaning: str
    suggestions: list[str]
    details: dict[str, Any] = field(default_factory=dict)
    source: str = ""
    action: str | None = None
    notification_body: str | None = None


@dataclass
class Snapshot:
    issues: list[Issue]
    status_line: str
    checked_at: str
    metrics: dict[str, str]
    raw: dict[str, Any] = field(default_factory=dict)
