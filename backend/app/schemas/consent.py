"""Consent schemas."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, model_validator

from app.models.enums import CONSENT_SCOPES


class ConsentCreate(BaseModel):
    grantee_user_id: Optional[uuid.UUID] = None
    grantee_organization_id: Optional[uuid.UUID] = None
    resource_scope: str
    purpose: Optional[str] = Field(default=None, max_length=240)
    expires_at: Optional[datetime] = None

    @model_validator(mode="after")
    def _check_grantee(self):
        has_user = self.grantee_user_id is not None
        has_org = self.grantee_organization_id is not None
        if has_user == has_org:
            raise ValueError(
                "Provide exactly one of grantee_user_id or grantee_organization_id."
            )
        if self.resource_scope not in CONSENT_SCOPES:
            raise ValueError(
                f"resource_scope must be one of {sorted(CONSENT_SCOPES)}"
            )
        return self


class ConsentOut(BaseModel):
    id: uuid.UUID
    person_id: uuid.UUID
    grantee_user_id: Optional[uuid.UUID] = None
    grantee_organization_id: Optional[uuid.UUID] = None
    resource_scope: str
    purpose: Optional[str] = None
    granted_at: datetime
    expires_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    active: bool = True
