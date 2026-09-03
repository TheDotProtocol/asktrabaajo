"""Company Employment OS schemas."""
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.schemas.common import ORMOut


# --- Company profile ----------------------------------------------------------

class CompanyProfileUpdate(BaseModel):
    legal_name: Optional[str] = Field(default=None, max_length=240)
    display_name: Optional[str] = Field(default=None, max_length=240)
    industry: Optional[str] = Field(default=None, max_length=120)
    sector: Optional[str] = Field(default=None, max_length=120)
    country: Optional[str] = Field(default=None, max_length=80)
    city: Optional[str] = Field(default=None, max_length=120)
    website_url: Optional[str] = Field(default=None, max_length=300)
    company_size: Optional[str] = Field(default=None, max_length=40)
    company_type: Optional[str] = Field(default=None, max_length=40)
    description: Optional[str] = Field(default=None, max_length=6000)
    contact_name: Optional[str] = Field(default=None, max_length=160)
    contact_email: Optional[str] = Field(default=None, max_length=320)


class CompanyProfileOut(ORMOut):
    organization_id: uuid.UUID
    legal_name: Optional[str] = None
    display_name: Optional[str] = None
    industry: Optional[str] = None
    sector: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    website_url: Optional[str] = None
    company_size: Optional[str] = None
    company_type: Optional[str] = None
    description: Optional[str] = None
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    verification_status: str


class CompanyDashboardOut(BaseModel):
    organization: Dict[str, Any]
    profile: Optional[CompanyProfileOut] = None
    open_jobs: int
    applications_total: int
    needs_review: int
    interviews_today: int
    interviews_upcoming: int
    offers_pending: int
    offers_accepted: int
    recent_applications: List[Dict[str, Any]]
    my_role: str
    permissions: List[str]


# --- Jobs ---------------------------------------------------------------------

class JobCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    summary: Optional[str] = Field(default=None, max_length=4000)
    description: Optional[str] = Field(default=None, max_length=20000)
    department: Optional[str] = Field(default=None, max_length=160)
    requirements: Optional[List[str]] = None
    skills_required: Optional[List[str]] = None
    preferred_skills: Optional[List[str]] = None
    experience_level: Optional[str] = Field(default=None, max_length=80)
    location: Optional[str] = Field(default=None, max_length=200)
    country: Optional[str] = Field(default=None, max_length=80)
    city: Optional[str] = Field(default=None, max_length=120)
    remote_eligible: bool = False
    work_mode: Optional[str] = Field(default=None, max_length=20)
    employment_type: Optional[str] = Field(default=None, max_length=32)
    salary_min: Optional[float] = Field(default=None, ge=0)
    salary_max: Optional[float] = Field(default=None, ge=0)
    salary_currency: Optional[str] = Field(default="USD", max_length=8)
    seniority: Optional[str] = Field(default=None, max_length=40)
    industry: Optional[str] = Field(default=None, max_length=120)
    languages: Optional[List[str]] = None
    openings_count: int = Field(default=1, ge=1, le=500)
    application_deadline: Optional[date] = None
    screening_questions: Optional[List[Dict[str, str]]] = None


class JobUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=200)
    summary: Optional[str] = Field(default=None, max_length=4000)
    description: Optional[str] = Field(default=None, max_length=20000)
    department: Optional[str] = Field(default=None, max_length=160)
    requirements: Optional[List[str]] = None
    skills_required: Optional[List[str]] = None
    preferred_skills: Optional[List[str]] = None
    experience_level: Optional[str] = Field(default=None, max_length=80)
    location: Optional[str] = Field(default=None, max_length=200)
    country: Optional[str] = Field(default=None, max_length=80)
    city: Optional[str] = Field(default=None, max_length=120)
    remote_eligible: Optional[bool] = None
    work_mode: Optional[str] = Field(default=None, max_length=20)
    employment_type: Optional[str] = Field(default=None, max_length=32)
    salary_min: Optional[float] = Field(default=None, ge=0)
    salary_max: Optional[float] = Field(default=None, ge=0)
    salary_currency: Optional[str] = Field(default=None, max_length=8)
    seniority: Optional[str] = Field(default=None, max_length=40)
    industry: Optional[str] = Field(default=None, max_length=120)
    languages: Optional[List[str]] = None
    openings_count: Optional[int] = Field(default=None, ge=1, le=500)
    application_deadline: Optional[date] = None
    screening_questions: Optional[List[Dict[str, str]]] = None


