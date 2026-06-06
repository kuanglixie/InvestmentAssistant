"""Simple rate limiter for polite fixed-basket collection."""

from __future__ import annotations

import time


class RateLimiter:
    def __init__(self, min_delay_seconds: float) -> None:
        self.min_delay_seconds = max(0.0, min_delay_seconds)
        self._last_call: float | None = None

    def wait(self) -> None:
        if self._last_call is None:
            self._last_call = time.monotonic()
            return
        elapsed = time.monotonic() - self._last_call
        if elapsed < self.min_delay_seconds:
            time.sleep(self.min_delay_seconds - elapsed)
        self._last_call = time.monotonic()
