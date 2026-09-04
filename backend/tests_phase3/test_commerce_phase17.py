"""Phase 17 — Commerce, Billing, Payments, Finance: deterministic tests.

Code-enforced safety invariants (never LLM-dependent):
- billing is org-scoped + permission-gated (billing.read / billing.manage)
- cross-organization billing isolation is absolute
- jobseekers and org members without billing roles cannot touch billing
- subscription state machine is explicit; only catalog plan codes are
  accepted (no client-supplied plan id / price)
- money is Decimal/NUMERIC with validated currency; negative/zero amounts
  rejected; refunds idempotent and never exceed the paid amount
- payments are provider-neutral and mock-first; a disabled provider fails
  safe (503), it never fabricates success
- webhooks are signature-verified, replay-protected, duplicate-safe; a
  client can never fake payment success through the webhook route
- finance operations require PLATFORM finance.read/finance.manage — org
  billing.manage never satisfies them; support cannot refund
- refunds are authorized, audited, provider-linked
- Athena has no billing mutation tools (no autonomous charge/refund/
  upgrade/cancel); only controlled read tooling could ever exist
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError, InvalidInputError
from app.models.audit import AuditLogEntry
from app.models.commerce import Invoice, Plan, Subscription, UsageRecord
from app.models.identity import User
from app.models.payments import (
    PaymentRefund,
    PaymentTransaction,
    PaymentWebhookEvent,
)
from app.models.tenancy import Membership, Organization
from app.services import commerce, payments


# --- Helpers -------------------------------------------------------------------

def _user_id(db: Session, email: str) -> uuid.UUID:
    user = db.scalar(select(User).where(User.email == email))
    assert user is not None, f"missing user {email}"
    return user.id


def _make_org(db: Session, user_id: uuid.UUID, role: str = "org_admin") -> uuid.UUID:
    org = Organization(
        name=f"Org {uuid.uuid4().hex[:6]}", slug=f"org-{uuid.uuid4().hex[:6]}", kind="employer"
    )
    db.add(org)
    db.flush()
    db.add(Membership(user_id=user_id, organization_id=org.id, role_code=role, created_by=user_id))
    db.commit()
    return org.id


def _make_platform_membership(db: Session, user_id: uuid.UUID, role: str = "finance") -> uuid.UUID:
    org = Organization(
        name=f"Platform {uuid.uuid4().hex[:6]}",
        slug=f"platform-{uuid.uuid4().hex[:6]}",
        kind="platform",
    )
    db.add(org)
    db.flush()
    db.add(Membership(user_id=user_id, organization_id=org.id, role_code=role, created_by=user_id))
    db.commit()
    return org.id


def _billing_admin(client, make_user, db) -> tuple:
    user = make_user(f"ba{uuid.uuid4().hex[:6]}@example.com")
    org_id = _make_org(db, _user_id(db, user["email"]), role="org_admin")
    return user, org_id


def _subscribe(client, user, org_id, plan_code: str = "free", interval: str | None = None):
    body: dict = {"plan_code": plan_code}
    if interval is not None:
        body["billing_interval"] = interval
    return client.post(
        "/api/v1/billing/subscriptions",
        headers=user["authorization"],
        params={"organization_id": str(org_id)},
        json=body,
    )


def _cancel(client, user, org_id):
    return client.post(
        "/api/v1/billing/subscriptions/cancel",
        headers=user["authorization"],
        params={"organization_id": str(org_id)},
        json={"reason": "test"},
    )


def _webhook(client, body: bytes, signature: str | None):
    headers = {"Content-Type": "application/json"}
    if signature is not None:
        headers["X-Provider-Signature"] = signature
    return client.post("/api/v1/billing/webhooks/mock", content=body, headers=headers)


def _signed_event(client, payload: dict) -> str:
    """Post a correctly signed event and return the resulting status."""
    provider = payments.get_payment_provider("mock")
    body = json.dumps(payload).encode("utf-8")
    sig = provider.sign(body)
    resp = _webhook(client, body, sig)
    return resp


# --- Catalog + RBAC -------------------------------------------------------------

def test_plans_require_auth_and_are_configuration(client, make_user, db):
    anon = client.get("/api/v1/billing/plans")
    assert anon.status_code == 401, anon.text
    user, org_id = _billing_admin(client, make_user, db)
    resp = client.get("/api/v1/billing/plans", headers=user["authorization"])
    assert resp.status_code == 200, resp.text
    plans = resp.json()["plans"]
    # Only the configurable FREE plan is seeded — no invented pricing.
    assert [p["code"] for p in plans] == ["free"]
    assert plans[0]["price"] == "0.00"
    assert plans[0]["currency"] == "USD"


def test_billing_requires_org_permission(client, make_user, db):
    admin, org_id = _billing_admin(client, make_user, db)
    # org_admin can read; hr / recruiter roles have no billing.* -> 403.
    for role in ("hr", "recruiter", "hiring_manager"):
        member = make_user(f"no-bill-{role}-{uuid.uuid4().hex[:6]}@example.com")
        other_org = _make_org(db, _user_id(db, member["email"]), role=role)
        resp = client.get(
            "/api/v1/billing/subscription",
            headers=member["authorization"],
            params={"organization_id": str(org_id)},
        )
        assert resp.status_code == 403, f"{role}: {resp.text}"
        # On their own org too — membership alone is not enough.
        own = client.get(
            "/api/v1/billing/subscription",
            headers=member["authorization"],
            params={"organization_id": str(other_org)},
        )
        assert own.status_code == 403, f"{role} own org: {own.text}"
    # No membership at all -> 403.
    stranger = make_user(f"stranger{uuid.uuid4().hex[:6]}@example.com")
    resp = client.get(
        "/api/v1/billing/subscription",
        headers=stranger["authorization"],
        params={"organization_id": str(org_id)},
    )
    assert resp.status_code == 403, resp.text
    # Admin can read (no subscription yet -> null).
    ok = client.get(
        "/api/v1/billing/subscription",
        headers=admin["authorization"],
        params={"organization_id": str(org_id)},
    )
    assert ok.status_code == 200 and ok.json()["subscription"] is None


def test_cross_organization_billing_isolation(client, make_user, db):
    admin_a, org_a = _billing_admin(client, make_user, db)
    admin_b, org_b = _billing_admin(client, make_user, db)
    _subscribe(client, admin_a, org_a)
    # A's admin can read A but NEVER B.
    for path in ("subscription", "entitlements", "usage", "invoices"):
        mine = client.get(
            f"/api/v1/billing/{path}",
            headers=admin_a["authorization"],
            params={"organization_id": str(org_a)},
        )
        assert mine.status_code == 200, path
        other = client.get(
            f"/api/v1/billing/{path}",
            headers=admin_a["authorization"],
            params={"organization_id": str(org_b)},
        )
        assert other.status_code == 403, f"cross-org {path}: {other.text}"
    # And B's admin cannot act on A (subscribe/cancel).
    sub = _subscribe(client, admin_b, org_a)
    assert sub.status_code == 403, sub.text
    cancel = _cancel(client, admin_b, org_a)
    assert cancel.status_code == 403, cancel.text


def test_candidate_cannot_access_employer_billing(client, make_user, db):
    admin, org_id = _billing_admin(client, make_user, db)
    _subscribe(client, admin, org_id)
    candidate = make_user(f"cand17{uuid.uuid4().hex[:6]}@example.com")
    for path in ("subscription", "entitlements", "usage", "invoices", "plans"):
        resp = client.get(
            f"/api/v1/billing/{path}",
            headers=candidate["authorization"],
            params={"organization_id": str(org_id)},
        )
        if path == "plans":
            assert resp.status_code == 200  # public catalog is fine
        else:
            assert resp.status_code == 403, f"{path}: {resp.text}"


# --- Subscription lifecycle ----------------------------------------------------

def test_free_plan_subscription_lifecycle(client, make_user, db):
    admin, org_id = _billing_admin(client, make_user, db)
    sub = _subscribe(client, admin, org_id)
    assert sub.status_code == 201, sub.text
    body = sub.json()["subscription"]
    assert body["plan_code"] == "free"
    assert body["status"] == "active"
    assert body["price"] == "0.00"
    # Replacing the plan cancels the prior row and starts a fresh one.
    sub2 = _subscribe(client, admin, org_id)
    assert sub2.status_code == 201, sub2.text
    assert sub2.json()["subscription"]["subscription_id"] != body["subscription_id"]
    rows = db.scalars(select(Subscription).where(Subscription.organization_id == org_id)).all()
    statuses = {r.status for r in rows}
    assert "cancelled" in statuses and "active" in statuses
    # Cancel the live one; a second cancel is a 404 (no live sub).
    canc = _cancel(client, admin, org_id)
    assert canc.status_code == 200 and canc.json()["subscription"]["status"] == "cancelled"
    again = _cancel(client, admin, org_id)
    assert again.status_code == 404, again.text
    # Lifecycle audited (end any open snapshot so the fresh reads see the
    # client's committed writes on the shared in-memory connection).
    db.commit()
    actions = {a for a in db.scalars(select(AuditLogEntry.action)).all()}
    assert "billing.subscription.created" in actions
    assert "billing.subscription.cancelled" in actions
    # Notifications delivered to billing readers.
    from app.models.career import UserNotification

    kinds = {n.kind for n in db.scalars(select(UserNotification)).all()}
    assert "billing" in kinds


def test_subscribe_only_catalog_plans_and_valid_intervals(client, make_user, db):
    admin, org_id = _billing_admin(client, make_user, db)
    # Unknown plan code -> 404 (no invented plans, no client plan ids).
    resp = _subscribe(client, admin, org_id, plan_code="platinum-plus")
    assert resp.status_code == 404, resp.text
    # Invalid billing interval -> 422 by schema.
    resp2 = _subscribe(client, admin, org_id, interval="weekly")
    assert resp2.status_code == 422, resp2.text


def test_subscription_state_transitions_are_explicit(client, make_user, db):
    admin, org_id = _billing_admin(client, make_user, db)
    sub = _subscribe(client, admin, org_id).json()["subscription"]
    # Only service code transitions state; the API exposes cancel only.
    row = db.get(Subscription, uuid.UUID(sub["subscription_id"]))
    from app.models.enums import SUBSCRIPTION_STATUS_CANCELLED

    row.status = SUBSCRIPTION_STATUS_CANCELLED  # simulate terminal state
    db.commit()
    # Terminal subscriptions cannot be silently resurrected by the API.
    resp = client.get(
        "/api/v1/billing/subscription",
        headers=admin["authorization"],
        params={"organization_id": str(org_id)},
    )
    assert resp.status_code == 200 and resp.json()["subscription"] is None


def test_entitlements_follow_free_catalog(client, make_user, db):
    admin, org_id = _billing_admin(client, make_user, db)
    ent = client.get(
        "/api/v1/billing/entitlements",
        headers=admin["authorization"],
        params={"organization_id": str(org_id)},
    )
    assert ent.status_code == 200, ent.text
    body = ent.json()["entitlements"]
    assert Decimal(body["jobs.create"]["limit"]) == Decimal("5")
    assert Decimal(body["ai.interview"]["limit"]) == Decimal("0")
    assert body["ai.interview"]["within_limit"] is True
    assert body["analytics"]["unlimited"] is True
    # Jobseeker-core feature is unlimited by design (never gated).
    assert "candidate.search" in body


def test_usage_records_are_tenant_scoped(client, make_user, db):
    admin_a, org_a = _billing_admin(client, make_user, db)
    admin_b, org_b = _billing_admin(client, make_user, db)
    commerce.record_usage(
        db,
        organization_id=org_a,
        actor_user_id=_user_id(db, admin_a["email"]),
        feature="analytics",
        quantity=3,
        reference_type="test",
    )
    db.commit()
    usage_a = commerce.usage_summary(db, org_a)
    usage_b = commerce.usage_summary(db, org_b)
    assert usage_a["analytics"] == 3
    assert usage_b["analytics"] == 0
    # Countable platform-table features also stay per-org.
    commerce.record_usage(
        db,
        organization_id=org_b,
        actor_user_id=_user_id(db, admin_b["email"]),
        feature="analytics",
        quantity=7,
    )
    db.commit()
    assert commerce.usage_summary(db, org_a)["analytics"] == 3
    assert commerce.usage_summary(db, org_b)["analytics"] == 7
    # Unknown feature codes and negative quantities are rejected.
    with pytest.raises(InvalidInputError):
        commerce.record_usage(db, organization_id=org_a, actor_user_id=uuid.uuid4(), feature="root.admin")
    with pytest.raises(InvalidInputError):
        commerce.record_usage(db, organization_id=org_a, actor_user_id=uuid.uuid4(), feature="analytics", quantity=-1)


# --- Money ---------------------------------------------------------------------

def test_money_is_decimal_and_quantized(client, make_user, db):
    admin, org_id = _billing_admin(client, make_user, db)
    tx = payments.create_payment_transaction(
        db,
        organization_id=org_id,
        actor_user_id=_user_id(db, admin["email"]),
        amount=Decimal("49.995"),
        currency="USD",
        description="decimal test",
        idempotency_key=f"money-{uuid.uuid4().hex}",
    )
    db.commit()
    assert isinstance(tx.amount, Decimal)
    assert tx.amount == Decimal("50.00")  # quantized to cents — never a float
    assert tx.refunded_amount == Decimal("0.00")
    inv = commerce.issue_invoice(
        db,
        organization_id=org_id,
        currency="USD",
        subtotal=Decimal("49.995"),
        items=[{"description": "line", "amount": "49.995", "quantity": 1}],
    )
    db.commit()
    assert isinstance(inv.total_amount, Decimal)
    assert inv.total_amount == (inv.subtotal_amount + inv.tax_amount)
    assert inv.subtotal_amount == Decimal("50.00")
    assert inv.invoice_number.startswith("INV-")


def test_amount_currency_and_refund_bounds_enforced(client, make_user, db):
    admin, org_id = _billing_admin(client, make_user, db)
    actor = _user_id(db, admin["email"])
    # Zero / negative payments.
    with pytest.raises(AppError) as zero:
        payments.create_payment_transaction(
            db, organization_id=org_id, actor_user_id=actor,
            amount=Decimal("0.00"), currency="USD", description="zero", idempotency_key=f"z-{uuid.uuid4().hex}",
        )
    assert zero.value.status_code == 402
    with pytest.raises(AppError) as neg:
        payments.create_payment_transaction(
            db, organization_id=org_id, actor_user_id=actor,
            amount=Decimal("-5.00"), currency="USD", description="neg", idempotency_key=f"n-{uuid.uuid4().hex}",
        )
    assert neg.value.status_code == 402
    # Bad currency.
    with pytest.raises(AppError) as cur:
        payments.create_payment_transaction(
            db, organization_id=org_id, actor_user_id=actor,
            amount=Decimal("5.00"), currency="US", description="cur", idempotency_key=f"c-{uuid.uuid4().hex}",
        )
    assert cur.value.status_code == 422
    # Negative invoice subtotal.
    with pytest.raises(AppError) as inv:
        commerce.issue_invoice(db, organization_id=org_id, currency="USD", subtotal=Decimal("-1.00"))
    assert inv.value.status_code == 422
    # Refunds: create a $100 payment, refund $120 -> rejected.
    tx = payments.create_payment_transaction(
        db, organization_id=org_id, actor_user_id=actor,
        amount=Decimal("100.00"), currency="USD", description="refundable", idempotency_key=f"r-{uuid.uuid4().hex}",
    )
    db.commit()
    with pytest.raises(AppError) as over:
        payments.create_refund(
            db, organization_id=org_id, actor_user_id=actor,
            transaction_id=tx.id, amount=Decimal("120.00"), reason="too much",
        )
    assert over.value.status_code == 402
    # Partial refund then full refund is fine; over again is not.
    partial = payments.create_refund(db, organization_id=org_id, actor_user_id=actor, transaction_id=tx.id, amount=Decimal("40.00"), reason="partial")
    db.commit()
    db.refresh(tx)
    assert tx.status == "partially_refunded"
    assert tx.refunded_amount == Decimal("40.00")
    # Refund idempotency: replaying an identical refund returns the SAME row
    # and never refunds twice.
    replay = payments.create_refund(db, organization_id=org_id, actor_user_id=actor, transaction_id=tx.id, amount=Decimal("40.00"), reason="partial")
    assert replay.id == partial.id
    db.commit()
    assert db.scalar(select(func.count(PaymentRefund.id))) == 1
    payments.create_refund(db, organization_id=org_id, actor_user_id=actor, transaction_id=tx.id, amount=Decimal("60.00"), reason="rest")
    db.commit()
    db.refresh(tx)
    assert tx.status == "refunded"
    assert tx.refunded_amount == Decimal("100.00")
    # Anything further fails safe (no negative balances, no double refunds).
    with pytest.raises(AppError):
        payments.create_refund(db, organization_id=org_id, actor_user_id=actor, transaction_id=tx.id, amount=Decimal("1.00"), reason="over")


def test_payment_idempotency_no_double_charge(client, make_user, db):
    admin, org_id = _billing_admin(client, make_user, db)
    key = f"idem-{uuid.uuid4().hex}"
    t1 = payments.create_payment_transaction(
        db, organization_id=org_id, actor_user_id=_user_id(db, admin["email"]),
        amount=Decimal("25.00"), currency="USD", description="idem", idempotency_key=key,
    )
    db.commit()
    t2 = payments.create_payment_transaction(
        db, organization_id=org_id, actor_user_id=_user_id(db, admin["email"]),
        amount=Decimal("25.00"), currency="USD", description="idem", idempotency_key=key,
    )
    db.commit()
    assert t1.id == t2.id
    assert db.scalar(select(func.count(PaymentTransaction.id))) == 1
    assert t1.provider_payment_id.startswith("mock_pay_")  # provider reference only


def test_provider_disabled_fails_safe(client, make_user, db, monkeypatch):
    admin, org_id = _billing_admin(client, make_user, db)
    # Simulate a deployment where payments are disabled.
    monkeypatch.setattr(
        payments, "get_settings", lambda: SimpleNamespace(payment_provider="none", payment_webhook_secret="")
    )
    with pytest.raises(AppError) as exc:
        payments.create_payment_transaction(
            db, organization_id=org_id, actor_user_id=_user_id(db, admin["email"]),
            amount=Decimal("10.00"), currency="USD", description="disabled", idempotency_key=f"d-{uuid.uuid4().hex}",
        )
    assert exc.value.status_code == 503  # payment.provider_unavailable — never fake success
    monkeypatch.undo()
    # The FREE plan path never touches a provider -> still works when disabled.
    monkeypatch.setattr(
        payments, "get_settings", lambda: SimpleNamespace(payment_provider="none", payment_webhook_secret="")
    )
    resp = _subscribe(client, admin, org_id, plan_code="free")
    assert resp.status_code == 201, resp.text
    assert resp.json()["subscription"]["status"] == "active"


# --- Webhooks ------------------------------------------------------------------

def _make_tx(client, make_user, db, amount: str = "100.00"):
    admin, org_id = _billing_admin(client, make_user, db)
    tx = payments.create_payment_transaction(
        db, organization_id=org_id, actor_user_id=_user_id(db, admin["email"]),
        amount=Decimal(amount), currency="USD", description="webhook fixture", idempotency_key=f"wh-{uuid.uuid4().hex}",
    )
    db.commit()
    return admin, org_id, tx


def test_webhook_missing_or_bad_signature_rejected(client, make_user, db):
    admin, org_id, tx = _make_tx(client, make_user, db)
    payload = {"event_id": f"evt-{uuid.uuid4().hex}", "type": "payment.succeeded", "payment_id": tx.provider_payment_id}
    body = json.dumps(payload).encode("utf-8")
    # No signature.
    resp = _webhook(client, body, None)
    assert resp.status_code == 400, resp.text
    # Wrong signature.
    resp2 = _webhook(client, body, "deadbeef" * 8)
    assert resp2.status_code == 400, resp2.text
    # Nothing persisted, no state change.
    assert db.scalar(select(func.count(PaymentWebhookEvent.id))) == 0
    db.refresh(tx)
    assert tx.status == "succeeded"


def test_webhook_valid_signature_processed_and_duplicate_safe(client, make_user, db):
    admin, org_id, tx = _make_tx(client, make_user, db)
    event_id = f"evt-{uuid.uuid4().hex}"
    payload = {"event_id": event_id, "type": "payment.succeeded", "payment_id": tx.provider_payment_id}
    first = _signed_event(client, payload)
    assert first.status_code == 200, first.text
    assert first.json()["status"] == "processed"
    # Duplicate delivery is detected (never processed twice).
    second = _signed_event(client, payload)
    assert second.status_code == 200, second.text
    assert second.json()["status"] == "duplicate"
    assert db.scalar(select(func.count(PaymentWebhookEvent.id))) == 1


def test_webhook_stale_event_ignored(client, make_user, db):
    admin, org_id, tx = _make_tx(client, make_user, db)
    stale = (datetime.utcnow() - timedelta(minutes=10)).isoformat()
    payload = {
        "event_id": f"evt-{uuid.uuid4().hex}",
        "type": "payment.succeeded",
        "payment_id": tx.provider_payment_id,
        "created": stale,
    }
    resp = _signed_event(client, payload)
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "ignored"  # replay window


def test_webhook_malformed_unknown_and_unconfigured_provider(client, make_user, db):
    admin, org_id, tx = _make_tx(client, make_user, db)
    provider = payments.get_payment_provider("mock")
    # Malformed JSON (valid signature) -> 400, no crash.
    body = b"{not json"
    resp = _webhook(client, body, provider.sign(body))
    assert resp.status_code == 400, resp.text
    # Unknown event type with a valid signature -> recorded + ignored.
    resp2 = _signed_event(client, {"event_id": f"evt-{uuid.uuid4().hex}", "type": "invoice.created", "payment_id": "x"})
    assert resp2.status_code == 200, resp2.text
    assert resp2.json()["status"] == "ignored"
    # Unknown provider -> fails safe (503), never silently accepted.
    body3 = json.dumps({"event_id": "x", "type": "payment.succeeded"}).encode()
    resp3 = client.post(
        "/api/v1/billing/webhooks/stripe", content=body3,
        headers={"Content-Type": "application/json", "X-Provider-Signature": provider.sign(body3)},
    )
    assert resp3.status_code == 503, resp3.text


def test_client_cannot_fake_payment_success(client, make_user, db):
    admin, org_id, tx = _make_tx(client, make_user, db)
    # A validly-signed webhook referencing an UNKNOWN payment cannot settle
    # anything — no fabricated transaction state.
    before = db.scalar(select(func.count(PaymentTransaction.id)))
    resp = _signed_event(client, {"event_id": f"evt-{uuid.uuid4().hex}", "type": "payment.succeeded", "payment_id": "nonexistent"})
    assert resp.status_code == 200 and resp.json()["status"] == "ignored"
    assert db.scalar(select(func.count(PaymentTransaction.id))) == before
    # And there is no route through which a client supplies an amount and
    # claims success: webhook bodies never carry amounts that mint records.
    bad = client.post(
        "/api/v1/billing/webhooks/mock",
        content=json.dumps({"event_id": "x", "type": "payment.succeeded", "amount": 999999}),
        headers={"Content-Type": "application/json", "X-Provider-Signature": payments.get_payment_provider("mock").sign(b'{"event_id": "x", "type": "payment.succeeded", "amount": 999999}')},
    )
    assert bad.status_code == 200 and bad.json()["status"] in ("ignored", "duplicate")


# --- Finance operations --------------------------------------------------------

def test_finance_requires_platform_role(client, make_user, db):
    admin, org_id = _billing_admin(client, make_user, db)
    # org billing.manage NEVER satisfies platform finance.
    for path in ("transactions", "refunds", "invoices", "subscriptions"):
        resp = client.get(f"/api/v1/finance/{path}", headers=admin["authorization"])
        assert resp.status_code == 403, f"{path}: {resp.text}"
    # customer_support (billing.read only) is not finance.
    support = make_user(f"support17{uuid.uuid4().hex[:6]}@example.com")
    _make_platform_membership(db, _user_id(db, support["email"]), role="customer_support")
    resp = client.get("/api/v1/finance/transactions", headers=support["authorization"])
    assert resp.status_code == 403, resp.text
    # finance role can read.
    fin = make_user(f"fin17{uuid.uuid4().hex[:6]}@example.com")
    _make_platform_membership(db, _user_id(db, fin["email"]), role="finance")
    ok = client.get("/api/v1/finance/transactions", headers=fin["authorization"])
    assert ok.status_code == 200, ok.text


def test_support_and_org_admin_cannot_authorize_refund(client, make_user, db):
    admin, org_id, tx = _make_tx(client, make_user, db)
    body = {"transaction_id": str(tx.id), "amount": "10.00", "reason": "test"}
    # Org admin (billing.manage) -> 403 on the PLATFORM finance surface.
    resp = client.post("/api/v1/finance/refunds", headers=admin["authorization"], json=body)
    assert resp.status_code == 403, resp.text
    # customer_support -> 403 (no finance.manage).
    support = make_user(f"supportr{uuid.uuid4().hex[:6]}@example.com")
    _make_platform_membership(db, _user_id(db, support["email"]), role="customer_support")
    resp2 = client.post("/api/v1/finance/refunds", headers=support["authorization"], json=body)
    assert resp2.status_code == 403, resp2.text
    assert db.scalar(select(func.count(PaymentRefund.id))) == 0


def test_finance_refund_workflow_audited_and_linked(client, make_user, db):
    admin, org_id, tx = _make_tx(client, make_user, db)
    fin = make_user(f"finaud{uuid.uuid4().hex[:6]}@example.com")
    _make_platform_membership(db, _user_id(db, fin["email"]), role="finance")
    resp = client.post(
        "/api/v1/finance/refunds",
        headers=fin["authorization"],
        json={"transaction_id": str(tx.id), "amount": "25.00", "reason": "courtesy"},
    )
    assert resp.status_code == 200, resp.text
    refund = resp.json()
    assert refund["status"] == "succeeded"
    assert refund["provider_refund_id"].startswith("mock_ref_")
    assert refund["amount"] == "25.00"
    db.refresh(tx)
    assert tx.refunded_amount == Decimal("25.00")
    assert tx.status == "partially_refunded"
    # Zero / negative amounts blocked at the schema boundary.
    for bad_amount in ("0.00", "-5.00"):
        resp2 = client.post(
            "/api/v1/finance/refunds",
            headers=fin["authorization"],
            json={"transaction_id": str(tx.id), "amount": bad_amount},
        )
        assert resp2.status_code == 422, resp2.text
    # Audited, with no sensitive content.
    actions = {a for a in db.scalars(select(AuditLogEntry.action)).all()}
    assert "finance.refund.authorized" in actions
    assert "billing.refund.succeeded" in actions
    for row in db.scalars(select(AuditLogEntry)).all():
        assert "password" not in str(row.payload).lower()
        assert "cvv" not in str(row.payload).lower()


def test_finance_surface_never_exposes_candidate_data(client, make_user, db):
    admin, org_id, tx = _make_tx(client, make_user, db)
    fin = make_user(f"finview{uuid.uuid4().hex[:6]}@example.com")
    _make_platform_membership(db, _user_id(db, fin["email"]), role="finance")
    rows = client.get(
        "/api/v1/finance/transactions",
        headers=fin["authorization"],
        params={"organization_id": str(org_id)},
    ).json()["transactions"]
    assert len(rows) == 1
    allowed = {
        "transaction_id", "organization_id", "provider", "provider_payment_id",
        "amount", "currency", "status", "description", "idempotency_key",
        "succeeded_at", "failed_at", "refunded_amount",
    }
    assert set(rows[0].keys()) == allowed
    assert "candidate" not in str(rows[0]).lower()
    assert "person" not in str(rows[0]).lower()
    # Provider references only — never card or credential fields.
    assert "card" not in str(rows[0]).lower()
    assert "cvv" not in str(rows[0]).lower()


# --- Athena never touches billing ----------------------------------------------

def test_athena_tool_registry_has_no_billing_mutation_tools(client):
    from app.services.athena_tools import TOOLS

    names = set(TOOLS.keys())
    forbidden_prefixes = ("billing.", "payment.", "subscription.", "refund.", "charge", "invoice.write", "plan.")
    for name in names:
        assert not name.lower().startswith(forbidden_prefixes), f"forbidden Athena tool: {name}"
    # No athena route performs billing mutations either.
    paths = [r.path for r in client.app.routes if getattr(r, "path", "").startswith("/api/v1")]
    joined = "\n".join(paths)
    assert "/athena" in joined
    athena_paths = [p for p in paths if "/athena" in p]
    for p in athena_paths:
        assert "billing" not in p and "refund" not in p and "payment" not in p, p


def test_high_risk_billing_requires_explicit_human_flow(client):
    """No Athena path exists to charge, refund, upgrade, downgrade or cancel.

    The confirmation framework (Phase 14) gates high-risk tools; billing
    mutations are not among them, so Athena structurally cannot perform one.
    """
    from app.core.ratelimit import RATE_LIMIT_POLICIES

    assert "athena.high_risk" in RATE_LIMIT_POLICIES  # gate exists and is wired
    paths = [r.path for r in client.app.routes if getattr(r, "path", "").startswith("/api/v1/athena")]
    assert paths  # Athena API exists
    # Billing state changes live only under /billing and /finance (org +
    # platform permission surfaces with audit); never under /athena.
    for p in paths:
        assert "billing" not in p and "finance" not in p, p


# --- Concurrent / isolation ----------------------------------------------------

def test_concurrent_orgs_isolated_in_usage_and_billing(client, make_user, db):
    a_admin, a_org = _billing_admin(client, make_user, db)
    b_admin, b_org = _billing_admin(client, make_user, db)
    _subscribe(client, a_admin, a_org)
    commerce.record_usage(db, organization_id=a_org, actor_user_id=_user_id(db, a_admin["email"]), feature="analytics", quantity=1)
    commerce.record_usage(db, organization_id=b_org, actor_user_id=_user_id(db, b_admin["email"]), feature="analytics", quantity=5)
    db.commit()
    # Simultaneous sessions: A can never resolve B's usage/invoices.
    a_usage = client.get(
        "/api/v1/billing/usage", headers=a_admin["authorization"], params={"organization_id": str(a_org)}
    ).json()["usage"]
    b_usage = client.get(
        "/api/v1/billing/usage", headers=b_admin["authorization"], params={"organization_id": str(b_org)}
    ).json()["usage"]
    assert a_usage["analytics"] == 1
    assert b_usage["analytics"] == 5
    cross = client.get(
        "/api/v1/billing/usage", headers=a_admin["authorization"], params={"organization_id": str(b_org)}
    )
    assert cross.status_code == 403, cross.text
