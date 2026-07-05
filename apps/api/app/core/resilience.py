from __future__ import annotations

import asyncio
import random
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from time import monotonic
from typing import TypeVar

from app.core.config import settings

T = TypeVar("T")


class CircuitOpenError(RuntimeError):
    pass


@dataclass
class CircuitBreaker:
    failure_threshold: int = settings.circuit_breaker_failure_threshold
    recovery_seconds: int = settings.circuit_breaker_recovery_seconds
    failures: int = 0
    opened_at: float | None = None

    async def call(self, operation: Callable[[], Awaitable[T]]) -> T:
        now = monotonic()
        if self.opened_at is not None and now - self.opened_at < self.recovery_seconds:
            raise CircuitOpenError("resilience.circuit_open")
        if self.opened_at is not None:
            self.opened_at = None
            self.failures = 0
        try:
            result = await operation()
        except Exception:
            self.failures += 1
            if self.failures >= self.failure_threshold:
                self.opened_at = monotonic()
            raise
        self.failures = 0
        return result


_breakers: dict[str, CircuitBreaker] = {}


async def call_with_resilience(
    service: str,
    operation: Callable[[], Awaitable[T]],
    *,
    attempts: int = 3,
    retryable: Callable[[Exception], bool] | None = None,
) -> T:
    breaker = _breakers.setdefault(service, CircuitBreaker())
    for attempt in range(1, attempts + 1):
        try:
            return await breaker.call(operation)
        except CircuitOpenError:
            raise
        except Exception as exc:
            if attempt >= attempts or (retryable is not None and not retryable(exc)):
                raise
            await asyncio.sleep(min(5.0, 0.2 * (2 ** (attempt - 1))) + random.uniform(0, 0.2))
    raise RuntimeError("resilience.retry_exhausted")
