from __future__ import annotations

from raven_bot.api.client import RavenAPI
from raven_bot.i18n import I18n


def test_translation_falls_back_to_english_and_escapes_unknown_locale() -> None:
    i18n = I18n()

    assert i18n.t("home.title", "unsupported") == i18n.t("home.title", "en")
    assert i18n.direction("ar") == "rtl"
    assert i18n.direction("en") == "ltr"


async def test_catalog_events_only_invalidate_presentation_cache() -> None:
    client = RavenAPI()
    client._translation_cache["en"] = (0, {"home.title": "Cached"})

    client._apply_invalidation(
        {"event_id": "event-1", "event_type": "translation.updated", "cache_tags": ["translations"], "payload": {"language_code": "en"}}
    )

    assert "en" not in client._translation_cache
    await client.close()
