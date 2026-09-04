"""Athena — controlled AI orchestration domain (Phase 14).

Athena never holds authorization; it holds tools. These tables persist
the orchestration envelope only:

- ``athena_sessions`` — who, in which mode, against which org context.
- ``athena_messages`` — sanitized conversation text + validated tool
  call envelopes (never documents, KYC, or credentials content).
- ``athena_action_confirmations`` — explicit human confirmation records
  for high-risk tool actions (requested action + scope + expiry + actor).
- ``ai_usage_log`` — provider usage metrics (tokens/cost/latency/model)
  with no provider secrets and no prompt content.

Sensitive fields (passports, government/tax IDs, KYC, private contact
details, document contents) are EXCLUDED by the context builder and never
reach these tables. Retention: messages/confirmations are governed by the
``ai_message_retention_days`` / ``athena_confirmation_ttl_minutes``
settings; a purge job is a later operational concern (documented).
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON, Uuid

from app.db.base import Base
from app.models.enums import (
    ATHENA_MODE_JOBSEEKER,
    ATHENA_MESSAGE_ROLE_USER,
    ATHENA_RISK_READ_ONLY,
    ATHENA_SESSION_STATUS_ACTIVE,
)


class AthenaSession(Base):
    """A scoped Athena conversation for one user in one mode."""

    __tablename__ = "athena_sessions"
    __table_args__ = (
        Index("ix_athena_sessions_user_created", "user_id", "created_at"),
        Index("ix_athena_sessions_org_created", "organization_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    organization_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("organizations.id", ondelete="SET NULL")
    )
    mode: Mapped[str] = mapped_column(
        String(24), default=ATHENA_MODE_JOBSEEKER, nullable=False
    )
    purpose: Mapped[Optional[str]] = mapped_column(String(240))
    status: Mapped[str] = mapped_column(
        String(20), default=ATHENA_SESSION_STATUS_ACTIVE, nullable=False
    )
    correlation_id: Mapped[Optional[str]] = mapped_column(String(40))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_active_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class AthenaMessage(Base):
    """One sanitized turn in an Athena session.

    ``content`` holds only the user/assistant text. ``tool_calls`` holds
    the validated structured tool-call envelope (name + canonical
    arguments + status) — never free-form model code, never documents.
    """

    __tablename__ = "athena_messages"
    __table_args__ = (
        Index("ix_athena_messages_session_created", "session_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("athena_sessions.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(
        String(16), default=ATHENA_MESSAGE_ROLE_USER, nullable=False
    )
    content: Mapped[Optional[str]] = mapped_column(Text)
    tool_calls: Mapped[Optional[list]] = mapped_column(JSON)
    provider_model: Mapped[Optional[str]] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class AthenaActionConfirmation(Base):
    """Explicit human confirmation for a high-risk Athena tool action.

    The model can propose; only an approved, unexpired confirmation for
    the EXACT canonical scope (``scope_hash``) authorizes execution.
    Never created from natural-language interpretation alone.
    """

    __tablename__ = "athena_action_confirmations"
    __table_args__ = (
        Index("ix_athena_confirmations_user_status", "user_id", "status"),
        Index("ix_athena_confirmations_session", "session_id"),
        UniqueConstraint(
            "session_id",
            "tool_name",
            "scope_hash",
            "status",
            name="uq_athena_confirmation_scope",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("athena_sessions.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    organization_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("organizations.id", ondelete="SET NULL")
    )
    tool_name: Mapped[str] = mapped_column(String(80), nullable=False)
    action_summary: Mapped[Optional[str]] = mapped_column(String(300))
    scope: Mapped[dict] = mapped_column(JSON, nullable=False)
    scope_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    risk_level: Mapped[str] = mapped_column(
        String(24), default=ATHENA_RISK_READ_ONLY, nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    authorization_source: Mapped[str] = mapped_column(
        String(40), default="user_confirmation", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    decided_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    decided_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL")
    )
    result: Mapped[Optional[dict]] = mapped_column(JSON)


class AiUsageLog(Base):
    """Provider usage metrics — no secrets, no prompts, no documents."""

    __tablename__ = "ai_usage_log"
    __table_args__ = (
        Index("ix_ai_usage_user_created", "user_id", "created_at"),
        Index("ix_ai_usage_org_created", "organization_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL")
    )
    organization_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("organizations.id", ondelete="SET NULL")
    )
    session_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("athena_sessions.id", ondelete="SET NULL")
    )
    mode: Mapped[Optional[str]] = mapped_column(String(24))
    feature: Mapped[str] = mapped_column(String(80), nullable=False)
    provider: Mapped[Optional[str]] = mapped_column(String(40))
    model: Mapped[Optional[str]] = mapped_column(String(80))
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    estimated_cost: Mapped[Optional[float]] = mapped_column(Float)
    latency_ms: Mapped[Optional[int]] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="success", nullable=False)
    error_code: Mapped[Optional[str]] = mapped_column(String(60))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )