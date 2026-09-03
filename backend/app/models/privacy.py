"""Consent + privacy foundations.

``Consent`` answers WHO gave consent, TO WHOM (user or organization), TO
ACCESS WHAT (resource scope), FOR WHAT PURPOSE, WHEN, UNTIL WHEN, and WAS IT
REVOKED — in one reusable, person-owned record.

``PersonVisibilitySetting`` records the person's chosen visibility per Work
ID section (private / public / authorized_only). Default is private: the
Work ID is never a public dump of personal information.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    DateTime,
    ForeignKey,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from app.db.base import Base
from app.models.enums import VISIBILITY_PRIVATE

UUID = Uuid


class Consent(Base):
    __tablename__ = "consents"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    person_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("person_profiles.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    # To whom: a user OR every member of an organization.
    grantee_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID, ForeignKey("users.id", ondelete="CASCADE")
    )
    grantee_organization_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        index=True,
    )
    # What: a resource scope from CONSENT_SCOPES (e.g. work_id:documents).
    resource_scope: Mapped[str] = mapped_column(String(120), nullable=False)
    purpose: Mapped[Optional[str]] = mapped_column(String(240))
    granted_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID, ForeignKey("users.id", ondelete="SET NULL")
    )
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    revoked_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID, ForeignKey("users.id", ondelete="SET NULL")
    )


class PersonVisibilitySetting(Base):
    __tablename__ = "person_visibility_settings"

    person_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("person_profiles.id", ondelete="CASCADE"),
        primary_key=True,
    )
    scope: Mapped[str] = mapped_column(String(80), primary_key=True)
    visibility: Mapped[str] = mapped_column(
        String(20), default=VISIBILITY_PRIVATE, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
