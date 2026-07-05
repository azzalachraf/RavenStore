from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

SUPPORTED_LOCALES = {"en", "ar"}
DEFAULT_LOCALE = "en"


class I18n:
    def __init__(self, locale_dir: Path | None = None):
        self.locale_dir = locale_dir or Path(__file__).resolve().parent / "locales"

    @lru_cache(maxsize=8)
    def catalog(self, locale: str) -> dict[str, str]:
        normalized = locale if locale in SUPPORTED_LOCALES else DEFAULT_LOCALE
        path = self.locale_dir / f"{normalized}.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def t(
        self,
        key: str,
        locale: str = DEFAULT_LOCALE,
        remote_catalog: dict[str, str] | None = None,
        **params: Any,
    ) -> str:
        normalized = locale if locale in SUPPORTED_LOCALES else DEFAULT_LOCALE
        template = (
            (remote_catalog or {}).get(key)
            or self.catalog(normalized).get(key)
            or self.catalog(DEFAULT_LOCALE).get(key)
            or key
        )
        return template.format(**params)

    def direction(self, locale: str) -> str:
        return "rtl" if locale == "ar" else "ltr"


i18n = I18n()
