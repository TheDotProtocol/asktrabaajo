"""Platform infrastructure records — Phase 9.

- ``PlatformEvent``        — the canonical realtime event log. Domain
  services emit MINIMAL, whitelisted events (type + resource reference +
  timestamps), never full records and never message bodies or private Work
  ID data. Delivery is per-user (``recipient_user_id``) or
  organization-scoped (``organization_id`` + ``org_scope``: visible to that
  org's members only). A future WebSocket/SSE transport reads this same
  table; polling is the Phase 9 transport.
- ``RateLimitHit``         — the distributed-safe store backend for the
  rate-limiting policy layer. Application code keeps using the in-process
  limiter; deployments that run multiple instances switch
  ``RATE_LIMIT_STORE=db`` and this table becomes the shared counter.
- ``NotificationPreference`` — per-user opt-in for out-of-band channels
  (email/push/sms). In-app is always on; no channel is assumed configured.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    JSON,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from app.db.base import Base
from app.models.enums import NOTIFICATION_CHANNEL_IN_APP

UUID = Uuid


class PlatformEvent(Base):
    """Append-only realtime event log (minimal, authorization-safe payloads)."""

    __tablename__ = "platform_events"
    __table_args__ = (
        Index("ix_platform_events_recipient_created", "recipient_user_id", "created_at"),
        Index("ix_platform_events_org_created", "organization_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    event_type: Mapped[str] = mapped_column(String(60), nullable=False)
    recipient_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    organization_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID, ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    # True: every member of ``organization_id`` may read this event.
    org_scope: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    resource_type: Mapped[str] = mapped_column(String(60), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(64), nullable=False)
    actor_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID, ForeignKey("users.id", ondelete="SET NULL")
    )
    # Whitelisted, minimal metadata only (never bodies / private records).
    payload: Mapped[Optional[dict]] = mapped_column(JSON)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class RateLimitHit(Base):
    """One hit against a rate-limit policy (DB-backed store backend)."""

    __tablename__ = "rate_limit_hits"
    __table_args__ = (
        Index("ix_rate_limit_hits_scope_key_hit", "scope", "key", "hit_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    scope: Mapped[str] = mapped_column(String(60), nullable=False)
    key: Mapped[str] = mapped_column(String(160), nullable=False)
    hit_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class NotificationPreference(Base):
    """Per-user opt-in for a notification channel."""

    __tablename__ = "notification_preferences"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    channel: Mapped[str] = mapped_column(
        String(20), primary_key=True, default=NOTIFICATION_CHANNEL_IN_APP
    )
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )