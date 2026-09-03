"""Identity foundation.

Conceptual separation (per the approved architecture):
- ``User``          = authentication / account identity (login, sessions)
- ``PersonProfile`` = human professional identity (the PERSON record)
- Work ID sections  = person-owned records (see ``app.models.work``)

A login account and a professional identity are deliberately NOT the same
record — one user owns exactly one person profile.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from app.db.base import Base
from app.models.enums import USER_STATUS_ACTIVE

UUID = Uuid


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(
        String(320), unique=True, index=True, nullable=False
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), default=USER_STATUS_ACTIVE, nullable=False
    )
    email_verified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True)
    )
    token_version: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class PersonProfile(Base, TimestampMixin):
    """The PERSON record — professional identity header (1:1 with User)."""

    __tablename__ = "person_profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    headline: Mapped[Optional[str]] = mapped_column(String(200))
    summary: Mapped[Optional[str]] = mapped_column(String(4000))
    location: Mapped[Optional[str]] = mapped_column(String(160))
    country_code: Mapped[Optional[str]] = mapped_column(String(8))
    date_of_birth: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    profile_photo_storage_key: Mapped[Optional[str]] = mapped_column(String(255))


class RefreshToken(Base):
    """Server-side refresh token records (opaque, stored hashed)."""

    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    token_hash: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    user_agent: Mapped[Optional[str]] = mapped_column(String(255))
    ip_address: Mapped[Optional[str]] = mapped_column(String(64))
