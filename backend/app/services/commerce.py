"""Commerce / billing service (Phase 17).

Centralized plan/subscription/entitlement/invoice/usage logic. Routes and
(soon) paid features resolve entitlements through:
User -> Organization -> Subscription -> Plan -> Entitlement.

Principles:
- Jobseeker core stays free; only employer/company functionality may be
  paid; pricing is configuration (catalog rows), never invented here.
- Subscriptions are ORGANIZATION-owned; explicit state machine.
- Money is Decimal over NUMERIC columns; amounts are validated.
- Entitlement limits are centralized; no inline billing checks in routes.
- Every state change is audited; org-scoped events are emitted.
"""

from __future__ import annotations

import uuid
from datetime import timedelta
from decimal import Decimal
from typing import Dict, List, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import (
    InvalidInputError,
    NotFoundError,
    PermissionDeniedError,
)
from app.core.timeutil import utc_now_naive
from app.models.commerce import (
    Invoice,
    Plan,
    PlanEntitlement,
    Subscription,
    UsageRecord,
)
from app.models.enums import (
    AUDIT_ACTION_INVOICE_ISSUED,
    AUDIT_ACTION_INVOICE_PAID,
    AUDIT_ACTION_SUBSCRIPTION_CANCELLED,
    AUDIT_ACTION_SUBSCRIPTION_CREATED,
    AUDIT_ACTION_SUBSCRIPTION_EXPIRED,
    AUDIT_ACTION_USAGE_RECORDED,
    BILLING_INTERVALS,
    ENTITLEMENT_CODES,
    INVOICE_STATUS_DRAFT,
    INVOICE_STATUS_ISSUED,
    INVOICE_STATUS_PAID,
    INVOICE_STATUS_VOID,
    NOTIFICATION_KIND_BILLING,
    PLAN_CODE_FREE,
    SUBSCRIPTION_STATUS_ACTIVE,
    SUBSCRIPTION_STATUS_CANCELLED,
    SUBSCRIPTION_STATUS_EXPIRED,
    SUBSCRIPTION_STATUS_PAST_DUE,
    SUBSCRIPTION_STATUS_PAUSED,
    SUBSCRIPTION_STATUS_TRIAL,
    SUBSCRIPTION_TRANSITIONS,
)
from app.models.tenancy import Membership, Organization
from app.services import audit as audit_service
from app.services import events, notifications

# Entitlement codes that map to countable platform tables for usage display.
_COUNTABLE_FEATURES: Dict[str, str] = {
    "jobs.create": "job_postings",
    "jobs.active": "job_postings_active",
    "candidate.search": "candidate_search_events",
    "candidate.outreach": "outreach_requests",
    "ai.athena": "ai_usage_log",
    "ai.interview": "ai_interview_sessions",
}


# --- Catalog --------------------------------------------------------------------

def ensure_default_catalog(db: Session) -> None:
    """Idempotently ensure the FREE plan + entitlements exist.

    Mirrors the migration 0014 seed so the test harness (create_all from
    models) and any runtime environment always have the free plan.
    """
    if db.scalar(select(Plan).where(Plan.code == PLAN_CODE_FREE)) is not None:
        return
    plan = Plan(
        id=uuid.UUID("10000000-0000-4000-8000-000000000001"),
        code=PLAN_CODE_FREE,
        name="Free",
        description=(
            "Free plan for organizations on the AskTrabaajo platform. "
            "Jobseeker core functionality is always free."
        ),
        billing_interval="month",
        currency="USD",
        price=Decimal("0.00"),
        active=True,
        published=True,
    )
    db.add(plan)
    db.flush()
    FREE_ENTITLEMENTS = [
        ("jobs.create", "5"),
        ("jobs.active", "5"),
        ("candidate.search", "20"),
        ("candidate.outreach", "5"),
        ("ai.athena", "20"),
        ("ai.interview", "0"),
        ("analytics", None),
        ("premium_support", "0"),
    ]
    for i, (code, limit) in enumerate(FREE_ENTITLEMENTS):
        db.add(
            PlanEntitlement(
                id=uuid.UUID(f"10000000-0000-4000-8000-{1000 + i:012d}"),
                plan_id=plan.id,
                entitlement_code=code,
                limit_value=Decimal(limit) if limit is not None else None,
            )
        )
    db.commit()


def list_plans(db: Session, *, published_only: bool = True) -> List[Plan]:
    ensure_default_catalog(db)
    query = select(Plan).where(Plan.active.is_(True))
    if published_only:
        query = query.where(Plan.published.is_(True))
    query = query.order_by(Plan.sort_order.asc(), Plan.code.asc())
    return db.scalars(query).all()


