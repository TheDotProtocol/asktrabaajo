# PHASE 17 REPORT — COMMERCE, BILLING, PAYMENTS, PLATFORM OPERATIONS

Project: AskTrabaajo / Trabaajo 2.0 · AI: Athena
Canonical branch: `main` (Phase 16 HEAD `bedf666` → Phase 17 commits)

## 1. Executive summary

Phase 17's first objective — clearing the live Supabase blocker safely —
remains BLOCKED, but it is now fully characterized with a precise,
single operator action documented (supply a current pooler/direct
PostgreSQL connection string into the gitignored `backend/.env` under
`DATABASE_URL`). No host/region was guessed, no live database was
touched, and no migration was attempted against production.

On the commerce objective, the full domain was built on the canonical
architecture with the highest security bar in the project:

- **Migration 0014** (additive, 72 → 80 tables): eight justified
  tables — plans, plan entitlements, subscriptions (org-owned,
  explicit state machine), invoices, usage records, payment
  transactions, refunds, and signature-verified webhook events. Only
  the FREE plan (price 0.00) is seeded; no pricing is invented.
- **Commerce service**: catalog + subscription lifecycle +
  centralized entitlements + tenant-scoped usage, all Decimal/NUMERIC.
- **Payments service**: provider-neutral `PaymentProvider` abstraction
  (mock sandbox default, `none` safe-degraded, no production vendor
  wired); idempotent transactions and refunds; bounded, audited,
  provider-linked refunds.
- **Webhooks**: HMAC signature verification over raw bytes, replay
  window, duplicate-safe uniqueness, no raw payload storage.
- **Finance operations**: platform-scope `/finance/*` separated from
  org self-service `/billing/*`; refund authorization requires the
  platform `finance.manage` permission; support and org billing
  admins cannot refund.
- **Athena boundary**: the tool registry (39 tools) contains NO billing
  mutation tools and no `/athena` route reaches `/billing` or
  `/finance` — the AI structurally cannot charge, refund, upgrade, or
  cancel (asserted by tests).
- **Frontend**: org-scoped `/employer/billing` dashboard (plan,
  entitlements + usage bars, invoices, start/cancel) + API types;
  typecheck/lint/build green.
- **Test result: 244 passed, 11 skipped, 0 failed** (25 new Phase-17
  tests). RLS: 11/11 on PostgreSQL 16 with 0014 present. Migration
  roundtrip clean on SQLite and PostgreSQL 16; `P17_PG_SMOKE_PASS`
  end-to-end; legacy backend unchanged at 107 routes.

## 2. Supabase blocker (first objective)

- Code verification: the app consumes a single `DATABASE_URL`
  (SQLAlchemy URL) via `settings.database_url` →
  `create_engine`; `.env` is loaded by Settings and `backend/.env` is
  gitignored.
- Current state: `backend/.env` holds a `DATABASE_URL` whose host is
  the retired direct database host for project `zrvrjqwboylvvzusorry`
  (no longer resolves). The project host itself is alive; the stored
  anon key is stale (401). No pooler host was guessed.
- Operator action: paste the current Supabase PostgreSQL connection
  string (direct or pooler, exactly as shown in the dashboard) into
  `backend/.env` under `DATABASE_URL=…` — full, secret-safe
  instructions and the read-only verification gate are in
  `PHASE_17_SUPABASE_CONNECTION.md`.
- Nothing was deployed, stamped, repaired, or modified on the live
  project.

## 3. What was built

### 3.1 Domain (migration 0014)
Eight tables + FREE-plan catalog seed. Each table is organization- or
catalog-scoped with NUMERIC money and provider references only. Full
justifications (why existing tables are insufficient) in
`PHASE_17_COMMERCE_ARCHITECTURE.md`.

### 3.2 Services
- `app/services/commerce.py` — `list_plans`, `subscribe`,
  `cancel_subscription`, `entitlements_for`, `usage_count/summary`,
  `record_usage`, `issue_invoice`, `mark_invoice_issued/paid`,
  serializers. Lazy trial expiry; explicit transition map; audit +
  events + billing notifications on every transition.
- `app/services/payments.py` — `PaymentProvider` ABC,
  `MockPaymentProvider`, `get_payment_provider`, idempotent
  `create_payment_transaction`, bounded idempotent `create_refund`,
  signature/replay/duplicate-safe `handle_provider_webhook`.

### 3.3 API (246 canonical `/api/v1` routes; +14)
- `/api/v1/billing/*` (9): org self-service + signature-gated
  webhook intake.
- `/api/v1/finance/*` (5): platform finance read + refund
  authorization.
- Rate-limit policy `billing.change` added (registry now 17).

### 3.4 Tests (25 new)
Cross-org isolation, RBAC (org vs platform), money math, refund
bounds/idempotency, provider-outage fail-safe, webhook adversarial
matrix, finance separation, Athena-no-billing-mutation, concurrent-org
isolation.

### 3.5 Frontend
`/employer/billing` org dashboard + Phase-17 API types. Built and
routed green.

## 4. Validation

| Check | Result |
| --- | --- |
| SQLite suite | 244 passed · 11 skipped · 0 failed |
| New Phase-17 tests | 25 (all passing) |
| PostgreSQL 16 roundtrip | 0013 → 0014 → 0013 → 0014 clean |
| App-role grants (PG) | 316 = 79 canonical tables × 4 DML |
| RLS suite (PG) | 11/11 passing with 0014 |
| PG commerce smoke | `P17_PG_SMOKE_PASS` (Decimal money, refunds, webhooks, isolation, notifications) |
| Schema parity | models == migration head (80 tables) |
| Canonical routes | 246 `/api/v1` |
| Legacy backend | 107 routes (unchanged) |
| Frontend | typecheck 0 · lint 0 new errors · production build green (`/employer/billing` in manifest) |

## 5. Git

Phase 17 commits are logical groups on `main`; nothing was pushed; the
63 carried Phase-1 working-tree entries remain untouched and
uncommitted; the working tree returns to exactly those entries after
the commits.

## 6. Companion documents

`PHASE_17_COMMERCE_ARCHITECTURE.md` · `PHASE_17_BILLING.md` ·
`PHASE_17_PAYMENTS.md` · `PHASE_17_ENTITLEMENTS.md` ·
`PHASE_17_WEBHOOK_SECURITY.md` · `PHASE_17_FINANCE_OPERATIONS.md` ·
`PHASE_17_SECURITY.md` · `PHASE_17_MIGRATION.md` ·
`PHASE_17_SUPABASE_CONNECTION.md`

---

PHASE 17 STATUS:
PASS WITH LIMITATIONS

SUPABASE CONNECTION:
BLOCKED

DATABASE IDENTITY:
BLOCKED

BACKUP/PITR:
UNKNOWN

LIVE MIGRATION:
BLOCKED

LIVE MIGRATION REVISION:
UNKNOWN

LOCAL MIGRATION REVISION:
0014

SCHEMA DRIFT:
UNKNOWN

RLS:
NOT ENABLED

APP ROLE:
VERIFIED

COMMERCE:
IMPLEMENTED

BILLING:
IMPLEMENTED

PAYMENTS:
MOCKED

WEBHOOKS:
PASS

ENTITLEMENTS:
PASS

FINANCE:
PASS

ATHENA BILLING:
PASS

SECURITY:
PASS WITH LIMITATIONS

FRONTEND:
INTEGRATED

TESTS:
244 PASSED
0 FAILED
11 SKIPPED

NEW TABLES:
8 — commerce_plans, commerce_plan_entitlements, commerce_subscriptions,
commerce_invoices, usage_records, payment_transactions,
payment_refunds, payment_webhook_events (justification per table in
PHASE_17_COMMERCE_ARCHITECTURE.md §4)

NEW MIGRATION:
0014 (commerce_billing_payments)

PRODUCTION CHARGES:
NONE

LEGACY BACKEND:
107 ROUTES — VERIFY UNCHANGED (verified: 107 total routes)

CARRIED PHASE-1 ENTRIES:
VERIFY UNTOUCHED (verified: 63 entries untouched)

BLOCKERS:
1. Live Supabase SQL credentials unavailable (unchanged since Phase 13).
   Operator action: place a current Supabase PostgreSQL/pooler
   connection string in backend/.env under DATABASE_URL, then run the
   read-only verification gate in PHASE_17_SUPABASE_CONNECTION.md.
2. Backup/PITR status of the live project unverifiable until connected.
3. No production payment/AI/voice provider provisioned (by design in
   this phase — mock/sandbox only).

OWNER ACTIONS:
1. Supply the current Supabase connection string into backend/.env
   (gitignored) as DATABASE_URL, then approve the read-only identity +
   migration-history + backup/PITR verification described in
   PHASE_17_SUPABASE_CONNECTION.md.
2. Decide real plan codes + prices when ready — add them as catalog
   rows (commerce_plans + commerce_plan_entitlements); no code change
   required.
3. Decide and configure a production payment provider under
   PAYMENT_PROVIDER only after the deployment runbook is green.
4. Run scripts/db/app_role.sql on the live database as a superuser
   during the approved deployment (never from the app role).

PHASE 18 RECOMMENDATION:
- Execute the Phase 13/17 deployment runbook once the connection
  blocker clears: read-only baseline, backup/PITR verification,
  drift reconciliation, migration 0001-0014, app role, staged RLS.
- Enforce entitlement gates at the service boundary for paid employer
  features (job posts, outreach, AI interview usage) now that the
  entitlement + usage infrastructure is verified.
- Wire a real provider adapter behind PaymentProvider with sandbox
  keys (never production), plus the retention/archive job for payment
  and usage records.
- Build the Athena read-only billing Q&A tools ("what plan are we on?",
  "how many postings left?") behind the Phase-14 registry with
  billing.read, keeping all mutations human-only.
