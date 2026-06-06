"""Retry policy for transient fetch failures."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import TypeVar


T = TypeVar("T")


class RetryPolicy:
    def __init__(self, max_retries: int = 2, base_delay_seconds: float = 1.0) -> None:
        self.max_retries = max(0, max_retries)
        self.base_delay_seconds = max(0.0, base_delay_seconds)

    def run(self, fn: Callable[[], T]) -> T:
        last_exc: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                return fn()
            except Exception as exc:  # pragma: no cover - exercised by live fetches.
                last_exc = exc
                if attempt >= self.max_retries:
                    break
                time.sleep(self.base_delay_seconds * (2**attempt))
        assert last_exc is not None
        raise last_exc
