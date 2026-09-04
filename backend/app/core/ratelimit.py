"""Centralized rate-limiting policy layer (Phase 9 hardened).

One registry (``RATE_LIMIT_POLICIES``) defines every protected action and
its limits. Routes declare ``Depends(rate_limit("outreach.create"))`` — no
inline limits scattered across handlers. Keys are the authenticated user id
when present, otherwise the client IP (risk actions that run pre-auth are
IP-keyed).

The in-process ``RateLimiter`` remains the development/test implementation
(safe single-instance). A distributed multi-instance deployment must back
the same interface with Redis or the DB store (``RateLimitHit`` table +
``DbRateLimitStore``); the interface never changes. See
``services/ratelimit_store.py``.

Limits are configurable per action; ``settings.rate_limits_enabled=False``
disables enforcement (test harness). Responses are identical regardless of
the target — rate limiting never reveals whether an account exists.
"""
from __future__ import annotations

import threading
import time
from typing import Callable, Dict, Tuple

from fastapi import Request

from app.core import context
from app.core.errors import AppError

MAX_BUCKETS = 100_000

# (max_requests, window_seconds) per policy name.
RATE_LIMIT_POLICIES: Dict[str, Tuple[int, float]] = {
    # Authentication (pre-auth, IP-keyed) — strict.
    "login": (10, 60),
    "mfa_verify": (5, 60),
    "reset": (5, 60),  # forgot + reset password
    "register": (5, 3600),
    # Candidate-facing writes — user-keyed.
    "outreach.create": (30, 60),
    "message.send": (60, 60),
    "application.batch": (10, 60),
    "document.request": (15, 60),
    # Discovery — user-keyed (anti-scraping).
    "candidates.search": (60, 60),
    # Athena (Phase 14) — user-keyed; high-risk actions are the strictest.
    "athena.chat": (30, 60),
    "athena.tool": (40, 60),
    "athena.search": (30, 60),
    "athena.high_risk": (10, 3600),
    # AI Interview Engine (Phase 16) — candidate-side writes are bounded
    # so a compromised token cannot drive unbounded AI expenditure.
    "ai_interview.create": (20, 3600),
    "ai_interview.invite": (20, 3600),
    "ai_interview.respond": (40, 60),
    # Commerce / billing (Phase 17) — subscription state changes are
    # strictly bounded; org-keyed.
    "billing.change": (20, 3600),
    # Government intelligence (Wave 8) — aggregate queries and exports.
    "government.query": (60, 60),
    "government.export": (10, 3600),
}


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


def build_limiters() -> Dict[str, RateLimiter]:
    """One limiter per policy, from the registry (called by the app factory)."""
    return {
        name: RateLimiter(max_requests=max_r, window_seconds=window)
        for name, (max_r, window) in RATE_LIMIT_POLICIES.items()
    }


def _client_key(request: Request) -> str:
    meta = context.request_meta()
    # Authenticated actor wins (per-user limits); otherwise client IP.
    actor_id = meta.get("actor_id")
    if actor_id:
        return f"user:{actor_id}"
    client_ip = meta.get("ip_address") or (
        request.client.host if request.client else "unknown"
    )
    return f"ip:{client_ip}"


def rate_limit_dependency(
    name: str, *, max_requests: int | None = None, window_seconds: float | None = None
) -> Callable:
    """Build a FastAPI dependency enforcing the named policy.

    Limits come from the registry unless overridden (overrides are used by
    tests to exercise small windows). Enforcement is disabled when
    ``settings.rate_limits_enabled`` is False.
    """
    policy = RATE_LIMIT_POLICIES.get(name)
    if policy is None and max_requests is None:
        raise ValueError(f"No rate-limit policy named '{name}'.")
    policy_max, policy_window = policy or (0, 60)
    effective_max = max_requests if max_requests is not None else policy_max
    effective_window = window_seconds if window_seconds is not None else policy_window

    def dependency(request: Request) -> None:
        from app.core.config import get_settings

        if not get_settings().rate_limits_enabled:
            return
        limiters = getattr(request.app.state, "rate_limiters", None)
        if not limiters:
            return
        limiter = limiters.get(name)
        if limiter is None:
            # Build on demand so tests can inject a custom limiter by name.
            limiter = RateLimiter(
                max_requests=effective_max, window_seconds=effective_window
            )
            limiters[name] = limiter
        limiter.check(_client_key(request))

    return dependency