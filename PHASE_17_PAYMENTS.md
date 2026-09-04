# PHASE 17 — PAYMENTS

## 1. Provider-neutral abstraction

`services/payments.py` defines a `PaymentProvider` interface and the
payment domain logic; business code never imports a vendor.

```python
class PaymentProvider(ABC):
    create_payment(*, amount, currency, description) -> dict
    refund(*, provider_payment_id, amount, currency) -> dict
    verify_webhook_signature(*, body, headers) -> bool
```

Providers are configuration-driven through
`settings.payment_provider` (`PAYMENT_PROVIDER` env):

- `mock` (default) — deterministic sandbox; never real money.
  Generates `mock_pay_*` / `mock_ref_*` references and signs webhook
  bodies with HMAC-SHA256 using `payment_webhook_secret`
  (`PAYMENT_WEBHOOK_SECRET`; dev fallback only when unset).
- `none` — payments disabled; every payment/refund attempt fails safe
  with `503 payment.provider_unavailable`. The FREE plan path never
  touches a provider, so the platform still boots and functions.
- `stripe` is accepted by the config validator but intentionally NOT
  wired in this phase — no production provider, no production charges.
  `get_payment_provider("stripe")` raises `503` rather than pretend.

No API key, no vendor credential, and no card data ever enter the
application, the database, or the logs.

## 2. Payment data policy

Stored fields are provider references only:

- `provider_customer_id`, `provider_payment_id`,
  `provider_subscription_id`, `provider_refund_id`.

NEVER stored: CVV, raw card numbers, full bank credentials, or private
payment credentials. Tests assert no card/cvv fields exist on any
finance output and that audit payloads carry only metadata.

## 3. Transactions

`payment_transactions` records one provider payment attempt:
organization, provider, amount NUMERIC, currency, status
(`pending → succeeded / failed / cancelled`, plus
`partially_refunded / refunded`), idempotency key, failure code,
provider references, timestamps.

- Idempotent on `idempotency_key` (unique constraint): a replay returns
  the existing transaction and never charges twice.
- Amounts are `Decimal` quantized to cents; zero/negative amounts are
  rejected (`402 payment.failed`); currency must be a valid ISO code.
- Only the backend/provider/webhook path can mark a payment failed —
  a client can never claim success or failure for a transaction it
  does not own.

## 4. Refunds

`payment_refunds` — authorized, idempotent, provider-linked refunds.

- Idempotency key is derived: `refund:{transaction_id}:{amount}` — an
  exact replay returns the existing refund row (checked BEFORE the
  state gate, so retries after a partial refund are safe).
- Refunds are allowed only while the transaction is in a paid state
  (`succeeded` / `partially_refunded`) and never exceed the remaining
  refundable balance (`paid − refunded`). A fully-refunded transaction
  cannot be refunded further.
- Refunds must be org-matching: org B cannot refund org A's
  transaction (`403`).
- Every refund emits `finance.refund.authorized`,
  `billing.refund.created` and `billing.refund.succeeded` audit rows.
- Refunds are authorized by a human through `/finance/refunds`
  (finance.manage) or the future org self-service refund flow
  (billing.manage); there is no autonomous/Athena refund path.

## 5. Money handling

- Storage: `NUMERIC(14,2)` columns, values always `Decimal`.
- Arithmetic is `Decimal` with `.quantize(0.01)`; floats are never used
  for money (tests assert `Decimal` instances and cent-quantized
  values, e.g. `49.995 → 50.00`).
- Currency is explicit ISO (`USD`, `INR`, `THB`, `EUR`, …). No silent
  conversion and no exchange-rate assumptions exist anywhere.
- Wire format for amounts is decimal strings (`"199.99"`), not floats.

## 6. Invoice ↔ payment link

A settled payment can settle an invoice (`invoice.payment_transaction_id`
+ status `paid` + `paid_at`). Free-plan subscriptions create no
invoice; paid-plan subscriptions create one invoice per settlement.

## 7. Failure model

- Provider disabled → `503`; no fabricated success, no fallback that
  "performs the action anyway".
- Malformed amounts/currency → `422` invalid input.
- Refund over the refundable amount → `402`.
- Unknown/unsupported webhook events → recorded + ignored; they never
  crash the intake path.
