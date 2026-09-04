"""Commerce / Billing domain (Phase 17).

Employer/company functionality is the only paid surface — the jobseeker's
core (Work ID, discovery, applications, career intelligence) stays free.
Pricing is CONFIGURABLE: the seeded catalog contains only the FREE plan
(price 0); paid plans are configuration-driven catalog rows that an
operator adds when pricing is decided. No final prices are invented here.

Money is stored as NUMERIC (never binary float) with explicit currency
codes. All amounts are in the plan/subscription currency; there is no
silent currency conversion and no assumed exchange rate.

- ``Plan`` — configurable catalog entry (code, interval, currency,
  NUMERIC price, published flag).
- ``PlanEntitlement`` — plan -> feature code -> numeric limit (NULL =
  unlimited). Feature codes are the controlled ENTITLEMENT_CODES set.
- ``Subscription`` — ORGANIZATION-owned (never an individual employee's).
  Explicit state machine (trial/active/past_due/paused/cancelled/expired)
  enforced by the commerce service; history rows are kept, one live
  subscription per org is enforced by the service.
- ``Invoice`` — NUMERIC money record (subtotal/tax/total) with bounded
  JSON line items and an explicit lifecycle.
- ``UsageRecord`` — tenant-scoped usage for countable entitlements.

Tenancy: every row is organization-scoped; service + API layers enforce
the tenant boundary. RLS: designed for future stage-B/C groups (not
enabled in this phase — see PHASE_13_RLS_MATRIX).
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON, Uuid

from app.db.base import Base
from app.models.enums import (
    BILLING_INTERVAL_MONTH,
    INVOICE_STATUS_DRAFT,
    SUBSCRIPTION_STATUS_ACTIVE,
)
from app.models.identity import TimestampMixin

UUID = Uuid
MONEY = Numeric(14, 2)


class Plan(Base, TimestampMixin):
    """Configurable commerce plan catalog entry."""

    __tablename__ = "commerce_plans"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    billing_interval: Mapped[str] = mapped_column(
        String(16), default=BILLING_INTERVAL_MONTH, nullable=False
    )
    currency: Mapped[str] = mapped_column(String(8), default="USD", nullable=False)
    price: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0.00"), nullable=False)
    # ``active`` keeps the catalog entry; ``published`` makes it purchasable.
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    published: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    seat_included: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # Attribute renamed away from SQLAlchemy's reserved ``metadata``; DB
    # column stays ``metadata`` (see migration 0014).
    plan_metadata: Mapped[Optional[dict]] = mapped_column("metadata", JSON)


class PlanEntitlement(Base, TimestampMixin):
    """One entitlement on a plan (feature code + numeric limit)."""

    __tablename__ = "commerce_plan_entitlements"
    __table_args__ = (
        UniqueConstraint(
            "plan_id", "entitlement_code", name="uq_plan_entitlement_feature"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID, ForeignKey("commerce_plans.id", ondelete="CASCADE"), nullable=False
    )
    entitlement_code: Mapped[str] = mapped_column(String(60), nullable=False)
    # NULL limit_value = unlimited.
    limit_value: Mapped[Optional[Decimal]] = mapped_column(MONEY)
    unit: Mapped[Optional[str]] = mapped_column(String(40))


class Subscription(Base, TimestampMixin):
    """Organization-owned subscription with explicit lifecycle."""

    __tablename__ = "commerce_subscriptions"
    __table_args__ = (
        Index("ix_subscriptions_org_status", "organization_id", "status"),
        Index("ix_subscriptions_provider_ref", "provider_subscription_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID, ForeignKey("commerce_plans.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(20), default=SUBSCRIPTION_STATUS_ACTIVE, nullable=False
    )
    billing_interval: Mapped[str] = mapped_column(
        String(16), default=BILLING_INTERVAL_MONTH, nullable=False
    )
    currency: Mapped[str] = mapped_column(String(8), default="USD", nullable=False)
    price_amount: Mapped[Decimal] = mapped_column(
        MONEY, default=Decimal("0.00"), nullable=False
    )
    seat_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # Provider references only — never payment credentials.
    provider_subscription_id: Mapped[Optional[str]] = mapped_column(String(120))
    trial_ends_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    current_period_start: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True)
    )
    current_period_end: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True)
    )
    cancel_at_period_end: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=False
    )
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    cancel_reason: Mapped[Optional[str]] = mapped_column(String(60))
    note: Mapped[Optional[str]] = mapped_column(String(300))


class Invoice(Base, TimestampMixin):
    """NUMERIC invoice record with an explicit lifecycle."""

    __tablename__ = "commerce_invoices"
    __table_args__ = (
        Index("ix_invoices_org_status", "organization_id", "status"),
        UniqueConstraint("invoice_number", name="uq_invoice_number"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    invoice_number: Mapped[str] = mapped_column(String(40), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), default="USD", nullable=False)
    subtotal_amount: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    tax_amount: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0.00"), nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), default=INVOICE_STATUS_DRAFT, nullable=False
    )
    # Bounded line items (description + numeric amount), never free-form PII.
    items: Mapped[Optional[list]] = mapped_column(JSON)
    # Optional link to the payment that settled this invoice.
    payment_transaction_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID)
    issued_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    due_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    note: Mapped[Optional[str]] = mapped_column(String(300))


class UsageRecord(Base):
    """Tenant-scoped usage for countable entitlements."""

    __tablename__ = "usage_records"
    __table_args__ = (
        Index("ix_usage_records_org_feature", "organization_id", "feature", "recorded_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    feature: Mapped[str] = mapped_column(String(60), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    actor_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID, ForeignKey("users.id", ondelete="SET NULL")
    )
    reference_type: Mapped[Optional[str]] = mapped_column(String(60))
    reference_id: Mapped[Optional[str]] = mapped_column(String(64))
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )