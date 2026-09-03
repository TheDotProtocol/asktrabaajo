"""Company / HR / Recruiter Employment OS — company-domain models (Phase 6).

Relationships (one authoritative model, no parallel universe):
- CompanyProfile 1:1 Organization (employer/recruiter tenant)
- JobPosting     -> Organization (owner) -> Opportunity (published canon)
- JobApplication -> Opportunity AND job_id (denormalized for the employer
  pipeline) — ONE lifecycle shared with the jobseeker Career OS (Phase 5)
- InterviewScorecard -> Interview (structured feedback foundation)
- DocumentRequest    -> Application -> PERSON; approval grants org access
  through the Phase 4 consent/document layer

Nothing here copies the legacy Supabase careers tables (companies, jobs,
applications, ...). Those stay authoritative for the legacy careers platform;
the ingestion adapter maps them INTO this canonical model with provenance.
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
    DOC_REQUEST_STATUS_PENDING,
    JOB_STATUS_DRAFT,
    ORG_VERIFICATION_UNVERIFIED,
)
from app.models.identity import TimestampMixin

UUID = Uuid


class CompanyProfile(Base, TimestampMixin):
    """Canonical company/employer profile attached to an Organization."""

    __tablename__ = "company_profiles"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        primary_key=True,
    )
    legal_name: Mapped[Optional[str]] = mapped_column(String(240))
    display_name: Mapped[Optional[str]] = mapped_column(String(240))
    industry: Mapped[Optional[str]] = mapped_column(String(120))
    sector: Mapped[Optional[str]] = mapped_column(String(120))
    country: Mapped[Optional[str]] = mapped_column(String(80))
    city: Mapped[Optional[str]] = mapped_column(String(120))
    website_url: Mapped[Optional[str]] = mapped_column(String(300))
    company_size: Mapped[Optional[str]] = mapped_column(String(40))
    company_type: Mapped[Optional[str]] = mapped_column(String(40))  # startup/sme/...
    description: Mapped[Optional[str]] = mapped_column(Text)
    contact_name: Mapped[Optional[str]] = mapped_column(String(160))
    contact_email: Mapped[Optional[str]] = mapped_column(String(320))
    verification_status: Mapped[str] = mapped_column(
        String(20), default=ORG_VERIFICATION_UNVERIFIED, nullable=False
    )


class JobPosting(Base, TimestampMixin):
    """A company's job posting with a controlled lifecycle.

    Publishing maps the job into the shared catalogue: the canonical
    ``Opportunity`` the jobseeker Career OS already discovers and applies to
    (``opportunity_id``). One job = one active opportunity while published.
    """

    __tablename__ = "job_postings"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    opportunity_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID, ForeignKey("opportunities.id", ondelete="SET NULL")
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(220), nullable=False)
    department: Mapped[Optional[str]] = mapped_column(String(160))
    summary: Mapped[Optional[str]] = mapped_column(Text)
    description: Mapped[Optional[str]] = mapped_column(Text)
    responsibilities: Mapped[Optional[list]] = mapped_column(JSON)
    requirements: Mapped[Optional[list]] = mapped_column(JSON)
    skills_required: Mapped[Optional[list]] = mapped_column(JSON)
    preferred_skills: Mapped[Optional[list]] = mapped_column(JSON)
    experience_level: Mapped[Optional[str]] = mapped_column(String(80))
    education_level: Mapped[Optional[str]] = mapped_column(String(60))
    location: Mapped[Optional[str]] = mapped_column(String(200))
    country: Mapped[Optional[str]] = mapped_column(String(80))
    city: Mapped[Optional[str]] = mapped_column(String(120))
    remote_eligible: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    work_mode: Mapped[Optional[str]] = mapped_column(String(20))
    employment_type: Mapped[Optional[str]] = mapped_column(String(32))
    salary_min: Mapped[Optional[float]] = mapped_column(Float)
    salary_max: Mapped[Optional[float]] = mapped_column(Float)
    salary_currency: Mapped[Optional[str]] = mapped_column(String(8), default="USD")
    seniority: Mapped[Optional[str]] = mapped_column(String(40))
    industry: Mapped[Optional[str]] = mapped_column(String(120))
    languages: Mapped[Optional[list]] = mapped_column(JSON)
    openings_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    application_deadline: Mapped[Optional[date]] = mapped_column(Date)
    screening_questions: Mapped[Optional[list]] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(
        String(20), default=JOB_STATUS_DRAFT, nullable=False
    )
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    imported_from: Mapped[Optional[str]] = mapped_column(String(120))

    organization: Mapped["Organization"] = relationship(lazy="selectin")  # noqa: F821


class ScreeningResponse(Base, TimestampMixin):
    """Candidate answers to a job's screening questions (auditable)."""

    __tablename__ = "screening_responses"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("job_applications.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID, ForeignKey("job_postings.id", ondelete="CASCADE"), nullable=False
    )
    answers: Mapped[Optional[list]] = mapped_column(JSON)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class InterviewScorecard(Base, TimestampMixin):
    """Structured interviewer feedback — foundation only.

    Fields are role-relevant criteria; protected characteristics are never
    collected or inferred. No facial/behavioural analysis exists anywhere.
    """

    __tablename__ = "interview_scorecards"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    interview_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("interviews.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    interviewer_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    criteria: Mapped[Optional[list]] = mapped_column(JSON)  # [{key,label,score,note}]
    strengths: Mapped[Optional[str]] = mapped_column(Text)
    concerns: Mapped[Optional[str]] = mapped_column(Text)
    recommendation: Mapped[Optional[str]] = mapped_column(String(20))
    notes: Mapped[Optional[str]] = mapped_column(Text)


class DocumentRequest(Base, TimestampMixin):
    """Company -> candidate request for a specific document/evidence.

    Candidate approval creates a live organization grant through the Phase 4
    document layer (the candidate controls disclosure; access is audited).
    """

    __tablename__ = "document_requests"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("job_applications.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    requested_by: Mapped[uuid.UUID] = mapped_column(
        UUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    document_type: Mapped[str] = mapped_column(String(60), nullable=False)
    purpose: Mapped[Optional[str]] = mapped_column(String(240))
    status: Mapped[str] = mapped_column(
        String(20), default=DOC_REQUEST_STATUS_PENDING, nullable=False
    )
    responded_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    responded_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID, ForeignKey("users.id", ondelete="SET NULL")
    )
    note: Mapped[Optional[str]] = mapped_column(Text)
