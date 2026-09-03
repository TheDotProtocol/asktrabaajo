"""Work ID foundation — person-owned professional journey records.

All rows belong to a ``PersonProfile`` (the PERSON record). Nothing here is
shared with an employer unless the person authorizes disclosure (the
document/consent layer handles that — see ``app.models.documents``).
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
    JSON,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from app.db.base import Base
from app.models.enums import CREDENTIAL_STATUS_UNVERIFIED, VERIFICATION_UNVERIFIED
from app.models.identity import TimestampMixin

UUID = Uuid


class WorkExperience(Base, TimestampMixin):
    __tablename__ = "work_experiences"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    person_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("person_profiles.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    company_name: Mapped[str] = mapped_column(String(200), nullable=False)
    company_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID)  # resolved later
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    department: Mapped[Optional[str]] = mapped_column(String(160))
    location: Mapped[Optional[str]] = mapped_column(String(160))
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[Optional[date]] = mapped_column(Date)
    is_current: Mapped[bool] = mapped_column(default=False, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    skills_used: Mapped[Optional[list]] = mapped_column(JSON)
    verification_status: Mapped[str] = mapped_column(
        String(20), default=VERIFICATION_UNVERIFIED, nullable=False
    )


class Education(Base, TimestampMixin):
    __tablename__ = "educations"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    person_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("person_profiles.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    institution: Mapped[str] = mapped_column(String(200), nullable=False)
    level: Mapped[Optional[str]] = mapped_column(String(60))  # EDUCATION_LEVELS
    degree: Mapped[Optional[str]] = mapped_column(String(200))
    field_of_study: Mapped[Optional[str]] = mapped_column(String(200))
    start_date: Mapped[Optional[date]] = mapped_column(Date)
    end_date: Mapped[Optional[date]] = mapped_column(Date)
    is_current: Mapped[bool] = mapped_column(default=False, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    verification_status: Mapped[str] = mapped_column(
        String(20), default=VERIFICATION_UNVERIFIED, nullable=False
    )


class Skill(Base):
    __tablename__ = "skills"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(
        String(120), unique=True, index=True, nullable=False
    )
    category: Mapped[str] = mapped_column(String(60), default="general", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class UserSkill(Base, TimestampMixin):
    __tablename__ = "user_skills"
    __table_args__ = (
        UniqueConstraint("person_id", "skill_id", name="uq_user_skills_person_skill"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    person_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("person_profiles.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(
        UUID, ForeignKey("skills.id", ondelete="CASCADE"), nullable=False
    )
    level: Mapped[str] = mapped_column(String(20), default="intermediate", nullable=False)
    years_experience: Mapped[Optional[float]] = mapped_column(Float)


class Credential(Base, TimestampMixin):
    """A credential/certification instance owned by a person.

    Verification state is explicit and transitions are restricted: only the
    verification pipeline may move a record into VERIFIED/PENDING (future
    phases); owners may mark their own claims as unverified or request
    verification. EXPIRED/REVOKED result from policy or issuer action.
    """

    __tablename__ = "credentials"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    person_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("person_profiles.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    issuer: Mapped[Optional[str]] = mapped_column(String(200))
    credential_type: Mapped[str] = mapped_column(
        String(32), default="certification", nullable=False
    )
    credential_number: Mapped[Optional[str]] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(
        String(20), default=CREDENTIAL_STATUS_UNVERIFIED, nullable=False
    )
    issued_at: Mapped[Optional[date]] = mapped_column(Date)
    expires_at: Mapped[Optional[date]] = mapped_column(Date)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    verification_source: Mapped[Optional[str]] = mapped_column(String(200))
    document_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID)


class Employment(Base, TimestampMixin):
    __tablename__ = "employments"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    person_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("person_profiles.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    company_name: Mapped[str] = mapped_column(String(200), nullable=False)
    company_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID)  # resolved later
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    department: Mapped[Optional[str]] = mapped_column(String(160))
    location: Mapped[Optional[str]] = mapped_column(String(160))
    employment_type: Mapped[str] = mapped_column(
        String(32), default="full_time", nullable=False
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[Optional[date]] = mapped_column(Date)
    is_current: Mapped[bool] = mapped_column(default=False, nullable=False)
    skills_used: Mapped[Optional[list]] = mapped_column(JSON)
    verification_status: Mapped[str] = mapped_column(
        String(20), default=VERIFICATION_UNVERIFIED, nullable=False
    )
