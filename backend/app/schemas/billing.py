"""Commerce / billing / finance schemas (Phase 17)."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field


class SubscribeRequest(BaseModel):
    plan_code: str = Field(min_length=2, max_length=60)
    billing_interval: Optional[str] = Field(default=None, pattern="^(month|year)$")


class CancelRequest(BaseModel):
    reason: Optional[str] = Field(default="employer_requested", max_length=60)


class RefundRequest(BaseModel):
    transaction_id: uuid.UUID
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    reason: Optional[str] = Field(default=None, max_length=240)


class TransactionOut(BaseModel):
    transaction_id: uuid.UUID
    organization_id: uuid.UUID
    provider: str
    provider_payment_id: Optional[str] = None
    amount: str
    currency: str
    status: str
    description: Optional[str] = None
    idempotency_key: Optional[str] = None
    succeeded_at: Optional[str] = None
    failed_at: Optional[str] = None
    refunded_amount: str


class RefundOut(BaseModel):
    refund_id: uuid.UUID
    transaction_id: uuid.UUID
    provider_refund_id: Optional[str] = None
    amount: str
    currency: str
    status: str
    reason: Optional[str] = None
    authorized_by_user_id: Optional[uuid.UUID] = None
    succeeded_at: Optional[str] = None


class WebhookOut(BaseModel):
    event_id: str
    status: str