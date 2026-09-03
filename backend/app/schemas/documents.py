"""Controlled document schemas."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, model_validator

from app.schemas.common import ORMOut


class DocumentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    doc_type: str = Field(min_length=1, max_length=60)
    storage_key: Optional[str] = Field(default=None, max_length=255)
    mime_type: Optional[str] = Field(default=None, max_length=100)
    size_bytes: Optional[int] = Field(default=None, ge=0)


class DocumentOut(ORMOut):
    id: uuid.UUID
    name: str
    doc_type: str
    storage_key: Optional[str] = None
    mime_type: Optional[str] = None
    size_bytes: Optional[int] = None
    verification_status: str
    created_at: datetime


class GrantCreate(BaseModel):
    grantee_user_id: Optional[uuid.UUID] = None
    grantee_organization_id: Optional[uuid.UUID] = None
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
        return self


class GrantOut(ORMOut):
    id: uuid.UUID
    document_id: uuid.UUID
    grantee_user_id: Optional[uuid.UUID] = None
    grantee_organization_id: Optional[uuid.UUID] = None
    purpose: Optional[str] = None
    granted_at: datetime
    expires_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None


class DocumentWithGrants(BaseModel):
    document: DocumentOut
    grants: List[GrantOut] = []
