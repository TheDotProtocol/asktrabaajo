"""Talent Graph API schemas (Phase 7).

Payloads are intentionally discovery-safe: employer-facing candidate shapes
never carry contact/private Work ID fields — progressive disclosure is
enforced in the service layer and reflected in these response types.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# --- skill taxonomy -----------------------------------------------------------

class TaxonomySkillOut(BaseModel):
    id: uuid.UUID
    name: str
    category: str
    subcategory: Optional[str] = None
    description: Optional[str] = None
    status: str


class TaxonomyListOut(BaseModel):
    total: int
    page: int
    page_size: int
    categories: List[str]
    items: List[TaxonomySkillOut]


class SkillDetailOut(BaseModel):
    id: str
    name: str
    category: str
    subcategory: Optional[str] = None
    description: Optional[str] = None
    status: str
    aliases: List[str]
    parents: List[Dict[str, str]]
    related: List[Dict[str, str]]


class NormalizeRequest(BaseModel):
    text: str = Field(min_length=1, max_length=200)


class NormalizeResult(BaseModel):
    raw: str
    normalized: str
    canonical: Optional[Dict[str, str]] = None  # {id, name} when resolved


# --- candidate discovery --------------------------------------------------------

class SkillSummaryOut(BaseModel):
    name: str
    level: Optional[str] = None


class DisclosureOut(BaseModel):
    profile: bool
    skills_visible: bool
    experience_visible: bool
    contact_visible: bool


class CandidateSearchItem(BaseModel):
    person_id: str
    name: Optional[str] = None
    headline: Optional[str] = None
    location: Optional[str] = None
    skills: List[SkillSummaryOut]
    experience_years: Optional[float] = None
    latest_role: Optional[Dict[str, Any]] = None
    disclosure: DisclosureOut


class CandidateSearchList(BaseModel):
    items: List[CandidateSearchItem]
    total: int
    page: int
    page_size: int


# --- ranked matches -------------------------------------------------------------

class MatchedCandidateOut(BaseModel):
    person_id: str
    summary: CandidateSearchItem
    percent: int
    score: float
    mode: str
    coverage: float
    strengths: List[str]
    gaps: List[str]
    matched_skills: List[str]
    missing_skills: List[str]


class MatchedCandidateList(BaseModel):
    items: List[MatchedCandidateOut]
    total: int
    page: int
    page_size: int
    opportunity_id: str


# --- saved / pools -----------------------------------------------------------

class SaveCandidateRequest(BaseModel):
    note: Optional[str] = Field(default=None, max_length=2000)
    tags: Optional[List[str]] = None


class SavedCandidateOut(BaseModel):
    id: str
    person_id: str
    name: Optional[str] = None
    headline: Optional[str] = None
    note: Optional[str] = None
    tags: Optional[List[str]] = None
    saved_at: datetime
    context: str


class PoolCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=2000)


class PoolMemberAdd(BaseModel):
    person_id: uuid.UUID
    note: Optional[str] = Field(default=None, max_length=2000)


class TalentPoolOut(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    created_at: datetime
    member_count: int


class PoolMemberOut(BaseModel):
    person_id: str
    name: Optional[str] = None
    headline: Optional[str] = None
    note: Optional[str] = None
    added_at: datetime


class TalentPoolDetailOut(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    member_count: int
    members: List[PoolMemberOut]


# --- opportunity requirements / profile --------------------------------------

class RequirementOut(BaseModel):
    id: str
    skill: Optional[str] = None
    raw_text: str
    requirement_kind: str
    min_years: Optional[float] = None


class CandidateProfileOut(BaseModel):
    """Discovery-safe employer candidate view (dict payload passthrough)."""

    payload: Dict[str, Any]
