"""Payment domain (Phase 17).

Provider references ONLY — CVV, raw card numbers and private credentials
are never stored. Money is NUMERIC with explicit currency codes.

- ``PaymentTransaction`` — one provider payment attempt with an
  idempotency key, status lifecycle and provider references.
- ``PaymentRefund`` — idempotent, authorized refund against a
  transaction (never more than the paid amount).
- ``PaymentWebhookEvent`` — provider event envelope: signature-verified,
  replay-protected (unique event id), duplicate-safe. Raw payloads are
  never stored.

The PaymentProvider abstraction (services/payments.py) is provider-neutral;
the default is a deterministic mock/sandbox provider. No real money, no
production provider is activated.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from app.db.base import Base
from app.models.enums import PAYMENT_STATUS_PENDING, REFUND_STATUS_PENDING
from app.models.identity import TimestampMixin

UUID = Uuid
MONEY = Numeric(14, 2)


class PaymentTransaction(Base, TimestampMixin):
    """One provider payment attempt."""

    __tablename__ = "payment_transactions"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_payment_idempotency"),
        Index("ix_payments_org_status", "organization_id", "status"),
        Index("ix_payments_provider_ref", "provider_payment_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    provider: Mapped[str] = mapped_column(String(40), nullable=False)
    provider_customer_id: Mapped[Optional[str]] = mapped_column(String(120))
    provider_payment_id: Mapped[Optional[str]] = mapped_column(String(120))
    amount: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default=PAYMENT_STATUS_PENDING, nullable=False
    )
    description: Mapped[Optional[str]] = mapped_column(String(240))
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(120))
    failure_code: Mapped[Optional[str]] = mapped_column(String(60))
    created_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID, ForeignKey("users.id", ondelete="SET NULL")
    )
    succeeded_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    failed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    refunded_amount: Mapped[Decimal] = mapped_column(
        MONEY, default=Decimal("0.00"), nullable=False
    )


class PaymentRefund(Base, TimestampMixin):
    """Idempotent, authorized refund."""

    __tablename__ = "payment_refunds"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_refund_idempotency"),
        Index("ix_refunds_transaction", "transaction_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    transaction_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("payment_transactions.id", ondelete="CASCADE"),
        nullable=False,
    )
    provider_refund_id: Mapped[Optional[str]] = mapped_column(String(120))
    amount: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), default=REFUND_STATUS_PENDING, nullable=False
    )
    reason: Mapped[Optional[str]] = mapped_column(String(240))
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(120))
    authorized_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID, ForeignKey("users.id", ondelete="SET NULL")
    )
    succeeded_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    failed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class PaymentWebhookEvent(Base):
    """Signature-verified provider event envelope (no raw payload stored)."""

    __tablename__ = "payment_webhook_events"
    __table_args__ = (
        UniqueConstraint("provider", "event_id", name="uq_webhook_event_id"),
        Index("ix_webhook_events_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    provider: Mapped[str] = mapped_column(String(40), nullable=False)
    event_id: Mapped[str] = mapped_column(String(120), nullable=False)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    signature_valid: Mapped[Optional[bool]] = mapped_column()
    # Bounded, non-sensitive processing metadata.
    note: Mapped[Optional[str]] = mapped_column(String(240))
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))