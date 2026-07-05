from __future__ import annotations

import secrets
import time
from dataclasses import dataclass


@dataclass
class NavigationValue:
    value: str
    expires_at: float


class NavigationCache:
    def __init__(self, ttl_seconds: int = 900):
        self.ttl_seconds = ttl_seconds
        self._values: dict[str, NavigationValue] = {}

    def put(self, value: str) -> str:
        self._cleanup()
        token = secrets.token_urlsafe(6)
        self._values[token] = NavigationValue(value=value, expires_at=time.time() + self.ttl_seconds)
        return token

    def get(self, token: str) -> str | None:
        item = self._values.get(token)
        if not item or item.expires_at < time.time():
            self._values.pop(token, None)
            return None
        return item.value

    def _cleanup(self) -> None:
        now = time.time()
        expired = [key for key, item in self._values.items() if item.expires_at < now]
        for key in expired:
            self._values.pop(key, None)


navigation_cache = NavigationCache()

