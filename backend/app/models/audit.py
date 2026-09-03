"""Append-only audit log.

No UPDATE/DELETE is ever issued against this table by application code.
Every important action records: actor, action, resource, tenant,
request metadata, and result. Future phases may add batch hash-chaining.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON, Uuid

from app.db.base import Base
from app.models.enums import AUDIT_RESULT_SUCCESS


class AuditLogEntry(Base):
    __tablename__ = "audit_log"
    __table_args__ = (
        Index("ix_audit_log_actor_created", "actor_id", "created_at"),
        Index("ix_audit_log_action_created", "action", "created_at"),
        Index("ix_audit_log_resource", "resource_type", "resource_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    actor_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    resource_type: Mapped[Optional[str]] = mapped_column(String(80))
    resource_id: Mapped[Optional[str]] = mapped_column(String(64))
    organization_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("organizations.id", ondelete="SET NULL")
    )
    result: Mapped[str] = mapped_column(
        String(20), default=AUDIT_RESULT_SUCCESS, nullable=False
    )
    request_id: Mapped[Optional[str]] = mapped_column(String(40))
    ip_address: Mapped[Optional[str]] = mapped_column(String(64))
    user_agent: Mapped[Optional[str]] = mapped_column(String(255))
    payload: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
