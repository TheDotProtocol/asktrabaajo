"""In-process sliding-window rate limiting.

Production deployments needing shared, multi-process limits should back this
with Redis (Phase 6 realtime/infra); the interface stays the same. The
limiter is memory-safe: expired windows are evicted lazily and a hard cap
bounds dictionary growth.
"""
from __future__ import annotations

import threading
import time
from typing import Callable, Dict, Tuple

from fastapi import Request

from app.core import context
from app.core.errors import AppError

MAX_BUCKETS = 100_000


class RateLimitExceeded(AppError):
    status_code = 429
    code = "rate_limited"

    def __init__(self, retry_after_seconds: int) -> None:
        super().__init__(
            "Too many requests. Please try again later.",
            status_code=429,
            code="rate_limited",
            details={"retry_after_seconds": retry_after_seconds},
        )


class RateLimiter:
    """Fixed-window-with-float-boundaries limiter keyed by a string."""

    def __init__(self, max_requests: int, window_seconds: float = 60.0) -> None:
        self.max_requests = max(1, max_requests)
        self.window_seconds = max(1.0, window_seconds)
        self._buckets: Dict[str, Tuple[float, int]] = {}
        self._lock = threading.Lock()

    def _evict(self, now: float) -> None:
        stale = [
            key
            for key, (started, _) in self._buckets.items()
            if now - started >= self.window_seconds
        ]
        for key in stale:
            del self._buckets[key]

    def allow(self, key: str) -> Tuple[bool, int]:
        """Returns (allowed, retry_after_seconds)."""
        now = time.monotonic()
        with self._lock:
            if len(self._buckets) > MAX_BUCKETS:
                self._evict(now)
            started, count = self._buckets.get(key, (now, 0))
            if now - started >= self.window_seconds:
                started, count = now, 0
            if count >= self.max_requests:
                retry_after = int(self.window_seconds - (now - started)) + 1
                return False, retry_after
            self._buckets[key] = (started, count + 1)
            return True, 0

    def check(self, key: str) -> None:
        allowed, retry_after = self.allow(key)
        if not allowed:
            raise RateLimitExceeded(retry_after)


def rate_limit_dependency(
    name: str, *, max_requests: int, window_seconds: float = 60.0
) -> Callable:
    """Build a FastAPI dependency that rate-limits per client IP.

    Limiters live on ``app.state.rate_limiters`` (created in ``main.py``), so
    each app instance has its own counters (test isolation included).
    """

    def dependency(request: Request) -> None:
        limiters = getattr(request.app.state, "rate_limiters", None)
        if not limiters:
            return
        limiter = limiters.get(name)
        if limiter is None:
            return
        meta = context.request_meta()
        client_ip = meta.get("ip_address") or (
            request.client.host if request.client else "unknown"
        )
        limiter.check(f"{name}:{client_ip}")

    return dependency
