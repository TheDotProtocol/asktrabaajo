# PHASE 17 — COMMERCE, BILLING, PAYMENTS, PLATFORM OPERATIONS

# Commerce & Billing Architecture

## 1. Scope and principles

AskTrabaajo's core jobseeker employment functionality is FREE and remains
free. Phase 17 does not introduce a paywall around Work ID, the core
profile, job discovery, applications, the employment journey, or core
career intelligence. Employer/company functionality is the only paid
surface, and it is expressed as *configuration*, never as hard-coded
pricing or route-level billing checks.

Commercial decisions that were deliberately NOT made in this phase:

- No final prices were invented. The only seeded plan is `free`
  (`commerce_plans.code = 'free'`, price `0.00`).
- No tax regime was hard-coded. Tax is a `tax_amount` field that is
  `0.00` everywhere; jurisdiction-specific calculation/compliance is
  explicitly out of scope (configurable later).
- No live payment provider was activated. The default provider is the
  deterministic `mock` sandbox; `none` is the safe degraded mode.
- No currency conversion or exchange rates are assumed anywhere.

## 2. Architectural position

Phase 17 extends the canonical architecture from Phase 14-16 (Athena
controlled intelligence, interview engine). Commerce sits below those
capabilities as platform infrastructure:

```
                    USER / EMPLOYER UI
                            │
                  ┌─────────┴──────────┐
                  │  /billing (org)    │  /finance (platform)
                  └─────────┬──────────┘
                            │
               ┌────────────┴────────────┐
               │     commerce service    │   plans, subscriptions,
               │     payments service    │   entitlements, usage,
               └────────────┬────────────┘   invoices, transactions,
                            │                refunds, webhooks
        ┌───────────────────┼───────────────────┐
        │   Provider abstraction (PaymentProvider)│
        │     mock  ·  none  ·  (future: stripe)  │
        └───────────────────┬───────────────────┘
                            │
                 canonical DB (NUMERIC money)
```

Rules that hold everywhere:

1. Jobseeker-core features never route through an entitlement check.
2. Paid-capability checks resolve centrally through
   `commerce.entitlements_for(org)` —
   User → Organization → Subscription → Plan → Entitlement.
3. No route embeds its own copy of a billing rule.
4. Money is `Decimal` over `NUMERIC(14,2)` columns with explicit ISO
   currency codes. Binary floats are never used for money.
5. Only provider *references* are stored — never CVV, card numbers, or
   credentials.
6. All state changes are audited with platform audit entries and events
   (`billing.*`).

## 3. Domain model (migration 0014, additive, 72 → 80 tables)

### `commerce_plans`
Configurable plan catalog: `code` (unique), `name`, `description`,
`billing_interval` (`month`/`year`), `currency`, `price` NUMERIC,
`active`, `published`, `seat_included`, `sort_order`, `metadata` JSON.
`active` keeps a catalog row usable; `published` makes it purchasable.

### `commerce_plan_entitlements`
Plan → feature code (`entitlement_code`) → numeric `limit_value`
(`NULL` = unlimited). Feature codes are the controlled
`ENTITLEMENT_CODES` set defined in `app/models/enums.py`:
`jobs.create`, `jobs.active`, `candidate.search`, `candidate.outreach`,
`ai.athena`, `ai.interview`, `analytics`, `premium_support`.

### `commerce_subscriptions`
ORGANIZATION-owned (never an individual employee's subscription).
Explicit lifecycle `trial → active → past_due/paused → cancelled /
expired` enforced by `SUBSCRIPTION_TRANSITIONS`. One live subscription
per org is enforced by the service (`_live_subscription`), with history
rows retained. `provider_subscription_id` is a reference only.

### `commerce_invoices`
NUMERIC invoice: `invoice_number` (unique), `currency`, `subtotal`,
`tax`, `total`, lifecycle `draft → issued → paid/void`, bounded JSON
line items, optional link to the settling `payment_transactions` row.

### `usage_records`
Tenant-scoped usage for countable features:
`organization_id + feature + quantity + actor + recorded_at`. Usage
summaries for features that map to real platform tables
(`job_postings`, `ai_interview_sessions`, etc.) are counted directly
from those tables via `_COUNTABLE_FEATURES`; the rest use explicit
records. Counts are always org-scoped.

### `payment_transactions`, `payment_refunds`, `payment_webhook_events`
See `PHASE_17_PAYMENTS.md` and `PHASE_17_WEBHOOK_SECURITY.md`.

## 4. New tables — justification (none duplicate existing domains)

| Table | Why an existing table is insufficient |
| --- | --- |
| `commerce_plans` | No plan/catalog concept existed; configuration needs its own owned, tenant-neutral catalog with price/interval/currency. |
| `commerce_plan_entitlements` | Plan→feature limits are a distinct many-to-many with numeric limits; embedding in plan JSON would bypass code-level validation of `ENTITLEMENT_CODES`. |
| `commerce_subscriptions` | Organization-level lifecycle with trial/period state, provider reference and audit requirements has no existing home (organizations table carries no billing state). |
| `commerce_invoices` | NUMERIC money + lifecycle + line items; the audit/event tables are append-only records, not financial documents. |
| `usage_records` | Countable usage is orthogonal to audit (high volume, no retention guarantees); an explicit tenant-scoped table is required. |
| `payment_transactions` | Provider payment attempts with idempotency keys, status lifecycle and provider references — none of the existing event/audit tables model money movement. |
| `payment_refunds` | Authorized, idempotent refunds against transactions with amounts ≤ paid; distinct lifecycle. |
| `payment_webhook_events` | Signature-verified provider envelope with (provider, event_id) uniqueness and replay/duplicate statuses; no raw payload is stored. |

RLS for these tables follows the Phase 13 staged design: service + API
layers enforce tenant isolation today (proven by tests); the
`asktrabaajo_app` least-privilege grants were extended to all 8 tables
(79 canonical tables × 4 DML privileges = 316 grants on PostgreSQL).

## 5. Subscriptions

- Free plan activates immediately (status `active`, no payment).
- A paid plan (added later by an operator as a catalog row) starts in
  `trial`, settles one sandbox payment transaction, issues an invoice,
  and moves to `active`. A change never charges silently.
- The API only accepts a `plan_code`; the plan id, price and currency
  come from the catalog. A client can never supply a plan id or price.
- Replacing a live subscription cancels the prior row (audited) and
  starts a fresh one.
- `billing.subscription.created`, `billing.subscription.cancelled` and
  `billing.subscription.expired` audit actions and
  `billing.subscription.changed` / `billing.invoice.issued` events are
  emitted on every transition.

## 6. Entitlements resolution

`entitlements_for(org_id)` returns every `ENTITLEMENT_CODES` feature
with `{limit, used, remaining, unlimited, within_limit}`. The plan is
the live subscription's plan, or the FREE plan when no subscription
exists — so an organization always resolves against a safe default and
jobseeker-core features are never gated.

## 7. Usage

`record_usage` validates the feature code and quantity (never
negative), writes a tenant-scoped row and audits. `usage_summary`
returns one count per entitlement feature for the organization only.
Cross-tenant usage leakage is prevented at the query boundary and
covered by tests.

## 8. Athena + billing

Athena has NO billing-mutation tools: the Phase-14/15 tool registry
(39 tools) contains no charge/refund/upgrade/downgrade/cancel tool, and
no `/athena` route can reach `/billing` or `/finance`. Billing state
changes are organization-scoped (billing.manage) or platform-scoped
(finance.manage) human surfaces only. This is asserted by tests.
Future read-only Athena billing answers must be added as explicit,
permission-aware, read-only tools behind the same registry.