def plan_out(plan: Plan) -> Dict:
    return {
        "plan_id": str(plan.id),
        "code": plan.code,
        "name": plan.name,
        "description": plan.description,
        "billing_interval": plan.billing_interval,
        "currency": plan.currency,
        "price": str(plan.price),
        "published": plan.published,
        "seat_included": plan.seat_included,
    }


# --- Subscriptions --------------------------------------------------------------

def _live_subscription(db: Session, organization_id: uuid.UUID) -> Optional[Subscription]:
    row = db.scalar(
        select(Subscription)
        .where(
            Subscription.organization_id == organization_id,
            Subscription.status.in_(
                {
                    SUBSCRIPTION_STATUS_ACTIVE,
                    SUBSCRIPTION_STATUS_TRIAL,
                    SUBSCRIPTION_STATUS_PAST_DUE,
                    SUBSCRIPTION_STATUS_PAUSED,
                }
            ),
        )
        .order_by(Subscription.created_at.desc())
        .limit(1)
    )
    if row is None:
        return None
    # Deterministic lazy trial expiry.
    if (
        row.status == SUBSCRIPTION_STATUS_TRIAL
        and row.trial_ends_at is not None
        and utc_now_naive() >= row.trial_ends_at.replace(tzinfo=None)
    ):
        row.status = SUBSCRIPTION_STATUS_EXPIRED
        audit_service.record(
            db,
            actor_id=None,
            action=AUDIT_ACTION_SUBSCRIPTION_EXPIRED,
            resource_type="subscription",
            resource_id=str(row.id),
            organization_id=organization_id,
            metadata={"reason": "trial_expired"},
        )
        db.commit()
        db.refresh(row)
        return None
    return row


def get_subscription(db: Session, organization_id: uuid.UUID) -> Optional[Subscription]:
    ensure_default_catalog(db)
    return _live_subscription(db, organization_id)


def subscribe(
    db: Session,
    *,
    actor_user_id: uuid.UUID,
    organization_id: uuid.UUID,
    plan_code: str,
    billing_interval: Optional[str] = None,
) -> Subscription:
    """Start/change an organization subscription to a catalog plan.

    The free plan activates immediately without payment. Any paid plan
    requires a settled (sandbox) payment transaction and issues an invoice
    — a change never charges silently, and an org can only move between
    published catalog plans (no client-supplied plan id/price).
    """
    ensure_default_catalog(db)
    if billing_interval is not None and billing_interval not in BILLING_INTERVALS:
        raise InvalidInputError("billing_interval must be month or year.")
    plan = db.scalar(select(Plan).where(Plan.code == plan_code))
    if plan is None or not plan.active or not plan.published:
        raise NotFoundError("The requested plan is not available.")
    interval = billing_interval or plan.billing_interval
    if interval not in {plan.billing_interval, "month", "year"}:
        raise InvalidInputError("billing_interval is not offered by this plan.")

    # Close any live subscription first (explicit, audited replacement).
    live = _live_subscription(db, organization_id)
    if live is not None and live.status in {SUBSCRIPTION_STATUS_ACTIVE, SUBSCRIPTION_STATUS_TRIAL}:
        _transition_subscription(db, live, SUBSCRIPTION_STATUS_CANCELLED, actor_user_id, reason="replaced")
        db.flush()

    sub = Subscription(
        organization_id=organization_id,
        plan_id=plan.id,
        status=SUBSCRIPTION_STATUS_TRIAL if plan.price > 0 else SUBSCRIPTION_STATUS_ACTIVE,
        billing_interval=interval,
        currency=plan.currency,
        price_amount=plan.price,
        seat_count=plan.seat_included,
        created_by_user_id=actor_user_id,
        current_period_start=utc_now_naive(),
        current_period_end=utc_now_naive() + timedelta(days=365 if interval == "year" else 30),
        trial_ends_at=utc_now_naive() + timedelta(days=14) if plan.price > 0 else None,
        note="Subscription created via catalog plan.",
    )
    db.add(sub)
    db.flush()

    # Paid plans settle a payment + issue an invoice (sandbox provider).
    if plan.price > 0:
        from app.services.payments import create_payment_transaction

        tx = create_payment_transaction(
            db,
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            amount=plan.price,
            currency=plan.currency,
            description=f"{plan.name} ({interval}) subscription",
            idempotency_key=f"sub:{str(sub.id)}",
        )
        issue_invoice(
            db,
            organization_id=organization_id,
            currency=plan.currency,
            subtotal=plan.price,
            items=[
                {
                    "description": f"{plan.name} — {interval}",
                    "amount": str(plan.price),
                    "quantity": 1,
                }
            ],
            transaction_id=tx.id,
            note=f"Subscription to plan '{plan.code}'.",
        )
        sub.status = SUBSCRIPTION_STATUS_ACTIVE
        sub.trial_ends_at = None
        sub.provider_subscription_id = f"mock_sub_{uuid.uuid4().hex[:12]}"

    audit_service.record(
        db,
        actor_id=actor_user_id,
        action=AUDIT_ACTION_SUBSCRIPTION_CREATED,
        resource_type="subscription",
        resource_id=str(sub.id),
        organization_id=organization_id,
        metadata={
            "plan_code": plan.code,
            "interval": interval,
            "price": str(plan.price),
            "currency": plan.currency,
        },
    )
    events.emit(
        db,
        event_type="billing.subscription.changed",
        resource_type="subscription",
        resource_id=str(sub.id),
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        payload={"plan_code": plan.code, "status": sub.status},
    )
    _notify_org(db, organization_id, f"Subscription updated", f"You are now on the {plan.name} plan.")
    db.commit()
    db.refresh(sub)
    return sub


