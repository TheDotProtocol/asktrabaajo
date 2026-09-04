"""Payment service — provider-neutral, mock-first (Phase 17).

Design rules:
- ``PaymentProvider`` is an interface; business logic never imports a
  vendor. The default provider is ``mock``: deterministic, no real money,
  HMAC-SHA256-signed webhooks for local verification. ``none`` disables
  payments (safe degraded). A real Stripe adapter is intentionally NOT
  wired in this phase (no production charges).
- Only provider REFERENCES are stored (customer/payment/refund ids) —
  never CVV, card numbers, or credentials.
- Money is Decimal + NUMERIC columns; negative/zero amounts are rejected;
  currency must match the originating context; no conversion happens.
- Webhooks: signature verification first, then unique (provider, event_id)
  deduplication, replay rejection, safe transitions, audit. Unverified
  payloads are never trusted.
- Refunds are idempotent (idempotency key per transaction+amount) and can
  never exceed the paid (refundable) amount.
"""

from __future__ import annotations

import hmac
import hashlib
import json
import uuid
from abc import ABC, abstractmethod
from datetime import timedelta
from decimal import Decimal
from typing import Dict, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError, InvalidInputError, NotFoundError
from app.core.timeutil import to_utc_naive, utc_now_naive
from app.models.enums import (
    AUDIT_ACTION_FINANCE_REFUND_AUTHORIZED,
    AUDIT_ACTION_PAYMENT_CREATED,
    AUDIT_ACTION_PAYMENT_FAILED,
    AUDIT_ACTION_PAYMENT_SUCCEEDED,
    AUDIT_ACTION_REFUND_CREATED,
    AUDIT_ACTION_REFUND_SUCCEEDED,
    AUDIT_ACTION_WEBHOOK_RECEIVED,
    AUDIT_ACTION_WEBHOOK_REJECTED,
    AUDIT_ACTION_WEBHOOK_VERIFIED,
    PAYMENT_STATUS_CANCELLED,
    PAYMENT_STATUS_FAILED,
    PAYMENT_STATUS_PARTIALLY_REFUNDED,
    PAYMENT_STATUS_PENDING,
    PAYMENT_STATUS_REFUNDED,
    PAYMENT_STATUS_SUCCEEDED,
    REFUND_STATUS_FAILED,
    REFUND_STATUS_PENDING,
    REFUND_STATUS_SUCCEEDED,
    WEBHOOK_EVENT_STATUS_DUPLICATE,
    WEBHOOK_EVENT_STATUS_FAILED,
    WEBHOOK_EVENT_STATUS_IGNORED,
    WEBHOOK_EVENT_STATUS_PROCESSED,
    WEBHOOK_EVENT_STATUS_RECEIVED,
)
from app.models.payments import (
    PaymentRefund,
    PaymentTransaction,
    PaymentWebhookEvent,
)
from app.services import audit as audit_service


class PaymentError(AppError):
    status_code = 402
    code = "payment.failed"


class PaymentUnavailableError(AppError):
    status_code = 503
    code = "payment.provider_unavailable"


class WebhookVerificationError(AppError):
    status_code = 400
    code = "payment.webhook_invalid"


# --- Provider abstraction -------------------------------------------------------

class PaymentProvider(ABC):
    """Provider-neutral payment capability interface (mock-first)."""

    name = "none"

    @abstractmethod
    def create_payment(self, *, amount: Decimal, currency: str, description: str) -> Dict:
        ...

    @abstractmethod
    def refund(self, *, provider_payment_id: str, amount: Decimal, currency: str) -> Dict:
        ...

    @abstractmethod
    def verify_webhook_signature(self, *, body: bytes, headers: Dict[str, str]) -> bool:
        ...


