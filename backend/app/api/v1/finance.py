"""Platform finance operations — /api/v1/finance (Phase 17).

Platform-scope finance only (the ``finance`` role or super admin). Org
``billing.manage`` holders can self-serve their OWN organization's billing
through /api/v1/billing; they can never read another organization's
finance records here. Every sensitive action is audited.

No raw payment credentials, no unrelated candidate data, no unrelated
organization data is ever exposed.
"""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.errors import AppError, PermissionDeniedError
from app.db.session import get_db
from app.models.identity import User
from app.schemas.billing import RefundRequest
from app.services import commerce, payments
from app.services.authz import has_platform_permission

router = APIRouter(prefix="/finance", tags=["finance"])


def _raise_app(exc: AppError) -> Exception:
    from fastapi import HTTPException

    return HTTPException(status_code=exc.status_code, detail=exc.message)


def _require_finance(db: Session, user: User, permission: str) -> None:
    """Platform-scope finance permission (never org billing.manage)."""
    if not has_platform_permission(db, user.id, permission):
        raise PermissionDeniedError(
            f"Missing platform finance permission '{permission}'."
        )


def _serialize_tx(tx) -> dict:
    return {
        "transaction_id": str(tx.id),
        "organization_id": str(tx.organization_id),
        "provider": tx.provider,
        "provider_payment_id": tx.provider_payment_id,
        "amount": str(tx.amount),
        "currency": tx.currency,
        "status": tx.status,
        "description": tx.description,
        "idempotency_key": tx.idempotency_key,
        "succeeded_at": tx.succeeded_at.isoformat() if tx.succeeded_at else None,
        "failed_at": tx.failed_at.isoformat() if tx.failed_at else None,
        "refunded_amount": str(tx.refunded_amount),
    }


def _serialize_refund(r) -> dict:
    return {
        "refund_id": str(r.id),
        "transaction_id": str(r.transaction_id),
        "provider_refund_id": r.provider_refund_id,
        "amount": str(r.amount),
        "currency": r.currency,
        "status": r.status,
        "reason": r.reason,
        "authorized_by_user_id": str(r.authorized_by_user_id) if r.authorized_by_user_id else None,
        "succeeded_at": r.succeeded_at.isoformat() if r.succeeded_at else None,
    }


@router.get("/transactions")
def list_transactions(
    organization_id: Optional[uuid.UUID] = Query(default=None),
    limit: int = Query(default=30, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    try:
        _require_finance(db, user, "finance.read")
        rows = payments.list_transactions(db, organization_id, limit=limit)
        return {"transactions": [_serialize_tx(t) for t in rows]}
    except AppError as exc:
        raise _raise_app(exc) from exc


@router.get("/refunds")
def list_refunds(
    organization_id: Optional[uuid.UUID] = Query(default=None),
    limit: int = Query(default=30, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    try:
        _require_finance(db, user, "finance.read")
        rows = payments.list_refunds(db, limit=limit)
        if organization_id is not None:
            tx_ids = {
                t.id for t in payments.list_transactions(db, organization_id, limit=500)
            }
            rows = [r for r in rows if r.transaction_id in tx_ids]
        return {"refunds": [_serialize_refund(r) for r in rows]}
    except AppError as exc:
        raise _raise_app(exc) from exc


@router.get("/invoices")
def list_invoices(
    organization_id: Optional[uuid.UUID] = Query(default=None),
    limit: int = Query(default=30, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    try:
        _require_finance(db, user, "finance.read")
        if organization_id is not None:
            rows = commerce.list_invoices(db, organization_id, limit=limit)
        else:
            from app.models.commerce import Invoice

            rows = db.scalars(
                select_order_invoices(Invoice).limit(min(limit, 100))
            ).all()
        return {"invoices": [commerce.invoice_out(i) for i in rows]}
    except AppError as exc:
        raise _raise_app(exc) from exc


@router.get("/subscriptions")
def list_subscriptions(
    organization_id: Optional[uuid.UUID] = Query(default=None),
    limit: int = Query(default=30, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    try:
        _require_finance(db, user, "finance.read")
        from app.models.commerce import Subscription

        query = select_all_subscriptions(Subscription).order_by(Subscription.created_at.desc())
        if organization_id is not None:
            query = query.where(Subscription.organization_id == organization_id)
        query = query.limit(min(limit, 100))
        rows = db.scalars(query).all()
        return {"subscriptions": [commerce.subscription_out(db, s) for s in rows]}
    except AppError as exc:
        raise _raise_app(exc) from exc


@router.post("/refunds")
def authorize_refund(
    body: RefundRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    try:
        _require_finance(db, user, "finance.manage")
        tx = db.get(payments.PaymentTransaction, body.transaction_id)
        if tx is None:
            from app.core.errors import NotFoundError

            raise NotFoundError("Payment transaction not found.")
        refund = payments.create_refund(
            db,
            organization_id=tx.organization_id,
            actor_user_id=user.id,
            transaction_id=body.transaction_id,
            amount=body.amount,
            reason=body.reason,
        )
        return _serialize_refund(refund)
    except AppError as exc:
        raise _raise_app(exc) from exc


# --- small query helpers (kept module-local for readability) --------------------

def select_order_invoices(model):
    from sqlalchemy import select

    return select(model).order_by(model.created_at.desc())


def select_all_subscriptions(model):
    from sqlalchemy import select

    return select(model)
