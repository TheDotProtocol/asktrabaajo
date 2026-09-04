"""Government intelligence response envelopes — aggregate cells only."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class GovernmentFilters(BaseModel):
    country: Optional[str] = Field(default=None, max_length=80)
    state_province: Optional[str] = Field(default=None, max_length=80)
    city: Optional[str] = Field(default=None, max_length=80)
    industry: Optional[str] = Field(default=None, max_length=80)
    skill: Optional[str] = Field(default=None, max_length=80)


class GovernmentEnvelope(BaseModel):
    privacy: str
    privacy_threshold: int
    freshness: str
    generated_at: str
    period: str
    filters: Dict[str, str] = Field(default_factory=dict)
    status: str
    extra: Dict[str, Any] = Field(default_factory=dict)

    model_config = {"extra": "allow"}
