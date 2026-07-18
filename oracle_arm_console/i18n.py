"""File-based i18n for A1 Control.

Add a language by creating ``oracle_arm_console/locales/<code>.json``
(copy ``en.json`` and translate). Restart the process; the language menu
lists installed files automatically.

Selection order:
1. ``?lang=`` query (also written to cookie)
2. ``lang`` cookie
3. ``Accept-Language`` first match against an installed locale
4. Default: English
"""

from __future__ import annotations

import json
import re
from contextvars import ContextVar
from functools import lru_cache
from pathlib import Path

LOCALES_DIR = Path(__file__).resolve().parent / "locales"
DEFAULT_LOCALE = "en"
CHINESE_LOCALE = "zh"
LANG_RE = re.compile(r"^[a-z]{2}(?:-[A-Za-z0-9]+)?$")
LOCALE_COOKIE = "lang"

_current_locale: ContextVar[str] = ContextVar("locale", default=DEFAULT_LOCALE)


def _deep_get(data: dict, dotted: str):
    node = data
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


@lru_cache(maxsize=1)
def available_locales() -> tuple[str, ...]:
    if not LOCALES_DIR.is_dir():
        return (DEFAULT_LOCALE,)
    codes = sorted(path.stem for path in LOCALES_DIR.glob("*.json") if path.is_file())
    return tuple(codes) or (DEFAULT_LOCALE,)


@lru_cache(maxsize=32)
def load_locale(code: str) -> dict:
    path = LOCALES_DIR / f"{code}.json"
    if not path.is_file():
        if code == DEFAULT_LOCALE:
            return {}
        return load_locale(DEFAULT_LOCALE)
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def clear_locale_cache() -> None:
    available_locales.cache_clear()
    load_locale.cache_clear()


def get_locale() -> str:
    return _current_locale.get()


def set_locale(code: str):
    return _current_locale.set(code or DEFAULT_LOCALE)


def reset_locale(token) -> None:
    _current_locale.reset(token)


def normalize_locale(code: str | None) -> str | None:
    if not code:
        return None
    code = code.strip().replace("_", "-")
    if not LANG_RE.fullmatch(code):
        return None
    primary = code.split("-", 1)[0].lower()
    available = set(available_locales())
    if primary in available:
        return primary
    lowered = code.lower()
    if lowered in available:
        return lowered
    if primary == "zh" and CHINESE_LOCALE in available:
        return CHINESE_LOCALE
    return None


def parse_accept_language(header: str | None) -> str:
    if not header:
        return DEFAULT_LOCALE
    candidates: list[tuple[float, str]] = []
    for part in header.split(","):
        piece = part.strip()
        if not piece:
            continue
        if ";q=" in piece:
            tag, q_raw = piece.split(";q=", 1)
            try:
                quality = float(q_raw)
            except ValueError:
                quality = 0.0
        else:
            tag, quality = piece, 1.0
        tag = tag.strip()
        if tag == "*" or quality <= 0:
            continue
        candidates.append((quality, tag))
    candidates.sort(key=lambda item: item[0], reverse=True)
    for _, tag in candidates:
        resolved = normalize_locale(tag)
        if resolved:
            return resolved
    return DEFAULT_LOCALE


def resolve_locale(explicit: str | None = None, accept_language: str | None = None) -> str:
    preferred = normalize_locale(explicit)
    if preferred:
        return preferred
    return parse_accept_language(accept_language)


def translate(key: str, locale: str | None = None, **kwargs) -> str:
    code = locale or get_locale()
    catalog = load_locale(code)
    value = _deep_get(catalog, key)
    if value is None and code != DEFAULT_LOCALE:
        value = _deep_get(load_locale(DEFAULT_LOCALE), key)
    if value is None:
        value = key
    if kwargs and isinstance(value, str):
        try:
            return value.format(**kwargs)
        except (KeyError, ValueError):
            return value
    return value if isinstance(value, str) else str(value)


def t(key: str, **kwargs) -> str:
    """Translate using the active request locale."""
    return translate(key, **kwargs)


def html_lang(locale: str | None = None) -> str:
    code = locale or get_locale()
    value = _deep_get(load_locale(code), "meta.html_lang")
    return value if isinstance(value, str) else code


def section(name: str, locale: str | None = None) -> dict:
    code = locale or get_locale()
    catalog = load_locale(code)
    data = catalog.get(name) if isinstance(catalog, dict) else None
    if not isinstance(data, dict):
        fallback = load_locale(DEFAULT_LOCALE).get(name, {})
        return dict(fallback) if isinstance(fallback, dict) else {}
    if code != DEFAULT_LOCALE:
        base = load_locale(DEFAULT_LOCALE).get(name, {})
        if isinstance(base, dict):
            merged = dict(base)
            merged.update(data)
            return merged
    return dict(data)


def locale_choices() -> list[dict]:
    choices = []
    for code in available_locales():
        name = _deep_get(load_locale(code), "meta.name") or code
        choices.append({"code": code, "name": name})
    choices.sort(key=lambda item: (item["code"] != DEFAULT_LOCALE, item["code"]))
    return choices
