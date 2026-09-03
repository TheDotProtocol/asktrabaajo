"""Moderator Enforcement + Appeals (Phase 11).

Architectural principle: A governance CASE is not an enforcement action.

Report -> Case -> Investigation -> Decision -> ENFORCEMENT ACTION -> Audit
-> Appeal (if eligible) -> Appeal decision -> Final resolution.

- ``EnforcementAction`` is an explicit, granular, audited action against a
  target user and/or organization, tied to a governance case. It is NEVER a
  generic "admin can do anything" record: action type + scope + reason code +
  lifecycle are controlled values, and severe actions require an approval
  separation (creator != approver).
- Enforcement is derived-state, scheduler-free: a stored ``active`` action is
  only in effect while ``effective_at <= now < expires_at`` (or no expiry).
  Expiry therefore holds even if no background worker has flipped the row.
- ``Appeal`` lets an eligible enforcement target contest an action. Decisions
  never silently mutate the original action: an accepted/partial appeal creates
  a NEW superseding action (e.g. reinstatement) through the same audited
  lifecycle, and the handler revokes the original with an explicit note.

Reason codes are controlled; free-form sensitive narratives never enter
generic audit/event payloads. Only bounded, sanitized notes are stored here.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from app.db.base import Base
from app.models.enums import (
    APPEAL_STATUS_SUBMITTED,
    ENFORCEMENT_REASON_OTHER,
    ENFORCEMENT_STATUS_PROPOSED,
)
from app.models.identity import TimestampMixin

UUID = Uuid


class EnforcementAction(Base, TimestampMixin):
    """One explicit enforcement action against a target, tied to a case."""

    __tablename__ = "enforcement_actions"
    __table_args__ = (
        Index("ix_enforcement_actions_target_user", "target_user_id", "status"),
        Index(
            "ix_enforcement_actions_target_org", "target_organization_id", "status"
        ),
        Index("ix_enforcement_actions_case", "governance_case_id"),
        Index("ix_enforcement_actions_scope_type", "scope", "action_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    governance_case_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID,
        ForeignKey("governance_reports.id", ondelete="SET NULL"),
        index=True,
    )
    # Target: a user and/or an organization (scope decides which is relevant).
    target_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    target_organization_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID, ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    action_type: Mapped[str] = mapped_column(String(40), nullable=False)
    scope: Mapped[str] = mapped_column(String(40), nullable=False)
    # Controlled reason code + bounded sanitized note (never a raw body).
    reason_code: Mapped[str] = mapped_column(
        String(40), default=ENFORCEMENT_REASON_OTHER, nullable=False
    )
    note: Mapped[Optional[str]] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(
        String(20), default=ENFORCEMENT_STATUS_PROPOSED, nullable=False
    )
    # Lifecycle actors (creator != approver for approval-required types).
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID, ForeignKey("users.id", ondelete="SET NULL")
    )
    approval_note: Mapped[Optional[str]] = mapped_column(String(500))
    rejected_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID, ForeignKey("users.id", ondelete="SET NULL")
    )
    rejection_note: Mapped[Optional[str]] = mapped_column(String(500))
    revoked_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID, ForeignKey("users.id", ondelete="SET NULL")
    )
    revoke_note: Mapped[Optional[str]] = mapped_column(String(500))
    # Deterministic window. Correctness never depends on a scheduler.
    effective_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    activated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    # Supersession chain: a reinstatement/reduction created by an appeal
    # decision (or corrective action) points at the action it replaces.
    supersedes_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID, ForeignKey("enforcement_actions.id", ondelete="SET NULL")
    )


class Appeal(Base, TimestampMixin):
    """An enforcement target's appeal against one eligible action."""

    __tablename__ = "appeals"
    __table_args__ = (
        Index("ix_appeals_appellant", "appellant_user_id", "status"),
        Index("ix_appeals_reviewer", "assigned_reviewer_id", "status"),
        Index("ix_appeals_action", "enforcement_action_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    enforcement_action_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("enforcement_actions.id", ondelete="CASCADE"),
        nullable=False,
    )
    # The person filing (the target user, or an org admin for org actions).
    appellant_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    reason_code: Mapped[str] = mapped_column(
        String(40), default=ENFORCEMENT_REASON_OTHER, nullable=False
    )
    # The appellant's sanitized statement (bounded; no document/chat dumps).
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default=APPEAL_STATUS_SUBMITTED, nullable=False
    )
    assigned_reviewer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID, ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    # Reviewer-facing internal note — NEVER exposed to the appellant.
    review_note: Mapped[Optional[str]] = mapped_column(Text)
    decided_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID, ForeignKey("users.id", ondelete="SET NULL")
    )
    decision: Mapped[Optional[str]] = mapped_column(String(20))
    # Appellant-visible outcome summary (bounded; sanitized wording).
    decision_note: Mapped[Optional[str]] = mapped_column(String(1000))
    decided_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    withdrawn_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    # When a decision creates a superseding action (reinstatement/reduction).
    superseding_action_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID,
        ForeignKey("enforcement_actions.id", ondelete="SET NULL"),
        index=True,
    )
