"""Commerce / billing API — /api/v1/billing (Phase 17).

Jobseeker core stays free. These routes serve the organization side:
plans, subscription lifecycle, invoices, entitlements, usage and the
provider webhook endpoint. Tenant isolation is enforced server-side
(membership + billing.read/billing.manage + org ownership). Webhooks are
signature-verified and never callable by an ordinary client to fake
payment success.
"""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Header, Query, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_org_permission
from app.core.errors import AppError, NotFoundError
from app.core.ratelimit import rate_limit_dependency
from app.db.session import get_db
from app.models.identity import User
from app.schemas.billing import CancelRequest, RefundRequest, SubscribeRequest, WebhookOut
from app.services import commerce, payments

router = APIRouter(prefix="/billing", tags=["billing"])


def _raise_app(exc: AppError) -> Exception:
    from fastapi import HTTPException

    return HTTPException(status_code=exc.status_code, detail=exc.message)


def _org_member_org(db: Session, user: User, organization_id: uuid.UUID, permission: str) -> None:
    require_org_permission(db, user, permission, organization_id)


@router.get("/plans")
def list_plans(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    plans = commerce.list_plans(db)
    return {"plans": [commerce.plan_out(p) for p in plans]}


@router.get("/subscription")
def get_subscription(
    organization_id: uuid.UUID = Query(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    try:
        _org_member_org(db, user, organization_id, "billing.read")
        sub = commerce.get_subscription(db, organization_id)
        if sub is None:
            return {"subscription": None}
        return {"subscription": commerce.subscription_out(db, sub)}
    except AppError as exc:
        raise _raise_app(exc) from exc


@router.post("/subscriptions", status_code=201,
             dependencies=[Depends(rate_limit_dependency("billing.change"))])
def subscribe(
    body: SubscribeRequest,
    organization_id: uuid.UUID = Query(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    try:
        _org_member_org(db, user, organization_id, "billing.manage")
        sub = commerce.subscribe(
            db,
            actor_user_id=user.id,
            organization_id=organization_id,
            plan_code=body.plan_code,
            billing_interval=body.billing_interval,
        )
        return {"subscription": commerce.subscription_out(db, sub)}
    except AppError as exc:
        raise _raise_app(exc) from exc


@router.post("/subscriptions/cancel")
def cancel_subscription(
    body: CancelRequest,
    organization_id: uuid.UUID = Query(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    try:
        _org_member_org(db, user, organization_id, "billing.manage")
        sub = commerce.cancel_subscription(
            db,
            actor_user_id=user.id,
            organization_id=organization_id,
            reason=body.reason or "employer_requested",
        )
        return {"subscription": commerce.subscription_out(db, sub)}
    except AppError as exc:
        raise _raise_app(exc) from exc


@router.get("/entitlements")
def get_entitlements(
    organization_id: uuid.UUID = Query(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    try:
        _org_member_org(db, user, organization_id, "billing.read")
        return {"entitlements": commerce.entitlements_for(db, organization_id)}
    except AppError as exc:
        raise _raise_app(exc) from exc


@router.get("/usage")
def get_usage(
    organization_id: uuid.UUID = Query(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    try:
        _org_member_org(db, user, organization_id, "billing.read")
        return {"usage": commerce.usage_summary(db, organization_id)}
    except AppError as exc:
        raise _raise_app(exc) from exc


@router.get("/invoices")
def list_invoices(
    organization_id: uuid.UUID = Query(...),
    limit: int = Query(default=30, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    try:
        _org_member_org(db, user, organization_id, "billing.read")
        invoices = commerce.list_invoices(db, organization_id, limit=limit)
        return {"invoices": [commerce.invoice_out(i) for i in invoices]}
    except AppError as exc:
        raise _raise_app(exc) from exc


@router.get("/invoices/{invoice_id}")
def get_invoice(
    invoice_id: uuid.UUID,
    organization_id: uuid.UUID = Query(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    try:
        _org_member_org(db, user, organization_id, "billing.read")
        invoice = db.get(commerce.Invoice, invoice_id)
        if invoice is None or invoice.organization_id != organization_id:
            raise NotFoundError("Invoice not found.")
        return commerce.invoice_out(invoice)
    except AppError as exc:
        raise _raise_app(exc) from exc


# --- Provider webhook (signature-gated; NOT an authenticated route) -------------

@router.post("/webhooks/{provider}", response_model=WebhookOut)
async def provider_webhook(
    provider: str,
    request: Request,
    x_provider_signature: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
) -> dict:
    # Raw bytes are read from the request directly so signature verification
    # always covers the exact transmitted payload (no content-type quirks).
    body = await request.body()
    headers = {"x-provider-signature": x_provider_signature or ""}
    try:
        return payments.handle_provider_webhook(
            db, provider=provider, body=body, headers=headers
        )
    except AppError as exc:
        raise _raise_app(exc) from exc