def cancel_subscription(
    db: Session,
    *,
    actor_user_id: uuid.UUID,
    organization_id: uuid.UUID,
    reason: str = "employer_requested",
) -> Subscription:
    sub = _live_subscription(db, organization_id)
    if sub is None:
        raise NotFoundError("No active subscription to cancel.")
    _transition_subscription(db, sub, SUBSCRIPTION_STATUS_CANCELLED, actor_user_id, reason=reason)
    events.emit(
        db,
        event_type="billing.subscription.changed",
        resource_type="subscription",
        resource_id=str(sub.id),
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        payload={"status": SUBSCRIPTION_STATUS_CANCELLED},
    )
    _notify_org(db, organization_id, "Subscription cancelled", reason)
    db.commit()
    db.refresh(sub)
    return sub


def _transition_subscription(
    db: Session,
    sub: Subscription,
    target: str,
    actor_user_id: Optional[uuid.UUID],
    *,
    reason: str,
) -> None:
    allowed = SUBSCRIPTION_TRANSITIONS.get(sub.status, set())
    if target not in allowed:
        raise InvalidInputError(f"Invalid subscription transition {sub.status} -> {target}.")
    sub.status = target
    sub.cancelled_at = sub.cancelled_at or (utc_now_naive() if target == SUBSCRIPTION_STATUS_CANCELLED else None)
    sub.cancel_reason = reason[:60] if target in {SUBSCRIPTION_STATUS_CANCELLED, SUBSCRIPTION_STATUS_EXPIRED} else sub.cancel_reason
    audit_service.record(
        db,
        actor_id=actor_user_id,
        action={
            SUBSCRIPTION_STATUS_CANCELLED: AUDIT_ACTION_SUBSCRIPTION_CANCELLED,
            SUBSCRIPTION_STATUS_EXPIRED: AUDIT_ACTION_SUBSCRIPTION_EXPIRED,
        }.get(target, AUDIT_ACTION_SUBSCRIPTION_CANCELLED),
        resource_type="subscription",
        resource_id=str(sub.id),
        organization_id=sub.organization_id,
        metadata={"reason": reason},
    )


def _notify_org(db: Session, organization_id: uuid.UUID, title: str, body: str) -> None:
    """Notify org members holding billing.read (best-effort)."""
    memberships = db.execute(
        select(func.distinct(Membership.user_id)).where(
            Membership.organization_id == organization_id
        )
    ).scalars().all()
    from app.services.authz import has_permission

    for member_key in memberships:
        try:
            # SQLite returns distinct() UUID columns as hex strings; PG
            # returns UUID objects — normalize so both backends behave the
            # same before any ORM/authz call.
            user_id = member_key if isinstance(member_key, uuid.UUID) else uuid.UUID(str(member_key))
            if has_permission(db, user_id, "billing.read", organization_id):
                notifications.notify(
                    db, user_id, title, body=body, kind=NOTIFICATION_KIND_BILLING
                )
        except Exception:
            continue


