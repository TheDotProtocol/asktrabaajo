"""Athena API schemas (Phase 14)."""
from __future__ import annotations

import uuid
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class AthenaSessionCreate(BaseModel):
    mode: str
    purpose: Optional[str] = Field(default=None, max_length=240)
    organization_id: Optional[uuid.UUID] = None


class AthenaSessionOut(BaseModel):
    session_id: uuid.UUID
    mode: str
    purpose: Optional[str] = None
    organization_id: Optional[uuid.UUID] = None
    status: str
    expires_at: Optional[str] = None


class AthenaMessageRequest(BaseModel):
    session_id: uuid.UUID
    message: str = Field(min_length=1, max_length=4000)


class AthenaConfirmRequest(BaseModel):
    confirmation_id: uuid.UUID
    approve: bool


class AthenaConfirmOut(BaseModel):
    status: str
    confirmation_id: uuid.UUID
    tool: Optional[str] = None
    result: Optional[Dict] = None


class AthenaMessageOut(BaseModel):
    session_id: uuid.UUID
    reply: str
    tool_results: List[Dict] = Field(default_factory=list)
    pending_confirmations: List[Dict] = Field(default_factory=list)
    error: Optional[str] = None


class AthenaToolOut(BaseModel):
    name: str
    description: str
    risk: str
    read_only: bool
    data_scope: str
    confirmation_required: bool


class AthenaUsageOut(BaseModel):
    feature: str
    status: str
    total_tokens: int
    estimated_cost: Optional[float] = None
    created_at: str


class AthenaStatusOut(BaseModel):
    """Safe provider/capability status — never includes secrets or env values."""

    available: bool
    state: str  # available | not_configured | temporarily_unavailable
    modes: List[str]