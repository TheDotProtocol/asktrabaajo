"""Platform Governance — Phase 9.

AskTrabaajo is employment infrastructure, not just an HR app. This module is
the governance foundation that sits ABOVE the product domains:

- ``GovernanceReport``    — a structured report/complaint (abuse, fraud,
  impersonation, policy violation, communication dispute, document misuse,
  recruiter misconduct, suspicious activity, platform integrity, ...). The
  report REFERENCES platform objects (``target_type`` + ``target_id``) and
  ``evidence_refs`` holds {type, id} references only — private Work ID data
  and document contents are NEVER copied into governance payloads.
- ``GovernanceReportNote`` — internal moderator notes (least privilege:
  visible only to authorized governance roles, never to reporters).

Boundaries (explicit):
- Reports are platform-scope records. Employers, recruiters, candidates and
  government analysts can FILE a report but can never READ or MODIFY the
  queue (that requires a platform-scoped moderator/super-admin role).
- Governance reads reports + audit history, NOT private Work ID sections.
  Inspecting a person's private data remains a separate, permissioned,
  audited act — never a side effect of moderation.
- Government aggregate analytics stay separate from platform moderation data
  (aggregate-first, no individual surveillance).
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from app.db.base import Base
from app.models.enums import (
    REPORT_CATEGORY_OTHER,
    REPORT_SEVERITY_MEDIUM,
    REPORT_STATUS_OPEN,
)
from app.models.identity import TimestampMixin

UUID = Uuid


class GovernanceReport(Base, TimestampMixin):
    """A structured governance report filed by any authenticated user."""

    __tablename__ = "governance_reports"
    __table_args__ = (
        Index("ix_governance_reports_status_severity", "status", "severity"),
        Index("ix_governance_reports_target", "target_type", "target_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    reporter_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    # The reported object — references only, never a data dump.
    target_type: Mapped[str] = mapped_column(String(40), nullable=False)
    target_id: Mapped[str] = mapped_column(String(64), nullable=False)
    organization_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID, ForeignKey("organizations.id", ondelete="SET NULL"), index=True
    )
    category: Mapped[str] = mapped_column(
        String(40), default=REPORT_CATEGORY_OTHER, nullable=False
    )
    severity: Mapped[str] = mapped_column(
        String(16), default=REPORT_SEVERITY_MEDIUM, nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(20), default=REPORT_STATUS_OPEN, nullable=False
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    # Evidence references only: [{type, id, note}] — never document contents.
    evidence_refs: Mapped[Optional[list]] = mapped_column(JSON)
    assigned_moderator_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID, ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    resolution: Mapped[Optional[str]] = mapped_column(Text)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    resolved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID, ForeignKey("users.id", ondelete="SET NULL")
    )
    reopened_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class GovernanceReportNote(Base):
    """Internal moderator note on a report (not visible to the reporter)."""

    __tablename__ = "governance_report_notes"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    report_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("governance_reports.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    author_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )