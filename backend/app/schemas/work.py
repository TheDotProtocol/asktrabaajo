"""Work ID schemas — profile, experience, education, skills, credentials, employment."""
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.models.enums import CREDENTIAL_STATUSES, EMPLOYMENT_TYPES
from app.schemas.common import ORMOut


class ProfilePatch(BaseModel):
    headline: Optional[str] = Field(default=None, max_length=200)
    summary: Optional[str] = Field(default=None, max_length=4000)
    location: Optional[str] = Field(default=None, max_length=160)
    country_code: Optional[str] = Field(default=None, max_length=8)


class ProfileOut(ORMOut):
    id: uuid.UUID
    headline: Optional[str] = None
    summary: Optional[str] = None
    location: Optional[str] = None
    country_code: Optional[str] = None
    updated_at: datetime


class ExperienceCreate(BaseModel):
    company_name: str = Field(min_length=1, max_length=200)
    title: str = Field(min_length=1, max_length=200)
    location: Optional[str] = Field(default=None, max_length=160)
    start_date: date
    end_date: Optional[date] = None
    is_current: bool = False
    description: Optional[str] = Field(default=None, max_length=4000)


class ExperienceUpdate(BaseModel):
    company_name: Optional[str] = Field(default=None, max_length=200)
    title: Optional[str] = Field(default=None, max_length=200)
    location: Optional[str] = Field(default=None, max_length=160)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_current: Optional[bool] = None
    description: Optional[str] = Field(default=None, max_length=4000)


class ExperienceOut(ORMOut):
    id: uuid.UUID
    company_name: str
    title: str
    location: Optional[str] = None
    start_date: date
    end_date: Optional[date] = None
    is_current: bool
    description: Optional[str] = None


class EducationCreate(BaseModel):
    institution: str = Field(min_length=1, max_length=200)
    degree: Optional[str] = Field(default=None, max_length=200)
    field_of_study: Optional[str] = Field(default=None, max_length=200)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_current: bool = False
    description: Optional[str] = Field(default=None, max_length=4000)


class EducationUpdate(BaseModel):
    institution: Optional[str] = Field(default=None, max_length=200)
    degree: Optional[str] = Field(default=None, max_length=200)
    field_of_study: Optional[str] = Field(default=None, max_length=200)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_current: Optional[bool] = None
    description: Optional[str] = Field(default=None, max_length=4000)


class EducationOut(ORMOut):
    id: uuid.UUID
    institution: str
    degree: Optional[str] = None
    field_of_study: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_current: bool
    description: Optional[str] = None


class SkillOut(ORMOut):
    id: uuid.UUID
    name: str
    category: str


class UserSkillAdd(BaseModel):
    skill_name: str = Field(min_length=1, max_length=120)
    level: str = "intermediate"
    years_experience: Optional[float] = Field(default=None, ge=0, le=80)


class UserSkillOut(BaseModel):
    id: uuid.UUID
    skill_id: uuid.UUID
    name: str
    category: str
    level: str
    years_experience: Optional[float] = None


class CredentialCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    issuer: Optional[str] = Field(default=None, max_length=200)
    credential_type: str = "certification"
    credential_number: Optional[str] = Field(default=None, max_length=120)
    issued_at: Optional[date] = None
    expires_at: Optional[date] = None


class CredentialUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=200)
    issuer: Optional[str] = Field(default=None, max_length=200)
    credential_type: Optional[str] = None
    credential_number: Optional[str] = Field(default=None, max_length=120)
    issued_at: Optional[date] = None
    expires_at: Optional[date] = None


class CredentialOut(ORMOut):
    id: uuid.UUID
    name: str
    issuer: Optional[str] = None
    credential_type: str
    status: str
    issued_at: Optional[date] = None
    expires_at: Optional[date] = None
    verified_at: Optional[datetime] = None
    verification_source: Optional[str] = None


class EmploymentCreate(BaseModel):
    company_name: str = Field(min_length=1, max_length=200)
    title: str = Field(min_length=1, max_length=200)
    employment_type: str = "full_time"
    start_date: date
    end_date: Optional[date] = None
    is_current: bool = False


class EmploymentOut(ORMOut):
    id: uuid.UUID
    company_name: str
    title: str
    employment_type: str
    start_date: date
    end_date: Optional[date] = None
    is_current: bool


class WorkIdSummary(BaseModel):
    person: ProfileOut
    experiences: List[ExperienceOut]
    educations: List[EducationOut]
    skills: List[UserSkillOut]
    credentials: List[CredentialOut]
    employments: List[EmploymentOut]


# Valid status helpers --------------------------------------------------------
def is_valid_credential_status(value: str) -> bool:
    return value in CREDENTIAL_STATUSES


def is_valid_employment_type(value: str) -> bool:
    return value in EMPLOYMENT_TYPES
