"""Retry and idempotency helpers for external operations."""

from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Callable, TypeVar


T = TypeVar("T")


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 3
    base_delay_seconds: float = 0.0
    retryable_exceptions: tuple[type[BaseException], ...] = (TimeoutError, ConnectionError)

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        if self.base_delay_seconds < 0:
            raise ValueError("base_delay_seconds cannot be negative")


def call_with_retry(function: Callable[[], T], policy: RetryPolicy, *, sleep: Callable[[float], None] = time.sleep) -> T:
    """Retry only configured transient failures; surface permanent failures."""

    for attempt in range(policy.max_attempts):
        try:
            return function()
        except policy.retryable_exceptions:
            if attempt == policy.max_attempts - 1:
                raise
            delay = policy.base_delay_seconds * (2**attempt)
            if delay:
                sleep(delay)
    raise RuntimeError("retry loop exited unexpectedly")


class IdempotencyLedger:
    """In-memory idempotency guard; production storage can replace the backend."""

    def __init__(self):
        self._completed: set[str] = set()

    def has_completed(self, operation_key: str) -> bool:
        return operation_key in self._completed

    def mark_completed(self, operation_key: str) -> bool:
        if operation_key in self._completed:
            return False
        self._completed.add(operation_key)
        return True

