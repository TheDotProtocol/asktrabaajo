"""Jobseeker Career OS — career-domain models (Phase 5).

Ownership boundaries (per the approved architecture):
- Work DNA, career goals, milestones  -> person-owned (PERSON owns the journey)
- Applications, interviews, offers    -> person-owned; a company later
  *interacts* through authorized recruitment workflows, never by owning them
- Opportunities                       -> platform/company-provided catalogue;
  a person's SAVE/DISMISS/APPLY state lives on the person, not the catalogue
- Notifications                       -> user-owned feed

Phase-6 note: the live careers corpus (Supabase ``public.jobs``) is preserved
untouched. ``opportunities.imported_from`` + ``source`` carry provenance so the
employer pipeline can feed canonical opportunities later without remodelling.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.db.base import Base
from app.models.enums import (
    APPLICATION_STATUS_DISCOVERED,
    INTERVIEW_STATUS_SCHEDULED,
    NOTIFICATION_KIND_SYSTEM,
    OFFER_STATUS_PENDING,
    OPPORTUNITY_SOURCE_PLATFORM,
)
from app.models.identity import TimestampMixin

UUID = Uuid


class WorkDnaProfile(Base, TimestampMixin):
    """Structured Work DNA result — NOT one reductive score.

    ``dimensions`` is an extensible list of
    ``{key, label, value, confidence, evidence}`` maps so future assessment
    versions and adaptive engines can write richer profiles without schema
    churn. The source questionnaire version is recorded for auditability.
    """

    __tablename__ = "work_dna_profiles"
    __table_args__ = (
        UniqueConstraint("person_id", "version", name="uq_work_dna_person_version"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    person_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("person_profiles.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    version: Mapped[str] = mapped_column(String(40), nullable=False)
    source: Mapped[str] = mapped_column(String(40), default="assessment", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="completed", nullable=False)
    dimensions: Mapped[Optional[list]] = mapped_column(JSON)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class WorkDnaAnswer(Base):
    """Raw answer log for a Work DNA assessment session.

    Kept so future adaptive assessments and the audit trail can explain how a
    profile was derived. Answers are never used to fabricate claims about the
    person; they feed explicit, versioned dimension computation only.
    """

    __tablename__ = "work_dna_answers"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    person_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("person_profiles.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    profile_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID, ForeignKey("work_dna_profiles.id", ondelete="SET NULL")
    )
    question_key: Mapped[str] = mapped_column(String(80), nullable=False)
    answer: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class CareerGoal(Base, TimestampMixin):
    """A person's stated career direction + constraints.

    Matching and the Career Advisor read goals; the person always owns them.
    """

    __tablename__ = "career_goals"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    person_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("person_profiles.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    target_role: Mapped[Optional[str]] = mapped_column(String(200))
    target_industries: Mapped[Optional[list]] = mapped_column(JSON)
    target_locations: Mapped[Optional[list]] = mapped_column(JSON)
    preferred_work_modes: Mapped[Optional[list]] = mapped_column(JSON)
    min_salary: Mapped[Optional[float]] = mapped_column(Float)
    salary_currency: Mapped[Optional[str]] = mapped_column(String(8), default="USD")
    open_to_relocation: Mapped[bool] = mapped_column(Boolean, default=False)
    open_to_remote: Mapped[bool] = mapped_column(Boolean, default=True)
    availability: Mapped[Optional[str]] = mapped_column(String(120))
    is_primary: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)


class Opportunity(Base, TimestampMixin):
    """Normalized internal representation of a job opportunity.

    ``company_name`` is denormalized for the jobseeker catalogue; a future
    company/tenant link (Phase 6) will connect this row to an Organization
    without remodelling. ``imported_from`` records provenance (careers corpus,
    demo seed, external source) so every row is explainable.
    """

    __tablename__ = "opportunities"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    company_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID, ForeignKey("organizations.id", ondelete="SET NULL"), index=True
    )
    company_name: Mapped[str] = mapped_column(String(200), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[Optional[str]] = mapped_column(String(220))
    summary: Mapped[Optional[str]] = mapped_column(Text)
    description: Mapped[Optional[str]] = mapped_column(Text)
    location: Mapped[Optional[str]] = mapped_column(String(200))
    country: Mapped[Optional[str]] = mapped_column(String(80))
    city: Mapped[Optional[str]] = mapped_column(String(120))
    remote_eligible: Mapped[bool] = mapped_column(Boolean, default=False)
    work_mode: Mapped[Optional[str]] = mapped_column(String(20))
    employment_type: Mapped[Optional[str]] = mapped_column(String(32))
    experience_level: Mapped[Optional[str]] = mapped_column(String(80))
    seniority: Mapped[Optional[str]] = mapped_column(String(40))
    industry: Mapped[Optional[str]] = mapped_column(String(120))
    skills_required: Mapped[Optional[list]] = mapped_column(JSON)
    min_salary: Mapped[Optional[float]] = mapped_column(Float)
    max_salary: Mapped[Optional[float]] = mapped_column(Float)
    salary_currency: Mapped[Optional[str]] = mapped_column(String(8), default="USD")
    language_requirements: Mapped[Optional[list]] = mapped_column(JSON)
    closing_at: Mapped[Optional[date]] = mapped_column(Date)
    source: Mapped[str] = mapped_column(
        String(24), default=OPPORTUNITY_SOURCE_PLATFORM, nullable=False
    )
    imported_from: Mapped[Optional[str]] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    is_approved: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class OpportunityInteraction(Base):
    """A person's private stance on an opportunity (save / dismiss)."""

    __tablename__ = "opportunity_interactions"
    __table_args__ = (
        UniqueConstraint(
            "person_id", "opportunity_id", name="uq_opportunity_interactions_person_opp"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    person_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("person_profiles.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("opportunities.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    action: Mapped[str] = mapped_column(
        String(16), nullable=False
    )  # saved | dismissed
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class JobApplication(Base, TimestampMixin):
    """A person's application to an opportunity.

    Ownership: PERSON. The state machine (``services/applications.py``) is the
    only writer of status transitions and every transition is recorded as an
    ``ApplicationEvent`` — the same machine later serves employer-driven
    transitions behind membership permissions.
    """

    __tablename__ = "job_applications"
    __table_args__ = (
        UniqueConstraint(
            "person_id", "opportunity_id", name="uq_applications_person_opportunity"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    person_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("person_profiles.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("opportunities.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(32), default=APPLICATION_STATUS_DISCOVERED, nullable=False
    )
    cover_note: Mapped[Optional[str]] = mapped_column(Text)
    applied_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    withdrawn_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_activity_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    # Denormalized employer link: which company job this application belongs
    # to (set when the opportunity is a published company job). One lifecycle,
    # two sides — the jobseeker Career OS and the company pipeline read the
    # same row and the same state machine.
    job_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID,
        ForeignKey("job_postings.id", ondelete="SET NULL"),
        index=True,
    )

    opportunity: Mapped["Opportunity"] = relationship(lazy="selectin")


class ApplicationEvent(Base):
    """Append-only application timeline entry."""

    __tablename__ = "application_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("job_applications.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    from_status: Mapped[Optional[str]] = mapped_column(String(32))
    to_status: Mapped[str] = mapped_column(String(32), nullable=False)
    note: Mapped[Optional[str]] = mapped_column(Text)
    actor_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID, ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Interview(Base, TimestampMixin):
    """Jobseeker-side interview record attached to an application."""

    __tablename__ = "interviews"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("job_applications.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=45, nullable=False)
    mode: Mapped[str] = mapped_column(String(16), default="video", nullable=False)
    meeting_link: Mapped[Optional[str]] = mapped_column(String(500))
    interviewer_name: Mapped[Optional[str]] = mapped_column(String(200))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        String(24), default=INTERVIEW_STATUS_SCHEDULED, nullable=False
    )
    reschedule_reason: Mapped[Optional[str]] = mapped_column(Text)
    reschedule_requested_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True)
    )
    reschedule_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class Offer(Base, TimestampMixin):
    """Jobseeker-side offer record.

    The offer document is authoritative when supplied by the company; the
    record here mirrors the terms for the candidate experience. Accept/decline
    decisions are explicit, audited, and never auto-generated.
    """

    __tablename__ = "offers"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("job_applications.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20), default=OFFER_STATUS_PENDING, nullable=False
    )
    salary_amount: Mapped[Optional[float]] = mapped_column(Float)
    salary_currency: Mapped[Optional[str]] = mapped_column(String(8), default="USD")
    equity: Mapped[Optional[str]] = mapped_column(String(120))
    benefits_summary: Mapped[Optional[str]] = mapped_column(Text)
    start_date: Mapped[Optional[date]] = mapped_column(Date)
    location: Mapped[Optional[str]] = mapped_column(String(200))
    terms_summary: Mapped[Optional[str]] = mapped_column(Text)
    offer_document_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID)
    responded_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class CareerMilestone(Base, TimestampMixin):
    """Person-owned career timeline milestone."""

    __tablename__ = "career_milestones"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    person_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("person_profiles.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    occurred_on: Mapped[date] = mapped_column(Date, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    reference_type: Mapped[Optional[str]] = mapped_column(String(60))
    reference_id: Mapped[Optional[str]] = mapped_column(String(64))


class UserNotification(Base):
    """In-app notification feed entry (user-owned, minimal + not spammy)."""

    __tablename__ = "user_notifications"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    kind: Mapped[str] = mapped_column(
        String(24), default=NOTIFICATION_KIND_SYSTEM, nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[Optional[str]] = mapped_column(Text)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
