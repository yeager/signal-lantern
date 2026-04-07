from __future__ import annotations

import gettext
import locale
import os
import sys
from dataclasses import dataclass
from pathlib import Path

DOMAIN = "signal-lantern"


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _locale_search_paths() -> list[Path]:
    paths: list[Path] = []
    env_dir = os.environ.get("SIGNAL_LANTERN_LOCALE_DIR")
    if env_dir:
        paths.append(Path(env_dir))
    root = _project_root()
    paths.extend(
        [
            root / "locale",
            root / "share" / "locale",
            Path(sys.prefix) / "share" / "locale",
        ]
    )
    seen: set[str] = set()
    unique: list[Path] = []
    for path in paths:
        key = str(path)
        if key not in seen:
            seen.add(key)
            unique.append(path)
    return unique


@dataclass
class I18n:
    language: str
    translator: gettext.NullTranslations

    def gettext(self, text: str) -> str:
        return self.translator.gettext(text)


def detect_language() -> str:
    lang = locale.getlocale()[0] or locale.getdefaultlocale()[0]
    return lang or "en"


def get_i18n(language: str | None = None) -> I18n:
    chosen = language or detect_language()
    for localedir in _locale_search_paths():
        try:
            translator = gettext.translation(DOMAIN, localedir=str(localedir), languages=[chosen], fallback=False)
            return I18n(chosen, translator)
        except FileNotFoundError:
            continue
    return I18n(chosen, gettext.NullTranslations())

