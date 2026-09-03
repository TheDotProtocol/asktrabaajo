"""Distributed-safe rate-limit store (Phase 9).

The in-process ``RateLimiter`` is the development/test implementation. For a
multi-instance deployment the same policy layer can be backed by this
store, which counts hits in the shared ``rate_limit_hits`` table (no
external infrastructure). Redis remains the preferred production backend
when available; both implement the same ``check`` contract so the policy
layer never changes.

This store is exercised by the test suite against the isolated database;
deployments choose it with ``RATE_LIMIT_STORE=db``. Expired hits are
cleaned lazily on each check.
"""
from __future__ import annotations

from datetime import timedelta
from typing import Tuple

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.timeutil import utc_now_naive
from app.models.platform import RateLimitHit


class DbRateLimitStore:
    """Sliding-window store over ``rate_limit_hits`` (multi-instance safe)."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def allow(
        self, scope: str, key: str, max_requests: int, window_seconds: float
    ) -> Tuple[bool, int]:
        """Returns (allowed, retry_after_seconds) for one hit."""
        window_start = utc_now_naive() - timedelta(seconds=window_seconds)
        # Lazy cleanup of expired hits for this scope+key (bounded work).
        self.db.execute(
            delete(RateLimitHit).where(
                RateLimitHit.scope == scope,
                RateLimitHit.key == key,
                RateLimitHit.hit_at < window_start,
            )
        )
        count = self.db.scalar(
            select(func.count())
            .select_from(RateLimitHit)
            .where(
                RateLimitHit.scope == scope,
                RateLimitHit.key == key,
                RateLimitHit.hit_at >= window_start,
            )
        ) or 0
        if count >= max_requests:
            oldest = self.db.scalar(
                select(RateLimitHit.hit_at)
                .where(
                    RateLimitHit.scope == scope,
                    RateLimitHit.key == key,
                    RateLimitHit.hit_at >= window_start,
                )
                .order_by(RateLimitHit.hit_at.asc())
                .limit(1)
            )
            retry_after = 1
            if oldest is not None:
                retry_after = int(
                    window_seconds - (utc_now_naive() - oldest).total_seconds()
                ) + 1
            self.db.commit()
            return False, max(1, retry_after)
        self.db.add(RateLimitHit(scope=scope, key=key))
        self.db.commit()
        return True, 0

    def check(self, scope: str, key: str, max_requests: int, window_seconds: float) -> None:
        from app.core.ratelimit import RateLimitExceeded

        allowed, retry_after = self.allow(scope, key, max_requests, window_seconds)
        if not allowed:
            raise RateLimitExceeded(retry_after)