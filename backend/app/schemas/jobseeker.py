"""Jobseeker Career OS schemas — work DNA, goals, opportunities, applications.

All responses here describe data the caller owns (their career journey) or
the public/approved opportunity catalogue. Private Work ID sections never
appear in opportunity/application payloads except as explicit, minimal
candidate-side echoes (e.g. applied_at).
"""
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.schemas.common import ORMOut


# --- Work DNA ----------------------------------------------------------------

class DnaQuestionOut(BaseModel):
    key: str
    question: str
    options: List[Dict[str, str]]


class DnaSubmitRequest(BaseModel):
    answers: Dict[str, str]


class DnaDimensionOut(BaseModel):
    key: str
    label: str
    signal: float
    confidence: float


class DnaProfileOut(ORMOut):
    id: uuid.UUID
    version: str
    source: str
    status: str
    dimensions: Optional[List[DnaDimensionOut]] = None
    completed_at: Optional[datetime] = None


# --- Career goals ------------------------------------------------------------

class CareerGoalCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    target_role: Optional[str] = Field(default=None, max_length=200)
    target_industries: Optional[List[str]] = None
    target_locations: Optional[List[str]] = None
    preferred_work_modes: Optional[List[str]] = None
    min_salary: Optional[float] = Field(default=None, ge=0)
    salary_currency: Optional[str] = Field(default="USD", max_length=8)
    open_to_relocation: bool = False
    open_to_remote: bool = True
    availability: Optional[str] = Field(default=None, max_length=120)
    is_primary: bool = True


class CareerGoalUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=200)
    target_role: Optional[str] = Field(default=None, max_length=200)
    target_industries: Optional[List[str]] = None
    target_locations: Optional[List[str]] = None
    preferred_work_modes: Optional[List[str]] = None
    min_salary: Optional[float] = Field(default=None, ge=0)
    salary_currency: Optional[str] = Field(default=None, max_length=8)
    open_to_relocation: Optional[bool] = None
    open_to_remote: Optional[bool] = None
    availability: Optional[str] = Field(default=None, max_length=120)
    is_primary: Optional[bool] = None


class CareerGoalOut(ORMOut):
    id: uuid.UUID
    title: str
    target_role: Optional[str] = None
    target_industries: Optional[List[str]] = None
    target_locations: Optional[List[str]] = None
    preferred_work_modes: Optional[List[str]] = None
    min_salary: Optional[float] = None
    salary_currency: Optional[str] = None
    open_to_relocation: bool
    open_to_remote: bool
    availability: Optional[str] = None
    is_primary: bool
    status: str


# --- Opportunities -----------------------------------------------------------

class OpportunityOut(ORMOut):
    id: uuid.UUID
    company_name: str
    title: str
    summary: Optional[str] = None
    location: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    remote_eligible: bool
    work_mode: Optional[str] = None
    employment_type: Optional[str] = None
    experience_level: Optional[str] = None
    seniority: Optional[str] = None
    industry: Optional[str] = None
    skills_required: Optional[List[str]] = None
    min_salary: Optional[float] = None
    max_salary: Optional[float] = None
    salary_currency: Optional[str] = None
    closing_at: Optional[date] = None
    source: str


class ComponentOut(BaseModel):
    score: float
    reason: str
    matched: Optional[List[str]] = None
    missing: Optional[List[str]] = None


class OpportunityMatchOut(BaseModel):
    opportunity_id: uuid.UUID
    percent: int
    score: float
    components: Dict[str, ComponentOut]
    strengths: List[str]
    gaps: List[str]
    missing_skills: List[str]
    opportunity: Optional[OpportunityOut] = None
    saved: bool = False
    applied: bool = False


class OpportunityListOut(BaseModel):
    items: List[OpportunityMatchOut]
    total: int
    page: int
    page_size: int


# --- Applications ------------------------------------------------------------

class ApplicationOut(ORMOut):
    id: uuid.UUID
    opportunity_id: uuid.UUID
    status: str
    cover_note: Optional[str] = None
    applied_at: Optional[datetime] = None
    last_activity_at: datetime
    opportunity: Optional[OpportunityOut] = None


class ApplicationEventOut(ORMOut):
    id: uuid.UUID
    from_status: Optional[str] = None
    to_status: str
    note: Optional[str] = None
    created_at: datetime


class ApplicationDetailOut(BaseModel):
    application: ApplicationOut
    timeline: List[ApplicationEventOut]
    opportunity: Optional[OpportunityOut] = None
    has_interview: bool = False
    has_offer: bool = False


class ApplyRequest(BaseModel):
    opportunity_id: uuid.UUID
    cover_note: Optional[str] = Field(default=None, max_length=4000)


class BatchApplyRequest(BaseModel):
    opportunity_ids: List[uuid.UUID] = Field(..., min_length=1, max_length=20)


# --- Interviews / offers -----------------------------------------------------

class InterviewOut(ORMOut):
    id: uuid.UUID
    application_id: uuid.UUID
    scheduled_at: datetime
    duration_minutes: int
    mode: str
    meeting_link: Optional[str] = None
    interviewer_name: Optional[str] = None
    status: str
    reschedule_reason: Optional[str] = None
    reschedule_count: int


class RescheduleRequest(BaseModel):
    proposed_at: Optional[datetime] = None
    reason: str = Field(min_length=5, max_length=500)


class OfferOut(ORMOut):
    id: uuid.UUID
    application_id: uuid.UUID
    status: str
    salary_amount: Optional[float] = None
    salary_currency: Optional[str] = None
    equity: Optional[str] = None
    benefits_summary: Optional[str] = None
    start_date: Optional[date] = None
    location: Optional[str] = None
    terms_summary: Optional[str] = None
    responded_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None


class OfferDecisionRequest(BaseModel):
    decision: str  # accept | decline


# --- Advisor / development ---------------------------------------------------

class GapOut(BaseModel):
    kind: str
    title: str
    detail: str
    skill: Optional[str] = None
    action_type: Optional[str] = None


class LearningRecommendationOut(BaseModel):
    skill: str
    recommendation: str
    kind: str


class AdvisorSnapshotOut(BaseModel):
    summary: str
    current_position: Dict[str, Optional[str]]
    roles_held: List[str]
    strongest_skills: List[str]
    career_goal: Dict[str, Optional[str]]
    gaps: List[GapOut]
    learning_recommendations: List[LearningRecommendationOut]
    next_actions: List[str]
    disclaimer: str


# --- Milestones / dashboard --------------------------------------------------

class MilestoneCreate(BaseModel):
    kind: str = Field(min_length=1, max_length=32)
    title: str = Field(min_length=1, max_length=200)
    occurred_on: date
    description: Optional[str] = Field(default=None, max_length=2000)


class MilestoneOut(ORMOut):
    id: uuid.UUID
    kind: str
    title: str
    occurred_on: date
    description: Optional[str] = None


class NotificationOut(ORMOut):
    id: uuid.UUID
    kind: str
    title: str
    body: Optional[str] = None
    read_at: Optional[datetime] = None
    created_at: datetime


class DashboardOut(BaseModel):
    profile_completion: Optional[Dict[str, Any]] = None
    work_dna_status: str
    has_career_goal: bool
    stats: Dict[str, Any]
    upcoming_interviews: List[InterviewOut]
    recent_applications: List[ApplicationOut]
    recommended: List[OpportunityMatchOut]
    advisor: Optional[AdvisorSnapshotOut] = None
    unread_notifications: int
