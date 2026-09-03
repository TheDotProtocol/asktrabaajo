"""Talent Graph — skill taxonomy, evidence, career paths and employer-side
intelligence records (Phase 7).

One authoritative model, no duplicated concepts:
- The canonical skill lives in ``app.models.work.Skill`` (already referenced
  by ``user_skills``). This module extends it with ALIASES (normalization),
  RELATIONSHIPS (taxonomy graph) and EVIDENCE (where a person's claim to a
  skill comes from — provenance, never inferred as verified).
- ``OpportunityRequirement`` normalizes an opportunity's raw requirement
  text into a structured, skill-linked row while ALWAYS preserving the
  original employer wording (requirement provenance).
- ``CareerPath`` / ``CareerPathStep`` are a small advisory catalogue the
  career-intelligence layer reads to give *evidence-grounded* "what you may
  need next" advice. Paths are never deterministic guarantees.
- ``TalentPool`` / ``TalentPoolMember`` / ``SavedCandidate`` are
  organization-scoped private employer lists. Company A can never read
  Company B pools (tenant isolation is enforced at the service/API layer).
- ``CandidateSearchEvent`` records discovery activity for security and
  platform governance. It stores filters, never personal record content.

Privacy model (unchanged from Phase 4): the discovery layer reads only the
sections a person has marked PUBLIC on their Work ID. Everything else stays
behind consent.
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
    JSON,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from app.db.base import Base
from app.models.enums import (
    SKILL_EVIDENCE_SELF,
    SKILL_STATUS_ACTIVE,
    VERIFICATION_UNVERIFIED,
)
from app.models.identity import TimestampMixin

UUID = Uuid


class SkillAlias(Base):
    """A normalized alias that resolves to one canonical skill.

    ``alias`` holds the NORMALIZED form (the service's ``normalize()``
    output) and is globally unique so one alias can never resolve to two
    skills. ``original`` preserves the raw value first seen, ``source`` and
    ``confidence`` keep provenance of the alias itself.
    """

    __tablename__ = "skill_aliases"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    skill_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("skills.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    alias: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    original: Mapped[Optional[str]] = mapped_column(String(200))
    source: Mapped[str] = mapped_column(String(40), default="manual", nullable=False)
    confidence: Mapped[Optional[float]] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class SkillRelationship(Base):
    """A directed edge in the taxonomy graph.

    ``kind=parent`` means the subject (``skill_id``) is a specialization of
    the object (``related_skill_id``). Other kinds (related / complementary
    / similar) are adjacency edges between equals.
    """

    __tablename__ = "skill_relationships"
    __table_args__ = (
        UniqueConstraint(
            "skill_id", "related_skill_id", "kind",
            name="uq_skill_relationships_edge",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    skill_id: Mapped[uuid.UUID] = mapped_column(
        UUID, ForeignKey("skills.id", ondelete="CASCADE"), index=True, nullable=False
    )
    related_skill_id: Mapped[uuid.UUID] = mapped_column(
        UUID, ForeignKey("skills.id", ondelete="CASCADE"), index=True, nullable=False
    )
    kind: Mapped[str] = mapped_column(String(24), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class SkillEvidence(Base):
    """A person's skill claim linked to the record it came from.

    ``reference_type`` / ``reference_id`` point at the owning record (an
    employment row, a credential row, ...) without a polymorphic FK. The
    verification state mirrors the source record: a skill claimed only by
    the person is NEVER shown as verified.
    """

    __tablename__ = "skill_evidence"
    __table_args__ = (
        UniqueConstraint(
            "person_id", "skill_id", "reference_type", "reference_id",
            name="uq_skill_evidence_source",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    person_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("person_profiles.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(
        UUID, ForeignKey("skills.id", ondelete="CASCADE"), index=True, nullable=False
    )
    evidence_type: Mapped[str] = mapped_column(
        String(24), default=SKILL_EVIDENCE_SELF, nullable=False
    )
    reference_type: Mapped[str] = mapped_column(String(40), nullable=False)
    reference_id: Mapped[uuid.UUID] = mapped_column(UUID, nullable=False)
    source: Mapped[str] = mapped_column(String(60), default="work_id", nullable=False)
    verification_status: Mapped[str] = mapped_column(
        String(20), default=VERIFICATION_UNVERIFIED, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class OpportunityRequirement(Base, TimestampMixin):
    """A structured requirement derived from an opportunity.

    ``raw_text`` always preserves the employer's original wording. When the
    text resolves to a canonical taxonomy skill, ``skill_id`` links it so
    matching and gap analysis can reason structurally; otherwise the text is
    kept (never invented requirements are added).
    """

    __tablename__ = "opportunity_requirements"
    __table_args__ = (
        UniqueConstraint("opportunity_id", "raw_text", name="uq_opp_requirement_text"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("opportunities.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    skill_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID, ForeignKey("skills.id", ondelete="SET NULL")
    )
    raw_text: Mapped[str] = mapped_column(String(400), nullable=False)
    requirement_kind: Mapped[str] = mapped_column(
        String(16), default="required", nullable=False
    )
    min_years: Mapped[Optional[float]] = mapped_column(Float)


class CareerPath(Base):
    """Advisory career-path catalogue entry (foundation)."""

    __tablename__ = "career_paths"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    target_role: Mapped[str] = mapped_column(String(200), nullable=False)
    industry: Mapped[Optional[str]] = mapped_column(String(120))
    description: Mapped[Optional[str]] = mapped_column(Text)
    source: Mapped[str] = mapped_column(
        String(60), default="asktrabaajo_career_paths_v1", nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(20), default=SKILL_STATUS_ACTIVE, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class CareerPathStep(Base):
    """One rung on a career path.

    ``skills_required`` lists canonical skill names the rung commonly needs;
    it is advisory (a step toward the role), never a hard gate.
    """

    __tablename__ = "career_path_steps"
    __table_args__ = (
        UniqueConstraint("path_id", "step_order", name="uq_career_path_step_order"),
        Index("ix_career_path_steps_role_title", "role_title"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    path_id: Mapped[uuid.UUID] = mapped_column(
        UUID, ForeignKey("career_paths.id", ondelete="CASCADE"), index=True,
        nullable=False,
    )
    step_order: Mapped[int] = mapped_column(Integer, nullable=False)
    role_title: Mapped[str] = mapped_column(String(200), nullable=False)
    seniority: Mapped[Optional[str]] = mapped_column(String(40))
    description: Mapped[Optional[str]] = mapped_column(Text)
    skills_required: Mapped[Optional[list]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class TalentPool(Base, TimestampMixin):
    """A private, organization-scoped group of saved candidates."""

    __tablename__ = "talent_pools"
    __table_args__ = (
        UniqueConstraint("organization_id", "name", name="uq_talent_pools_org_name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID, ForeignKey("users.id", ondelete="SET NULL")
    )


class TalentPoolMember(Base):
    """A candidate inside an organization talent pool."""

    __tablename__ = "talent_pool_members"
    __table_args__ = (
        UniqueConstraint("pool_id", "person_id", name="uq_talent_pool_members"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    pool_id: Mapped[uuid.UUID] = mapped_column(
        UUID, ForeignKey("talent_pools.id", ondelete="CASCADE"), index=True,
        nullable=False,
    )
    person_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("person_profiles.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    added_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID, ForeignKey("users.id", ondelete="SET NULL")
    )
    note: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class SavedCandidate(Base, TimestampMixin):
    """A recruiter's private shortlist entry (organization-scoped)."""

    __tablename__ = "saved_candidates"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "user_id", "person_id",
            name="uq_saved_candidates_org_user_person",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    person_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("person_profiles.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    note: Mapped[Optional[str]] = mapped_column(Text)
    tags: Mapped[Optional[list]] = mapped_column(JSON)


class CandidateSearchEvent(Base):
    """Discovery activity record — who searched, in which organization, with
    which filters, and how many results returned. Filters only: never the
    candidate rows themselves (privacy + no sensitive payloads)."""

    __tablename__ = "candidate_search_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    query: Mapped[Optional[str]] = mapped_column(String(300))
    filters: Mapped[Optional[dict]] = mapped_column(JSON)
    result_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
