"""Privacy/visibility + profile completion schemas."""
from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from app.models.enums import VISIBILITY_LEVELS, VISIBILITY_SCOPES


class PrivacyUpdateRequest(BaseModel):
    settings: Dict[str, str] = Field(min_length=1)


class PrivacySettingsOut(BaseModel):
    """Visibility per Work ID section (default: private)."""

    settings: Dict[str, str]
    allowed_values: List[str] = sorted(VISIBILITY_LEVELS)
    scopes: List[str] = sorted(VISIBILITY_SCOPES)


class CompletionSection(BaseModel):
    met: bool
    weight: float
    threshold: Optional[int] = None
    count: Optional[int] = None


class CompletionOut(BaseModel):
    percent: int
    sections: Dict[str, CompletionSection]
    missing: List[str]
