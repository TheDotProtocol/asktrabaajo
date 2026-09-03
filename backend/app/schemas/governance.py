"""Platform governance schemas (Phase 9)."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ReportCreate(BaseModel):
    target_type: str = Field(min_length=1, max_length=40)
    target_id: str = Field(min_length=1, max_length=64)
    category: str = Field(min_length=1, max_length=40)
    description: str = Field(min_length=10, max_length=5000)
    organization_id: Optional[uuid.UUID] = None
    severity: str = Field(default="medium", max_length=16)
    evidence_refs: Optional[List[Dict[str, Any]]] = Field(default=None, max_length=10)


class ReportStatusUpdate(BaseModel):
    status: str = Field(min_length=1, max_length=20)


class ReportAssign(BaseModel):
    moderator_user_id: Optional[uuid.UUID] = None


class ReportNoteCreate(BaseModel):
    body: str = Field(min_length=1, max_length=3000)


class ReportResolve(BaseModel):
    resolution: str = Field(min_length=10, max_length=5000)


class ReportOut(BaseModel):
    id: str
    reporter_user_id: str
    target_type: str
    target_id: str
    organization_id: Optional[str] = None
    organization_name: Optional[str] = None
    category: str
    severity: str
    status: str
    description: str
    evidence_refs: List[Dict[str, Any]] = []
    assigned_moderator_id: Optional[str] = None
    assigned_moderator_name: Optional[str] = None
    resolution: Optional[str] = None
    resolved_at: Optional[datetime] = None
    reopened_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    notes: Optional[List[Dict[str, Any]]] = None
    audit: Optional[List[Dict[str, Any]]] = None


class ReportListOut(BaseModel):
    items: List[ReportOut]
    total: int
    page: int
    page_size: int


class GovernanceDashboardOut(BaseModel):
    total: int
    open: int
    by_status: Dict[str, int]
    by_severity: Dict[str, int]