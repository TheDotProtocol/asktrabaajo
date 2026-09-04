# PHASE 17 — WEBHOOK SECURITY

## 1. Route

`POST /api/v1/billing/webhooks/{provider}` — the ONLY unauthenticated
billing route, and deliberately so: providers do not authenticate like
users. Its entire security model is the provider signature. The raw
request body is read directly (`Request.body()`) so signature
verification always covers the exact transmitted bytes regardless of
content-type parsing.

## 2. Handling pipeline (enforced in this order)

```
raw body + headers
   │
   ▼
① provider resolution  ── unknown/unconfigured provider → 503 (fail safe)
   │
   ▼
② signature verification ── HMAC-SHA256 over the raw body; failure
   │                          → 400 payment.webhook_invalid
   │                          → audit billing.webhook.rejected
   ▼
③ payload parse ── malformed JSON / non-object → 400
   │
   ▼
④ event identity ── event_id required (else 400)
   │
   ▼
⑤ replay window ── stale `created` (> 300s) → recorded + ignored
   │
   ▼
⑥ (provider, event_id) uniqueness ── duplicate of a processed event
   │                                  → status `duplicate`, no re-run
   ▼
⑦ supported event mapping ── known types apply safe transitions;
                              unknown types are recorded + ignored
   │
   ▼
⑧ audit billing.webhook.received / verified / rejected
```

## 3. Attack coverage

| Attack | Behavior |
| --- | --- |
| Missing signature | 400 before any processing |
| Wrong signature | 400 (HMAC compare is constant-time), nothing persisted |
| Client imitating a provider | The route is signature-gated; no amount/state can be fabricated by an unsigned client |
| Validly signed payload referencing an unknown payment | Recorded + ignored — no transaction state is invented |
| Duplicate delivery | Second delivery of a processed `event_id` → `duplicate`, processed once |
| Replay of a stale event | `created` older than the 300s window → `ignored` |
| Malformed payload | 400 |
| Unknown event type | Recorded + ignored; the intake never crashes |
| Unknown provider | 503 — never silently accepted |
| Out-of-order events | Safe transitions only; `payment.failed` after `succeeded` is rejected by `mark_payment_failed`'s state gate |

## 4. State transitions applied by webhooks

- `payment.succeeded` on a `pending`/`failed` transaction → `succeeded`
  (+ audit). On an already-`succeeded` transaction it is a no-op that
  still records the verified event.
- `payment.failed` → marks the matching transaction failed via
  `mark_payment_failed` (state-gated; a succeeded/refunded/cancelled
  payment cannot be flipped to failed).

## 5. Storage policy

`payment_webhook_events` stores the envelope ONLY: provider, event_id
(unique per provider), event_type, status, signature validity, bounded
note, timestamps. The raw payload is never persisted.

## 6. Tests

The Phase-17 suite covers: missing/bad signature rejection with no
state change, valid-signature processing, duplicate detection
(one event row), stale replay rejection, malformed payload, unknown
event type, unknown provider, and the client-cannot-fake-success
property (a signed event for a nonexistent payment id changes nothing).
The same flow passed end-to-end on PostgreSQL 16.
