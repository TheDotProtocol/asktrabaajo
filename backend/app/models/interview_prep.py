"""Interview preparation container (Phase 15).

One candidate-owned row per mock-interview preparation flow. It is a
METADATA container only: individual questions and answers are returned by
the deterministic prep service at request time (and, when the mock runs
inside an Athena session, they live in ``athena_messages`` under the
existing sanitized-message retention policy). Raw answers are never
persisted here, so candidate narratives are not retained by default — the
session row simply records that a preparation flow existed, what it was
preparing for, and when it lapses or is deleted by its owner.

Ownership: PERSON (candidate). No employer/governance surface reads it.
Access is owner-only; the API layer enforces ``person_id`` matching, and
``expires_at`` gives a deterministic lazy expiry so stale sessions release
without a scheduler (mirroring Athena sessions and enforcement windows).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from app.db.base import Base
from app.models.enums import PREP_SESSION_STATUS_ACTIVE
from app.models.identity import TimestampMixin

UUID = Uuid


class InterviewPrepSession(Base, TimestampMixin):
    __tablename__ = "interview_prep_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    person_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("person_profiles.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    # Optional anchor: which opportunity / real interview / athena chat the
    # candidate is preparing for (context, not secrets).
    opportunity_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID, ForeignKey("opportunities.id", ondelete="SET NULL"), index=True
    )
    application_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID, ForeignKey("job_applications.id", ondelete="SET NULL"), index=True
    )
    interview_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID, ForeignKey("interviews.id", ondelete="SET NULL"), index=True
    )
    athena_session_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID, ForeignKey("athena_sessions.id", ondelete="SET NULL"), index=True
    )
    status: Mapped[str] = mapped_column(
        String(20), default=PREP_SESSION_STATUS_ACTIVE, nullable=False
    )
    # The candidate's own stated focus (competency areas / roles), sanitized
    # and bounded. Free-form personal narrative never lives here.
    focus_areas: Mapped[Optional[list]] = mapped_column(JSON)
    questions_generated: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    answers_evaluated: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_activity_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