def subscription_out(db: Session, sub: Subscription) -> Dict:
    plan = db.get(Plan, sub.plan_id)
    usage = usage_summary(db, sub.organization_id)
    return {
        "subscription_id": str(sub.id),
        "organization_id": str(sub.organization_id),
        "plan_code": plan.code if plan else None,
        "plan_name": plan.name if plan else None,
        "status": sub.status,
        "billing_interval": sub.billing_interval,
        "currency": sub.currency,
        "price": str(sub.price_amount),
        "seat_count": sub.seat_count,
        "trial_ends_at": sub.trial_ends_at.isoformat() if sub.trial_ends_at else None,
        "current_period_end": sub.current_period_end.isoformat() if sub.current_period_end else None,
        "cancel_at_period_end": sub.cancel_at_period_end,
        "usage": usage,
    }


# --- Entitlements ---------------------------------------------------------------

def entitlements_for(db: Session, organization_id: uuid.UUID) -> Dict[str, Dict]:
    """Resolve org -> subscription -> plan -> entitlements (limits + usage)."""
    ensure_default_catalog(db)
    sub = _live_subscription(db, organization_id)
    plan_id = sub.plan_id if sub is not None else _free_plan_id(db)
    rows = db.scalars(
        select(PlanEntitlement).where(PlanEntitlement.plan_id == plan_id)
    ).all()
    usage = usage_summary(db, organization_id)
    out: Dict[str, Dict] = {}
    for row in rows:
        current = usage.get(row.entitlement_code, 0)
        limit = row.limit_value
        out[row.entitlement_code] = {
            "limit": str(limit) if limit is not None else None,
            "used": current,
            "remaining": None if limit is None else max(0, int(limit) - current),
            "unlimited": limit is None,
            "within_limit": limit is None or Decimal(current) <= limit,
        }
    return out


def _free_plan_id(db: Session) -> uuid.UUID:
    plan = db.scalar(select(Plan).where(Plan.code == PLAN_CODE_FREE))
    if plan is None:
        ensure_default_catalog(db)
        plan = db.scalar(select(Plan).where(Plan.code == PLAN_CODE_FREE))
    assert plan is not None
    return plan.id


def usage_count(db: Session, organization_id: uuid.UUID, feature: str, since=None) -> int:
    table = _COUNTABLE_FEATURES.get(feature)
    if table is None:
        # Fall back to explicit usage records only.
        query = select(func.coalesce(func.sum(UsageRecord.quantity), 0)).where(
            UsageRecord.organization_id == organization_id,
            UsageRecord.feature == feature,
        )
        return int(db.scalar(query) or 0)
    try:
        from sqlalchemy import text

        sql = f"SELECT COUNT(*) FROM {table} WHERE organization_id = :org"
        params = {"org": str(organization_id)}
        if table == "job_postings_active":
            sql = (
                "SELECT COUNT(*) FROM job_postings WHERE organization_id = :org "
                "AND status = 'published'"
            )
        return int(db.execute(text(sql), params).scalar_one())
    except Exception:
        return 0


def usage_summary(db: Session, organization_id: uuid.UUID) -> Dict[str, int]:
    out = {}
    for feature in ENTITLEMENT_CODES:
        out[feature] = usage_count(db, organization_id, feature)
    return out


def record_usage(
    db: Session,
    *,
    organization_id: uuid.UUID,
    actor_user_id: uuid.UUID,
    feature: str,
    quantity: int = 1,
    reference_type: Optional[str] = None,
    reference_id: Optional[str] = None,
) -> UsageRecord:
    if feature not in ENTITLEMENT_CODES:
        raise InvalidInputError(f"Unknown feature '{feature}'.")
    if quantity < 0:
        raise InvalidInputError("Usage quantity cannot be negative.")
    row = UsageRecord(
        organization_id=organization_id,
        feature=feature,
        quantity=int(quantity),
        actor_user_id=actor_user_id,
        reference_type=reference_type,
        reference_id=reference_id,
    )
    db.add(row)
    db.flush()
    audit_service.record(
        db,
        actor_id=actor_user_id,
        action=AUDIT_ACTION_USAGE_RECORDED,
        resource_type="usage_record",
        resource_id=str(row.id),
        organization_id=organization_id,
        metadata={"feature": feature, "quantity": int(quantity)},
    )
    return row


# --- Invoices -------------------------------------------------------------------

