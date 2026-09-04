"""AI Interview Engine — controlled Athena-conducted interviews (Phase 16).

Athena assists with interviewing and evaluation; it never makes the final
employment decision. These tables persist the ORCHESTRATION ENVELOPE only:

- ``ai_interview_sessions`` — employer-configured, candidate-owned flow:
  state machine, consent snapshot, entry-token hash, media profile,
  bounded integrity signals, human decision fields. The raw interview
  is never recorded here.
- ``ai_interview_questions`` — the validated, sequenced question plan
  (deterministic plan generation at start; questions are grounded in the
  job requirements + candidate Work ID and pass the prohibited-topic gate).
- ``ai_interview_evaluations`` — structured per-answer evaluation on
  job-relevant dimensions. NO raw answer text is ever stored.
- ``ai_interview_reports`` — the completion report (strengths,
  improvement areas, competency evidence, unanswered areas, quality
  metadata, review signals) marked AI-assisted / human-review-required.

Privacy: raw responses, transcripts and media are NOT persisted by
default. Voice/video is a provider-neutral abstraction (``media.py``)
that fails safe when unconfigured. Integrity signals are objective
session-level events labeled as review signals — never proof of
wrongdoing and never an evaluation penalty.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
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
    AI_INTERVIEW_STATUS_SCHEDULED,
    AI_INTERVIEW_TYPE_SCREENING,
)
from app.models.identity import TimestampMixin

UUID = Uuid


class AiInterviewSession(Base, TimestampMixin):
    """One employer-configured, candidate-owned AI interview flow."""

    __tablename__ = "ai_interview_sessions"
    __table_args__ = (
        Index("ix_ai_interviews_org_created", "organization_id", "created_at"),
        Index("ix_ai_interviews_person_created", "candidate_person_id", "created_at"),
        Index("ix_ai_interviews_application_id", "application_id"),
        Index("ix_ai_interviews_opportunity_id", "opportunity_id"),
        Index("ix_ai_interviews_interview_id", "interview_id"),
        Index("ix_ai_interviews_person_id", "candidate_person_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    # The employment anchor. At least one of application/opportunity must be
    # set; the application carries the candidate side of the relationship.
    application_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID, ForeignKey("job_applications.id", ondelete="SET NULL")
    )
    opportunity_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID, ForeignKey("opportunities.id", ondelete="SET NULL")
    )
    interview_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID, ForeignKey("interviews.id", ondelete="SET NULL")
    )
    candidate_person_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("person_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=False
    )
    interview_type: Mapped[str] = mapped_column(
        String(24), default=AI_INTERVIEW_TYPE_SCREENING, nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(24), default=AI_INTERVIEW_STATUS_SCHEDULED, nullable=False
    )
    language: Mapped[str] = mapped_column(String(16), default="en", nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    question_count: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    difficulty: Mapped[str] = mapped_column(String(16), default="medium", nullable=False)
    # Configured competencies / skills the plan must stay within (bounded).
    competencies: Mapped[Optional[list]] = mapped_column(JSON)
    evaluation_dimensions: Mapped[Optional[list]] = mapped_column(JSON)
    introduction: Mapped[Optional[str]] = mapped_column(Text)
    closing: Mapped[Optional[str]] = mapped_column(Text)
    # Media profile — provider-neutral configuration, no credentials.
    media_profile: Mapped[Optional[dict]] = mapped_column(JSON)
    # Consent snapshot (metadata only).
    consent_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    consent_granted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True)
    )
    consent_version: Mapped[Optional[str]] = mapped_column(String(20))
    consent_mic: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    consent_camera: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    consent_recording: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    consent_withdrawn_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True)
    )
    # Secure session entry: the plaintext entry token is returned once at
    # creation; only its SHA-256 hash is stored. Candidate routes re-validate
    # it on every call (constant-time compare), so a session URL cannot be
    # guessed and replay requires the actual token.
    entry_token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    cancel_reason: Mapped[Optional[str]] = mapped_column(String(40))
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    failed_reason: Mapped[Optional[str]] = mapped_column(String(60))
    # Bounded objective signals (type + at + detail). Signals only.
    integrity_signals: Mapped[Optional[list]] = mapped_column(JSON)
    # Human decision (employer) — never set by the AI.
    decision: Mapped[Optional[str]] = mapped_column(String(32))
    decision_note: Mapped[Optional[str]] = mapped_column(String(500))
    decided_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID, ForeignKey("users.id", ondelete="SET NULL")
    )
    decided_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class AiInterviewQuestion(Base):
    """One validated, sequenced question in the interview plan."""

    __tablename__ = "ai_interview_questions"
    __table_args__ = (
        UniqueConstraint(
            "session_id", "sequence", name="uq_ai_interview_question_sequence"
        ),
        Index("ix_ai_interview_questions_session", "session_id", "sequence"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("ai_interview_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    category: Mapped[str] = mapped_column(String(24), nullable=False)
    competency: Mapped[str] = mapped_column(String(80), nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    difficulty: Mapped[str] = mapped_column(String(16), default="medium", nullable=False)
    target_skill: Mapped[Optional[str]] = mapped_column(String(120))
    reason: Mapped[Optional[str]] = mapped_column(Text)
    suggested_dimensions: Mapped[Optional[list]] = mapped_column(JSON)
    # Bounded follow-up questions, each linked to this competency.
    follow_ups: Mapped[Optional[list]] = mapped_column(JSON)
    # When this row IS a follow-up: the parent question it extends.
    follow_up_of: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID, ForeignKey("ai_interview_questions.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False)
    asked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    answered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class AiInterviewEvaluation(Base):
    """Structured evaluation of ONE answered question.

    Deliberately stores NO raw answer text: only explainable dimension
    scores, strengths/improvements, and objective evidence markers.
    """

    __tablename__ = "ai_interview_evaluations"
    __table_args__ = (
        UniqueConstraint(
            "session_id", "question_id", name="uq_ai_interview_eval_question"
        ),
        Index("ix_ai_interview_evaluations_session", "session_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("ai_interview_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("ai_interview_questions.id", ondelete="CASCADE"),
        nullable=False,
    )
    dimensions: Mapped[dict] = mapped_column(JSON, nullable=False)
    strengths: Mapped[Optional[list]] = mapped_column(JSON)
    improvements: Mapped[Optional[list]] = mapped_column(JSON)
    evidence_markers: Mapped[Optional[list]] = mapped_column(JSON)
    follow_up_used: Mapped[Optional[str]] = mapped_column(String(24))
    answer_length: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class AiInterviewReport(Base):
    """Completion report — AI-assisted, human review required."""

    __tablename__ = "ai_interview_reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("ai_interview_sessions.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    competency_evidence: Mapped[Optional[list]] = mapped_column(JSON)
    strengths: Mapped[Optional[list]] = mapped_column(JSON)
    improvement_areas: Mapped[Optional[list]] = mapped_column(JSON)
    unanswered_areas: Mapped[Optional[list]] = mapped_column(JSON)
    integrity_signals: Mapped[Optional[list]] = mapped_column(JSON)
    interview_quality: Mapped[Optional[dict]] = mapped_column(JSON)
    generated_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID, ForeignKey("users.id", ondelete="SET NULL")
    )
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )