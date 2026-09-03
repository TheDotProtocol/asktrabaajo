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
    REPORT_PRIORITY_NORMAL,
    REPORT_SEVERITY_MEDIUM,
    REPORT_STATUS_OPEN,
)
from app.models.identity import TimestampMixin

UUID = Uuid


class GovernanceReport(Base, TimestampMixin):
    """A structured governance report filed by any authenticated user.

    Phase 10 extends the same row into the operational case model (one
    authoritative record — no second moderation system): explicit priority,
    governance-team assignment, escalation markers and deterministic SLA
    deadlines computed from the priority policy at creation/escalation.
    """

    __tablename__ = "governance_reports"
    __table_args__ = (
        Index("ix_governance_reports_status_severity", "status", "severity"),
        Index("ix_governance_reports_target", "target_type", "target_id"),
        Index("ix_governance_reports_priority", "priority", "status"),
        Index("ix_governance_reports_sla_due", "sla_resolution_due_at", "status"),
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
    # Operational priority (Phase 10) — drives the deterministic SLA windows.
    priority: Mapped[str] = mapped_column(
        String(16), default=REPORT_PRIORITY_NORMAL, nullable=False
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
    # Governance team ownership (operational grouping, not authorization).
    team_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID, ForeignKey("governance_teams.id", ondelete="SET NULL"), index=True
    )
    # Escalation markers (metadata; reason travels in the audit event).
    escalated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    escalated_to_team_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID, ForeignKey("governance_teams.id", ondelete="SET NULL")
    )
    escalated_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID, ForeignKey("users.id", ondelete="SET NULL")
    )
    # Deterministic SLA fields (lazy evaluation — no scheduler).
    first_responded_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    sla_response_due_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    sla_resolution_due_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    resolution: Mapped[Optional[str]] = mapped_column(Text)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    resolved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID, ForeignKey("users.id", ondelete="SET NULL")
    )
    reopened_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


GOVERNANCE_TEAM_SEEDS = (
    ("platform_safety", "Platform Safety",
     "Safety, harassment and abuse reports."),
    ("fraud", "Fraud", "Fraudulent jobs, offers and impersonation."),
    ("employer_integrity", "Employer Integrity",
     "Employer behaviour and policy reports."),
    ("candidate_integrity", "Candidate Integrity",
     "Candidate-side integrity reports."),
    ("communications", "Communications",
     "Communication disputes and outreach conduct."),
    ("document_trust", "Document Trust",
     "Document misuse and verification trust."),
    ("technical_abuse", "Technical Abuse",
     "Scraping, rate abuse and technical misuse."),
    ("general_support", "General Support",
     "Everything else routed for triage."),
)


class GovernanceTeam(Base):
    """A lightweight operational governance team (Phase 10).

    Teams organize the queue and group workload — they are NOT an
    authorization mechanism. Authorization stays on platform-scope roles and
    ``reports.*`` permissions.
    """

    __tablename__ = "governance_teams"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class GovernanceTeamMember(Base):
    """A governance user's membership in one or more governance teams."""

    __tablename__ = "governance_team_members"
    __table_args__ = (
        # One membership per (team, user).
        Index("uq_governance_team_members", "team_id", "user_id", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    team_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("governance_teams.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class GovernanceCaseLink(Base):
    """Links multiple reports into one investigation case (Phase 10).

    Prevent duplicate investigations without copying any report data. Linking
    is restricted to reports that share a tenant boundary (same organization
    or both platform-level) — cross-tenant linking is refused.
    """

    __tablename__ = "governance_case_links"
    __table_args__ = (
        Index("uq_governance_case_links", "case_id", "linked_report_id", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("governance_reports.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    linked_report_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("governance_reports.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    reason: Mapped[Optional[str]] = mapped_column(String(300))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


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