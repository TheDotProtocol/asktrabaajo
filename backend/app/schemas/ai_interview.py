"""AI Interview Engine — API request/response schemas (Phase 16)."""

from __future__ import annotations

import uuid
from typing import List, Optional

from pydantic import BaseModel, Field


class AiInterviewCreateRequest(BaseModel):
    candidate_person_id: uuid.UUID
    application_id: Optional[uuid.UUID] = None
    opportunity_id: Optional[uuid.UUID] = None
    interview_id: Optional[uuid.UUID] = None
    interview_type: str = "screening"
    duration_minutes: int = Field(default=30, ge=10, le=120)
    question_count: int = Field(default=5, ge=1, le=10)
    difficulty: str = "medium"
    language: str = "en"
    competencies: Optional[List[str]] = Field(default=None, max_length=8)
    evaluation_dimensions: Optional[List[str]] = None
    introduction: Optional[str] = Field(default=None, max_length=2000)
    closing: Optional[str] = Field(default=None, max_length=1000)
    voice_enabled: bool = False
    video_enabled: bool = False
    consent_required: bool = True


class AiInterviewCreateOut(BaseModel):
    session_id: uuid.UUID
    entry_token: str  # returned exactly once — only the hash is stored
    expires_at: Optional[str] = None


class ConsentRequest(BaseModel):
    mic: bool = False
    camera: bool = False
    recording: bool = False


class IntegritySignalRequest(BaseModel):
    signal_type: str
    detail: Optional[str] = Field(default=None, max_length=120)


class ResponseRequest(BaseModel):
    question_id: uuid.UUID
    answer: str = Field(min_length=1, max_length=4000)


class RepeatRequest(BaseModel):
    question_id: uuid.UUID


class DecisionRequest(BaseModel):
    decision: str
    note: Optional[str] = Field(default=None, max_length=500)


class EntryTokenIn(BaseModel):
    entry_token: str = Field(min_length=8, max_length=200)