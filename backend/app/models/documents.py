"""Controlled document access foundation.

A document belongs to a person. Nothing is shared automatically — an
explicit, revocable grant (to a user or an organization) authorizes access.
Every access/download is audited (see ``app/services/audit``).
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from app.db.base import Base
from app.models.identity import TimestampMixin


class PersonDocument(Base, TimestampMixin):
    __tablename__ = "person_documents"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    person_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("person_profiles.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    doc_type: Mapped[str] = mapped_column(String(60), nullable=False)
    storage_key: Mapped[Optional[str]] = mapped_column(String(255))
    mime_type: Mapped[Optional[str]] = mapped_column(String(100))
    size_bytes: Mapped[Optional[int]] = mapped_column(Integer)
    is_archived: Mapped[bool] = mapped_column(default=False, nullable=False)
    verification_status: Mapped[str] = mapped_column(
        String(20), default="unverified", nullable=False
    )


class DocumentAccessGrant(Base):
    __tablename__ = "document_access_grants"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("person_documents.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    # Grant to a specific user OR to every member of an organization.
    grantee_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE")
    )
    grantee_organization_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("organizations.id", ondelete="CASCADE")
    )
    purpose: Mapped[Optional[str]] = mapped_column(String(240))
    granted_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL")
    )
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    revoked_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL")
    )
