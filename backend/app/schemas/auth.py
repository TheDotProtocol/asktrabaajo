"""Auth + current-user schemas (Phase 4: password lifecycle, sessions,
email verification, MFA foundation)."""
from __future__ import annotations

import uuid
from datetime import datetime
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


class LoginResult(BaseModel):
    """Login outcome — either a token pair or an MFA challenge."""

    mfa_required: bool = False
    mfa_token: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in_seconds: Optional[int] = None


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=20)
    new_password: str = Field(min_length=8, max_length=128)


class VerifyEmailRequest(BaseModel):
    token: str = Field(min_length=20)


class EmailVerificationMessage(BaseModel):
    message: str
    email_verified: bool


class SessionOut(BaseModel):
    id: uuid.UUID
    created_at: datetime
    expires_at: datetime
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


class MfaEnableResponse(BaseModel):
    secret: str
    otpauth_uri: str
    confirmed: bool


class MfaCodeRequest(BaseModel):
    code: str = Field(min_length=6, max_length=6)


class MfaLoginRequest(BaseModel):
    mfa_token: str = Field(min_length=20)
    code: str = Field(min_length=6, max_length=6)


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
    mfa_enabled: bool = False
    person: Optional[PersonSummary] = None
    memberships: List[MembershipBrief] = []
    permissions: List[str] = []
    super_admin: bool = False
