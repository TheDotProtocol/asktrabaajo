"""UTC time helpers.

Values stored in the canonical schema are UTC. SQLite returns naive
datetimes (it does not store timezone offsets), while PostgreSQL returns
timezone-aware datetimes for ``TIMESTAMPTZ`` columns. Application code must
therefore compare through these helpers so behavior is identical on both
dialects (tests run on SQLite; production runs on PostgreSQL).
"""
from __future__ import annotations

from datetime import datetime, timezone


def utc_now() -> datetime:
    """Aware UTC now."""
    return datetime.now(timezone.utc)


def utc_now_naive() -> datetime:
    """Naive UTC now — safe to compare against naive values from SQLite."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def to_utc_naive(value: datetime) -> datetime:
    """Normalize any datetime to naive UTC for storage/comparison."""
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)
