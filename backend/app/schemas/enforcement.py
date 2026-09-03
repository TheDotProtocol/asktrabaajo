"""Enforcement + appeals schemas (Phase 11)."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class EnforcementActionCreate(BaseModel):
    case_id: Optional[uuid.UUID] = None
    target_user_id: Optional[uuid.UUID] = None
    target_organization_id: Optional[uuid.UUID] = None
    action_type: str = Field(min_length=1, max_length=40)
    scope: str = Field(min_length=1, max_length=40)
    reason_code: str = Field(min_length=1, max_length=40)
    note: Optional[str] = Field(default=None, max_length=500)
    effective_at: datetime
    expires_at: Optional[datetime] = None


class EnforcementActionApprove(BaseModel):
    approval_note: Optional[str] = Field(default=None, max_length=500)


class EnforcementActionReject(BaseModel):
    rejection_note: Optional[str] = Field(default=None, max_length=500)


class EnforcementActionRevoke(BaseModel):
    revoke_note: Optional[str] = Field(default=None, max_length=500)


class EnforcementActionOut(BaseModel):
    id: str
    governance_case_id: Optional[str] = None
    target_user_id: Optional[str] = None
    target_organization_id: Optional[str] = None
    action_type: str
    scope: str
    reason_code: str
    status: str
    stored_status: str
    created_by: str
    approved_by: Optional[str] = None
    effective_at: datetime
    expires_at: Optional[datetime] = None
    activated_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    supersedes_id: Optional[str] = None
    note: Optional[str] = None
    created_at: Optional[datetime] = None
    audit: Optional[List[Dict[str, Any]]] = None


class EnforcementActionListOut(BaseModel):
    items: List[EnforcementActionOut]
    total: int
    page: int
    page_size: int


class DerivedUserStateOut(BaseModel):
    user_id: str
    state: str
    active_restrictions: List[Dict[str, Any]] = []
    derived_at: datetime


class AppealCreate(BaseModel):
    enforcement_action_id: uuid.UUID
    reason_code: str = Field(min_length=1, max_length=40)
    statement: str = Field(min_length=1, max_length=4000)


class AppealAssign(BaseModel):
    reviewer_id: uuid.UUID


class AppealDecide(BaseModel):
    decision: str = Field(min_length=1, max_length=20)
    decision_note: str = Field(min_length=1, max_length=1000)
    review_note: Optional[str] = Field(default=None, max_length=4000)


class AppealOut(BaseModel):
    id: str
    enforcement_action_id: str
    appellant_user_id: str
    reason_code: str
    statement: Optional[str] = None
    status: str
    assigned_reviewer_id: Optional[str] = None
    decision: Optional[str] = None
    decision_note: Optional[str] = None
    review_note: Optional[str] = None
    decided_by: Optional[str] = None
    decided_at: Optional[datetime] = None
    withdrawn_at: Optional[datetime] = None
    superseding_action_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    audit: Optional[List[Dict[str, Any]]] = None


class AppealListOut(BaseModel):
    items: List[AppealOut]
    total: int
    page: int
    page_size: int
