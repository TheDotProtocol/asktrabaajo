"""Shared schema primitives."""
from __future__ import annotations

import uuid
from typing import Optional

from pydantic import BaseModel, ConfigDict


class ORMOut(BaseModel):
    """Base response model that reads from ORM objects."""

    model_config = ConfigDict(from_attributes=True)


class PersonSummary(ORMOut):
    """The PERSON record summary (identity header)."""

    id: uuid.UUID
    headline: Optional[str] = None
    summary: Optional[str] = None
    location: Optional[str] = None
    country_code: Optional[str] = None


class MessageResponse(BaseModel):
    message: str
