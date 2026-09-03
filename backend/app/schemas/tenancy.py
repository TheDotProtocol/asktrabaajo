"""Organization + membership schemas."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.enums import ORG_KINDS
from app.schemas.common import ORMOut


class OrganizationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    slug: Optional[str] = Field(default=None, max_length=120)
    kind: str = "employer"

    @field_validator("kind")
    @classmethod
    def _kind_allowed(cls, v: str) -> str:
        if v not in ORG_KINDS:
            raise ValueError(f"kind must be one of {sorted(ORG_KINDS)}")
        return v


class OrganizationOut(ORMOut):
    id: uuid.UUID
    name: str
    slug: str
    kind: str
    status: str
    created_at: datetime


class MemberAddRequest(BaseModel):
    user_email: EmailStr
    role: str = Field(min_length=1, max_length=50)


class MemberUpdateRequest(BaseModel):
    role: str = Field(min_length=1, max_length=50)


class MemberOut(BaseModel):
    user_id: uuid.UUID
    email: str
    full_name: str
    role: str
    created_at: datetime


class MemberListResponse(BaseModel):
    organization_id: uuid.UUID
    members: List[MemberOut]


class MembershipListResponse(BaseModel):
    memberships: List[dict]
