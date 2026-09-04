"""Phase 15 request schemas — Career Advisor + interview preparation."""

from __future__ import annotations

import uuid
from typing import List, Optional

from pydantic import BaseModel, Field


class PrepSessionCreateRequest(BaseModel):
    """Candidate-owned prep session container request."""

    opportunity_id: Optional[uuid.UUID] = None
    application_id: Optional[uuid.UUID] = None
    interview_id: Optional[uuid.UUID] = None
    focus_areas: Optional[List[str]] = Field(default=None, max_length=6)


class PrepQuestionsRequest(BaseModel):
    count: int = Field(default=5, ge=1, le=10)
    categories: Optional[List[str]] = Field(default=None, max_length=6)


class PrepAnswerRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    answer: str = Field(min_length=1, max_length=6000)
