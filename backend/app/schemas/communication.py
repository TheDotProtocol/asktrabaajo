"""Controlled Talent Outreach & Communication schemas (Phase 8)."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# --- Outreach (company -> candidate) ------------------------------------------

class OutreachCreate(BaseModel):
    person_id: uuid.UUID
    opportunity_id: Optional[uuid.UUID] = None
    message: str = Field(min_length=10, max_length=3000)
    context: Optional[str] = Field(default=None, max_length=300)


class OutreachCompanyOut(BaseModel):
    id: str
    organization_id: str
    organization_name: Optional[str] = None
    candidate: Dict[str, Any]
    opportunity_id: Optional[str] = None
    opportunity_title: Optional[str] = None
    application_id: Optional[str] = None
    message: str
    context: Optional[str] = None
    status: str
    requester_name: Optional[str] = None
    created_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    viewed_at: Optional[datetime] = None
    responded_at: Optional[datetime] = None
    note: Optional[str] = None


class DeclineRequest(BaseModel):
    note: Optional[str] = Field(default=None, max_length=1000)


class ReportRequest(BaseModel):
    note: Optional[str] = Field(default=None, max_length=1000)


class BlockRequest(BaseModel):
    reason: Optional[str] = Field(default=None, max_length=300)


# --- Conversations ------------------------------------------------------------

class OpenConversationRequest(BaseModel):
    application_id: uuid.UUID
    note: Optional[str] = Field(default=None, max_length=300)


class MessageSend(BaseModel):
    body: str = Field(min_length=1, max_length=4000)


class MessageOut(BaseModel):
    id: str
    conversation_id: str
    sender_user_id: str
    sender_side: str
    sender_name: Optional[str] = None
    body: str
    created_at: Optional[datetime] = None


class ConversationOut(BaseModel):
    id: str
    organization: Dict[str, Any]
    candidate: Dict[str, Any]
    counterpart: Optional[str] = None
    opportunity_id: Optional[str] = None
    opportunity_title: Optional[str] = None
    application_id: Optional[str] = None
    outreach_id: Optional[str] = None
    status: str
    created_at: Optional[datetime] = None
    last_message_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    unread_count: int = 0
    messages: Optional[List[MessageOut]] = None
