# PHASE 17 — SECURITY

## 1. Security model summary

Phase 17 adds money movement and billing state to the platform, so the
security bar is the highest yet. The model rests on the unchanged
Phase 13-16 controls plus commerce-specific boundaries:

- **Authentication** — every billing/finance route (except the
  signature-gated webhook) requires a bearer token.
- **Authorization** — org routes require membership in the target
  organization AND a role-scoped `billing.read`/`billing.manage`;
  finance routes require a platform-organization membership with
  `finance.read`/`finance.manage`.
- **Tenant isolation** — every org query is scoped by
  `organization_id` resolved from the caller's own memberships; the
  client-supplied `organization_id` query parameter is validated
  against the caller's memberships before any read/write.
- **Data minimization** — payment/finance outputs contain provider
  references, amounts, statuses, timestamps only. No card data, no
  credentials, no candidate data, no unrelated org data.
- **Audit** — all subscription, invoice, payment, refund and webhook
  transitions produce `audit_log` rows and `platform_events`
  (`billing.*` types).
- **Rate limiting** — `billing.change` (20/hour) protects subscription
  state changes; existing Athena/high-risk policies are unchanged.
- **Money** — Decimal over NUMERIC; validated currencies and amounts;
  refunds bounded by the paid amount; idempotency everywhere.
- **No secrets in code/docs/logs** — provider credentials are
  server-side env configuration only; `.env` is gitignored.

## 2. Adversarial coverage (tests in `test_commerce_phase17.py`)

| Attack | Result |
| --- | --- |
| Employer A reads Employer B subscription/invoices/entitlements/usage | 403 on every route |
| Employer B acts on A's subscription (subscribe/cancel) | 403 |
| Recruiter / HR / hiring manager opens billing on own org | 403 |
| Candidate (jobseeker, no membership) opens employer billing | 403 |
| User supplies a foreign `organization_id` | 403 |
| Client claims payment success | Impossible: no route mints transactions from client amounts; webhook is signature-gated; signed unknown-payment events are ignored |
| Fake webhook (missing/wrong signature) | 400, nothing persisted |
| Webhook replay / duplicate / stale event | duplicate / ignored |
| Refund over the paid amount, negative/zero amount | 402 / 422 |
| Duplicate refund | Idempotent — same row returned |
| Cross-org refund | 403 |
| Org `billing.manage` user reaches `/finance/*` | 403 (platform scope required) |
| `customer_support` authorizes a refund | 403 (no finance.manage) |
| Client tampers with plan id/price | Impossible: API accepts only `plan_code`; plan id/price come from the catalog |
| Athena mutates billing | Impossible: no billing tools in the Athena registry (39 tools unchanged) and no `/athena` route touches `/billing` or `/finance` |
| Provider disabled | 503 — no fabricated success, free-plan path still functions |
| Concurrent orgs | Usage/invoices remain isolated; simultaneous A/B sessions see only their own data |

## 3. Audit invariants

- Audit payloads never contain passwords, CVV, card numbers, or raw
  candidate answers; tests scan every audit row written during the
  finance/refund flows.
- Webhook audit rows store event ids/statuses — never raw payloads.

## 4. Hard-stop review

No security control from Phases 13-16 was weakened. No production
database was modified. No real money was moved. No secrets were
committed, printed, or written into documentation. Legacy backend (107
routes) and the 63 carried Phase-1 working-tree entries are untouched.
