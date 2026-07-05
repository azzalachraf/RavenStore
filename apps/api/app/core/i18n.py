from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

SUPPORTED_LOCALES = {"en", "ar"}
DEFAULT_LOCALE = "en"


@lru_cache
def load_translations(locale: str) -> dict[str, str]:
    normalized = locale if locale in SUPPORTED_LOCALES else DEFAULT_LOCALE
    path = Path(__file__).resolve().parents[1] / "locales" / f"{normalized}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def translate(key: str, locale: str = DEFAULT_LOCALE, **params: object) -> str:
    catalog = load_translations(locale)
    fallback = load_translations(DEFAULT_LOCALE)
    template = catalog.get(key) or fallback.get(key) or key
    return template.format(**params)