class MockPaymentProvider(PaymentProvider):
    """Deterministic sandbox provider — never real money.

    Signs webhook bodies with HMAC-SHA256 using the configured
    ``payment_webhook_secret`` (dev default when unset, for the sandbox).
    """

    name = "mock"

    def __init__(self, webhook_secret: Optional[str] = None) -> None:
        secret = webhook_secret if webhook_secret is not None else get_settings().payment_webhook_secret
        self._secret = secret or "asktrabaajo-mock-webhook-secret"

    def create_payment(self, *, amount: Decimal, currency: str, description: str) -> Dict:
        if amount <= 0:
            raise PaymentError("Payment amount must be positive.")
        return {
            "provider_payment_id": f"mock_pay_{uuid.uuid4().hex[:16]}",
            "status": "succeeded",
            "amount": amount,
            "currency": currency,
        }

    def refund(self, *, provider_payment_id: str, amount: Decimal, currency: str) -> Dict:
        if amount <= 0:
            raise PaymentError("Refund amount must be positive.")
        return {
            "provider_refund_id": f"mock_ref_{uuid.uuid4().hex[:16]}",
            "status": "succeeded",
            "amount": amount,
            "currency": currency,
        }

    def verify_webhook_signature(self, *, body: bytes, headers: Dict[str, str]) -> bool:
        sig = headers.get("x-provider-signature", "")
        expected = hmac.new(
            self._secret.encode("utf-8"), body, hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(sig, expected)

    def sign(self, body: bytes) -> str:
        return hmac.new(self._secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


def get_payment_provider(name: Optional[str] = None) -> PaymentProvider:
    provider_name = name or get_settings().payment_provider
    if provider_name == "mock":
        return MockPaymentProvider()
    if provider_name == "none":
        raise PaymentUnavailableError("Payments are disabled for this deployment.")
    # A real vendor adapter would live here behind configuration; it is NOT
    # wired in Phase 17. Fail safe rather than pretend to process money.
    raise PaymentUnavailableError(
        f"Payment provider '{provider_name}' is not configured."
    )


# --- Transactions ---------------------------------------------------------------

def _refundable_amount(db: Session, transaction: PaymentTransaction) -> Decimal:
    """Remaining refundable balance.

    Only paid states (succeeded / partially_refunded) are refundable; the
    balance is always the paid amount minus already-refunded amounts, so
    repeated partial refunds stay possible until fully refunded.
    """
    if transaction.status not in {
        PAYMENT_STATUS_SUCCEEDED,
        PAYMENT_STATUS_PARTIALLY_REFUNDED,
    }:
        return Decimal("0.00")
    return max(
        Decimal("0.00"),
        (transaction.amount or Decimal("0.00")) - (transaction.refunded_amount or Decimal("0.00")),
    )


def create_payment_transaction(
    db: Session,
    *,
    organization_id: uuid.UUID,
    actor_user_id: uuid.UUID,
    amount: Decimal,
    currency: str,
    description: str,
    idempotency_key: str,
) -> PaymentTransaction:
    """Create (and settle via the sandbox provider) one payment.

    Idempotent on ``idempotency_key``: a repeat call returns the existing
    transaction instead of charging twice.
    """
    try:
        amount = Decimal(amount).quantize(Decimal("0.01"))
    except Exception:
        raise InvalidInputError("Invalid payment amount.") from None
    if amount <= 0:
        raise PaymentError("Payment amount must be positive.")
    if not currency or len(currency) != 3 or not currency.isalpha():
        raise InvalidInputError("A valid ISO currency code is required.")

    existing = db.scalar(
        select(PaymentTransaction).where(
            PaymentTransaction.idempotency_key == idempotency_key
        )
    )
    if existing is not None:
        return existing

    provider = get_payment_provider()
    result = provider.create_payment(amount=amount, currency=currency, description=description)

    tx = PaymentTransaction(
        organization_id=organization_id,
        provider=provider.name,
        provider_payment_id=result["provider_payment_id"],
        amount=amount,
        currency=currency,
        status=PAYMENT_STATUS_SUCCEEDED,
        description=description[:240],
        idempotency_key=idempotency_key,
        created_by_user_id=actor_user_id,
        succeeded_at=utc_now_naive(),
    )
    db.add(tx)
    db.flush()
    audit_service.record(
        db,
        actor_id=actor_user_id,
        action=AUDIT_ACTION_PAYMENT_CREATED,
        resource_type="payment_transaction",
        resource_id=str(tx.id),
        organization_id=organization_id,
        metadata={"provider": provider.name, "currency": currency, "amount": str(amount)},
    )
    audit_service.record(
        db,
        actor_id=actor_user_id,
        action=AUDIT_ACTION_PAYMENT_SUCCEEDED,
        resource_type="payment_transaction",
        resource_id=str(tx.id),
        organization_id=organization_id,
    )
    return tx


def mark_payment_failed(
    db: Session, transaction_id: uuid.UUID, *, failure_code: str, note: Optional[str] = None
) -> PaymentTransaction:
    """Only the provider/webhook/backend path may mark a payment failed."""
    tx = db.get(PaymentTransaction, transaction_id)
    if tx is None:
        raise NotFoundError("Payment transaction not found.")
    if tx.status in {PAYMENT_STATUS_SUCCEEDED, PAYMENT_STATUS_REFUNDED, PAYMENT_STATUS_CANCELLED}:
        raise InvalidInputError("This payment cannot be marked failed.")
    tx.status = PAYMENT_STATUS_FAILED
    tx.failure_code = failure_code
    tx.failed_at = utc_now_naive()
    audit_service.record(
        db,
        actor_id=None,
        action=AUDIT_ACTION_PAYMENT_FAILED,
        resource_type="payment_transaction",
        resource_id=str(tx.id),
        organization_id=tx.organization_id,
        metadata={"failure_code": failure_code, "note": (note or "")[:120]},
    )
    db.commit()
    db.refresh(tx)
    return tx


# --- Refunds --------------------------------------------------------------------

def create_refund(
    db: Session,
    *,
    organization_id: uuid.UUID,
    actor_user_id: uuid.UUID,
    transaction_id: uuid.UUID,
    amount: Decimal,
    reason: Optional[str] = None,
) -> PaymentRefund:
    """Idempotent, authorized refund; never exceeds the refundable amount."""
    try:
        amount = Decimal(amount).quantize(Decimal("0.01"))
    except Exception:
        raise InvalidInputError("Invalid refund amount.") from None
    if amount <= 0:
        raise PaymentError("Refund amount must be positive.")
    tx = db.get(PaymentTransaction, transaction_id)
    if tx is None:
        raise NotFoundError("Payment transaction not found.")
    if tx.organization_id != organization_id:
        from app.core.errors import PermissionDeniedError

        raise PermissionDeniedError("This payment does not belong to your organization.")

    # Idempotency first: replaying an identical refund returns the existing
    # record even after the transaction left the ``succeeded`` state (e.g. a
    # retry of a partial refund). The state gate below applies to NEW refunds.
    idem = f"refund:{str(transaction_id)}:{str(amount)}"
    existing = db.scalar(select(PaymentRefund).where(PaymentRefund.idempotency_key == idem))
    if existing is not None:
        return existing

    if tx.status not in {PAYMENT_STATUS_SUCCEEDED, PAYMENT_STATUS_PARTIALLY_REFUNDED}:
        raise PaymentError("Only succeeded payments can be refunded.")
    refundable = _refundable_amount(db, tx)
    if amount > refundable:
        raise PaymentError("Refund amount exceeds the refundable amount.")

    provider = get_payment_provider()
    result = provider.refund(
        provider_payment_id=tx.provider_payment_id or "", amount=amount, currency=tx.currency
    )
    refund = PaymentRefund(
        transaction_id=tx.id,
        provider_refund_id=result["provider_refund_id"],
        amount=amount,
        currency=tx.currency,
        status=REFUND_STATUS_SUCCEEDED,
        reason=(reason or "")[:240],
        idempotency_key=idem,
        authorized_by_user_id=actor_user_id,
        succeeded_at=utc_now_naive(),
    )
    db.add(refund)
    tx.refunded_amount = (tx.refunded_amount or Decimal("0.00")) + amount
    if tx.refunded_amount >= tx.amount:
        tx.status = PAYMENT_STATUS_REFUNDED
    else:
        tx.status = PAYMENT_STATUS_PARTIALLY_REFUNDED
    db.flush()
    audit_service.record(
        db,
        actor_id=actor_user_id,
        action=AUDIT_ACTION_FINANCE_REFUND_AUTHORIZED,
        resource_type="payment_transaction",
        resource_id=str(tx.id),
        organization_id=organization_id,
        metadata={"amount": str(amount), "currency": tx.currency},
    )
    audit_service.record(
        db,
        actor_id=actor_user_id,
        action=AUDIT_ACTION_REFUND_CREATED,
        resource_type="payment_refund",
        resource_id=str(refund.id),
        organization_id=organization_id,
    )
    audit_service.record(
        db,
        actor_id=actor_user_id,
        action=AUDIT_ACTION_REFUND_SUCCEEDED,
        resource_type="payment_refund",
        resource_id=str(refund.id),
        organization_id=organization_id,
    )
    db.commit()
    db.refresh(refund)
    return refund


# --- Webhooks -------------------------------------------------------------------

_WEBHOOK_MAX_AGE_SECONDS = 300  # replay window


def _parse_webhook_body(body: bytes, headers: Dict[str, str]) -> Dict:
    try:
        payload = json.loads(body.decode("utf-8"))
    except Exception:
        raise WebhookVerificationError("Malformed webhook payload.") from None
    if not isinstance(payload, dict):
        raise WebhookVerificationError("Malformed webhook payload.")
    return payload


def handle_provider_webhook(
    db: Session,
    *,
    provider: str,
    body: bytes,
    headers: Dict[str, str],
) -> Dict:
    """Signature-verified, replay-safe, idempotent provider webhook handling."""
    provider_obj = get_payment_provider(provider)

    if not provider_obj.verify_webhook_signature(body=body, headers=headers):
        audit_service.record_committed(
            db,
            actor_id=None,
            action=AUDIT_ACTION_WEBHOOK_REJECTED,
            resource_type="payment_webhook_event",
            organization_id=None,
            metadata={"provider": provider, "reason": "invalid_signature"},
        )
        raise WebhookVerificationError("Invalid webhook signature.")

    payload = _parse_webhook_body(body, headers)
    event_id = str(payload.get("event_id") or payload.get("id") or "")
    event_type = str(payload.get("type") or "unknown")
    if not event_id:
        raise WebhookVerificationError("Webhook payload is missing an event id.")

    audit_service.record_committed(
        db,
        actor_id=None,
        action=AUDIT_ACTION_WEBHOOK_RECEIVED,
        resource_type="payment_webhook_event",
        organization_id=None,
        metadata={"provider": provider, "event_id": event_id[:64], "event_type": event_type[:64]},
    )

    existing = db.scalar(
        select(PaymentWebhookEvent).where(
            PaymentWebhookEvent.provider == provider,
            PaymentWebhookEvent.event_id == event_id,
        )
    )
    if existing is not None:
        if existing.status == WEBHOOK_EVENT_STATUS_PROCESSED:
            existing.status = WEBHOOK_EVENT_STATUS_DUPLICATE
            db.commit()
            return {"event_id": event_id, "status": "duplicate"}
        return {"event_id": event_id, "status": existing.status}

    row = PaymentWebhookEvent(
        provider=provider,
        event_id=event_id,
        event_type=event_type[:80],
        status=WEBHOOK_EVENT_STATUS_RECEIVED,
        signature_valid=True,
    )
    db.add(row)
    db.flush()

    # Replay protection: stale events are recorded and ignored.
    created_at = row.received_at or utc_now_naive()
    received = to_utc_naive(created_at)
    sent = payload.get("created")
    if sent is not None:
        try:
            from datetime import datetime

            sent_dt = datetime.fromisoformat(str(sent))
            if (received - to_utc_naive(sent_dt)).total_seconds() > _WEBHOOK_MAX_AGE_SECONDS:
                row.status = WEBHOOK_EVENT_STATUS_IGNORED
                row.note = "stale event outside replay window"
                db.commit()
                audit_service.record_committed(
                    db,
                    actor_id=None,
                    action=AUDIT_ACTION_WEBHOOK_REJECTED,
                    resource_type="payment_webhook_event",
                    resource_id=str(row.id),
                    metadata={"reason": "replay_window"},
                )
                return {"event_id": event_id, "status": "ignored"}
        except Exception:
            pass

    # Process supported events only (unknown events are recorded + ignored).
    result_status = _apply_webhook_event(db, row, payload, provider)
    row.status = result_status
    row.processed_at = utc_now_naive()
    db.commit()
    db.refresh(row)
    return {"event_id": event_id, "status": result_status}


def _apply_webhook_event(db: Session, row: PaymentWebhookEvent, payload: Dict, provider: str) -> str:
    """Map a verified event to a safe transition. Returns the row status."""
    event_type = row.event_type
    if event_type == "payment.succeeded":
        ref = str(payload.get("payment_id") or "")
        tx = (
            db.scalar(
                select(PaymentTransaction).where(
                    PaymentTransaction.provider == provider,
                    PaymentTransaction.provider_payment_id == ref,
                )
            )
            if ref
            else None
        )
        if tx is None:
            row.note = "unknown payment reference"
            return WEBHOOK_EVENT_STATUS_IGNORED
        if tx.status in {PAYMENT_STATUS_PENDING, PAYMENT_STATUS_FAILED}:
            tx.status = PAYMENT_STATUS_SUCCEEDED
            tx.succeeded_at = utc_now_naive()
            audit_service.record(
                db,
                actor_id=None,
                action=AUDIT_ACTION_PAYMENT_SUCCEEDED,
                resource_type="payment_transaction",
                resource_id=str(tx.id),
                organization_id=tx.organization_id,
            )
        audit_service.record(
            db,
            actor_id=None,
            action=AUDIT_ACTION_WEBHOOK_VERIFIED,
            resource_type="payment_webhook_event",
            resource_id=str(row.id),
            organization_id=tx.organization_id if tx else None,
        )
        return WEBHOOK_EVENT_STATUS_PROCESSED

    if event_type == "payment.failed":
        ref = str(payload.get("payment_id") or "")
        tx = (
            db.scalar(
                select(PaymentTransaction).where(
                    PaymentTransaction.provider == provider,
                    PaymentTransaction.provider_payment_id == ref,
                )
            )
            if ref
            else None
        )
        if tx is None:
            row.note = "unknown payment reference"
            return WEBHOOK_EVENT_STATUS_IGNORED
        mark_payment_failed(db, tx.id, failure_code=str(payload.get("failure_code") or "provider_declined"))
        audit_service.record(
            db,
            actor_id=None,
            action=AUDIT_ACTION_WEBHOOK_VERIFIED,
            resource_type="payment_webhook_event",
            resource_id=str(row.id),
            organization_id=tx.organization_id,
        )
        return WEBHOOK_EVENT_STATUS_PROCESSED

    # Unknown/unsupported event: record + ignore (never crash the webhook).
    row.note = f"unsupported event type '{event_type[:60]}'"
    return WEBHOOK_EVENT_STATUS_IGNORED


# --- Listing helpers ------------------------------------------------------------

def list_transactions(db: Session, organization_id: Optional[uuid.UUID], limit: int = 50) -> list:
    query = select(PaymentTransaction)
    if organization_id is not None:
        query = query.where(PaymentTransaction.organization_id == organization_id)
    query = query.order_by(PaymentTransaction.created_at.desc()).limit(min(limit, 100))
    return db.scalars(query).all()


def list_refunds(db: Session, transaction_id: Optional[uuid.UUID] = None, limit: int = 50) -> list:
    query = select(PaymentRefund)
    if transaction_id is not None:
        query = query.where(PaymentRefund.transaction_id == transaction_id)
    query = query.order_by(PaymentRefund.created_at.desc()).limit(min(limit, 100))
    return db.scalars(query).all()