class JobOut(ORMOut):
    id: uuid.UUID
    organization_id: uuid.UUID
    opportunity_id: Optional[uuid.UUID] = None
    title: str
    slug: str
    department: Optional[str] = None
    summary: Optional[str] = None
    description: Optional[str] = None
    requirements: Optional[List[str]] = None
    skills_required: Optional[List[str]] = None
    preferred_skills: Optional[List[str]] = None
    experience_level: Optional[str] = None
    location: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    remote_eligible: bool
    work_mode: Optional[str] = None
    employment_type: Optional[str] = None
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    salary_currency: Optional[str] = None
    seniority: Optional[str] = None
    industry: Optional[str] = None
    openings_count: int
    application_deadline: Optional[date] = None
    screening_questions: Optional[List[Dict[str, str]]] = None
    status: str
    published_at: Optional[datetime] = None
    applications_count: int = 0


# --- Pipeline -----------------------------------------------------------------

class CandidateSummaryOut(BaseModel):
    person: Dict[str, Any]
    skills: List[Dict[str, Any]]
    has_live_consent: bool
    disclosure: Dict[str, bool]
    application_events_count: int
    events: List[Dict[str, Any]] = []


class ApplicationReviewOut(BaseModel):
    application: Dict[str, Any]
    job: Optional[Dict[str, Any]] = None
    candidate: Optional[CandidateSummaryOut] = None
    interview: Optional[Dict[str, Any]] = None
    offer: Optional[Dict[str, Any]] = None


class DecisionRequest(BaseModel):
    action: str  # advance | hold | reject
    note: Optional[str] = Field(default=None, max_length=1000)


# --- Interviews / offers ------------------------------------------------------

class InterviewCreate(BaseModel):
    application_id: uuid.UUID
    scheduled_at: datetime
    duration_minutes: int = Field(default=45, ge=5, le=480)
    mode: str = "video"
    interviewer_name: Optional[str] = Field(default=None, max_length=200)
    meeting_link: Optional[str] = Field(default=None, max_length=500)
    notes: Optional[str] = Field(default=None, max_length=2000)


class ScorecardCreate(BaseModel):
    criteria: Optional[List[Dict[str, Any]]] = None
    strengths: Optional[str] = Field(default=None, max_length=4000)
    concerns: Optional[str] = Field(default=None, max_length=4000)
    recommendation: Optional[str] = Field(default=None, max_length=20)
    notes: Optional[str] = Field(default=None, max_length=4000)


class ScorecardOut(ORMOut):
    id: uuid.UUID
    interview_id: uuid.UUID
    interviewer_user_id: uuid.UUID
    criteria: Optional[List[Dict[str, Any]]] = None
    strengths: Optional[str] = None
    concerns: Optional[str] = None
    recommendation: Optional[str] = None
    notes: Optional[str] = None


class OfferCreate(BaseModel):
    application_id: uuid.UUID
    salary_amount: Optional[float] = Field(default=None, ge=0)
    salary_currency: Optional[str] = Field(default="USD", max_length=8)
    equity: Optional[str] = Field(default=None, max_length=120)
    benefits_summary: Optional[str] = Field(default=None, max_length=4000)
    start_date: Optional[date] = None
    location: Optional[str] = Field(default=None, max_length=200)
    terms_summary: Optional[str] = Field(default=None, max_length=6000)
    expires_days: int = Field(default=7, ge=1, le=90)


# --- Document requests --------------------------------------------------------

class DocumentRequestCreate(BaseModel):
    application_id: uuid.UUID
    document_type: str = Field(min_length=1, max_length=60)
    purpose: Optional[str] = Field(default=None, max_length=240)


class DocumentRequestOut(ORMOut):
    id: uuid.UUID
    application_id: uuid.UUID
    organization_id: uuid.UUID
    document_type: str
    purpose: Optional[str] = None
    status: str
    note: Optional[str] = None
    created_at: datetime


# --- Analytics -----------------------------------------------------------------

class AnalyticsOut(BaseModel):
    open_jobs: int
    total_jobs: int
    applications_total: int
    by_status: Dict[str, int]
    needs_review: int
    interviews_scheduled: int
    offers_pending: int
    conversion: Dict[str, float]
