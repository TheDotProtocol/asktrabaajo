"""Organization / tenancy + RBAC foundation.

One user may belong to many organizations. A membership grants the user a
role inside that organization; the role's permissions are defined by the
``role_permissions`` catalog. ``SUPER_ADMIN`` is a platform-scope role that
can only be granted through a membership in a platform-kind organization —
company HR/recruiter memberships can never reach it.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from app.db.base import Base
from app.models.enums import ORG_KIND_EMPLOYER, ORG_STATUS_ACTIVE
from app.models.identity import TimestampMixin

# Role scopes
ROLE_SCOPE_PLATFORM = "platform"
ROLE_SCOPE_ORGANIZATION = "organization"
ROLE_SCOPE_GOVERNMENT = "government"

ROLE_SUPER_ADMIN = "super_admin"


class Organization(Base, TimestampMixin):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(
        String(120), unique=True, index=True, nullable=False
    )
    kind: Mapped[str] = mapped_column(
        String(20), default=ORG_KIND_EMPLOYER, nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(20), default=ORG_STATUS_ACTIVE, nullable=False
    )
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL")
    )


class Role(Base):
    __tablename__ = "roles"

    code: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    scope: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # platform|organization|government
    description: Mapped[Optional[str]] = mapped_column(Text)


class Permission(Base):
    __tablename__ = "permissions"

    code: Mapped[str] = mapped_column(String(100), primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)


class RolePermission(Base):
    __tablename__ = "role_permissions"

    role_code: Mapped[str] = mapped_column(
        String(50), ForeignKey("roles.code", ondelete="CASCADE"), primary_key=True
    )
    permission_code: Mapped[str] = mapped_column(
        String(100),
        ForeignKey("permissions.code", ondelete="CASCADE"),
        primary_key=True,
    )


class Membership(Base):
    __tablename__ = "memberships"
    __table_args__ = (
        UniqueConstraint("user_id", "organization_id", name="uq_memberships_user_org"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    role_code: Mapped[str] = mapped_column(
        String(50), ForeignKey("roles.code"), nullable=False
    )
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