def issue_invoice(
    db: Session,
    *,
    organization_id: uuid.UUID,
    currency: str,
    subtotal: Decimal,
    items: Optional[List[Dict]] = None,
    transaction_id: Optional[uuid.UUID] = None,
    note: Optional[str] = None,
    actor_user_id: Optional[uuid.UUID] = None,
) -> Invoice:
    try:
        subtotal = Decimal(subtotal).quantize(Decimal("0.01"))
    except Exception:
        raise InvalidInputError("Invalid invoice amount.") from None
    if subtotal < 0:
        raise InvalidInputError("Invoice subtotal cannot be negative.")
    if len(currency) != 3 or not currency.isalpha():
        raise InvalidInputError("A valid ISO currency code is required.")

    org = db.get(Organization, organization_id)
    number_seq = db.scalar(
        select(func.count(Invoice.id)).where(Invoice.organization_id == organization_id)
    ) or 0
    invoice_number = f"INV-{org.slug[:12].upper() if org and org.slug else 'ORG'}-{number_seq + 1:06d}"

    tax_amount = Decimal("0.00")  # Tax is jurisdiction-specific config (Phase 17 §27).
    invoice = Invoice(
        organization_id=organization_id,
        invoice_number=invoice_number,
        currency=currency,
        subtotal_amount=subtotal,
        tax_amount=tax_amount,
        total_amount=(subtotal + tax_amount).quantize(Decimal("0.01")),
        status=INVOICE_STATUS_DRAFT,
        items=(items or [])[:20],
        payment_transaction_id=transaction_id,
        note=(note or "")[:300],
    )
    db.add(invoice)
    db.flush()
    mark_invoice_issued(db, invoice.id, actor_user_id=actor_user_id)
    if transaction_id is not None:
        mark_invoice_paid(db, invoice.id, transaction_id=transaction_id, actor_user_id=actor_user_id)
    return invoice


def mark_invoice_issued(
    db: Session, invoice_id: uuid.UUID, *, actor_user_id: Optional[uuid.UUID] = None
) -> Invoice:
    invoice = db.get(Invoice, invoice_id)
    if invoice is None:
        raise NotFoundError("Invoice not found.")
    if invoice.status == INVOICE_STATUS_DRAFT:
        invoice.status = INVOICE_STATUS_ISSUED
        invoice.issued_at = utc_now_naive()
        audit_service.record(
            db,
            actor_id=actor_user_id,
            action=AUDIT_ACTION_INVOICE_ISSUED,
            resource_type="invoice",
            resource_id=str(invoice.id),
            organization_id=invoice.organization_id,
            metadata={"number": invoice.invoice_number, "total": str(invoice.total_amount)},
        )
        events.emit(
            db,
            event_type="billing.invoice.issued",
            resource_type="invoice",
            resource_id=str(invoice.id),
            organization_id=invoice.organization_id,
            actor_user_id=actor_user_id,
        )
    return invoice


def mark_invoice_paid(
    db: Session,
    invoice_id: uuid.UUID,
    *,
    transaction_id: uuid.UUID,
    actor_user_id: Optional[uuid.UUID] = None,
) -> Invoice:
    invoice = db.get(Invoice, invoice_id)
    if invoice is None:
        raise NotFoundError("Invoice not found.")
    if invoice.status in {INVOICE_STATUS_PAID, INVOICE_STATUS_VOID}:
        return invoice
    invoice.status = INVOICE_STATUS_PAID
    invoice.paid_at = utc_now_naive()
    invoice.payment_transaction_id = transaction_id
    audit_service.record(
        db,
        actor_id=actor_user_id,
        action=AUDIT_ACTION_INVOICE_PAID,
        resource_type="invoice",
        resource_id=str(invoice.id),
        organization_id=invoice.organization_id,
        metadata={"number": invoice.invoice_number},
    )
    return invoice


def list_invoices(db: Session, organization_id: uuid.UUID, limit: int = 50) -> List[Invoice]:
    return db.scalars(
        select(Invoice)
        .where(Invoice.organization_id == organization_id)
        .order_by(Invoice.created_at.desc())
        .limit(min(limit, 100))
    ).all()


def invoice_out(invoice: Invoice) -> Dict:
    return {
        "invoice_id": str(invoice.id),
        "organization_id": str(invoice.organization_id),
        "invoice_number": invoice.invoice_number,
        "currency": invoice.currency,
        "subtotal": str(invoice.subtotal_amount),
        "tax": str(invoice.tax_amount),
        "total": str(invoice.total_amount),
        "status": invoice.status,
        "items": invoice.items or [],
        "issued_at": invoice.issued_at.isoformat() if invoice.issued_at else None,
        "paid_at": invoice.paid_at.isoformat() if invoice.paid_at else None,
    }