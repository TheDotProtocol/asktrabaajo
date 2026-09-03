"""Auth + current-user schemas."""
from __future__ import annotations

import uuid
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field

from app.schemas.common import PersonSummary


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=200)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=20)


class LogoutRequest(BaseModel):
    refresh_token: str = Field(min_length=20)


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in_seconds: int


class MembershipBrief(BaseModel):
    organization_id: uuid.UUID
    organization_name: str
    organization_slug: str
    organization_kind: str
    role: str


class MeResponse(BaseModel):
    user_id: uuid.UUID
    email: EmailStr
    full_name: str
    status: str
    email_verified: bool
    person: Optional[PersonSummary] = None
    memberships: List[MembershipBrief] = []
    permissions: List[str] = []
    super_admin: bool = False
