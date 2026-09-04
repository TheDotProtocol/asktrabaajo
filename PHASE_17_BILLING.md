# PHASE 17 — BILLING

## 1. Surfaces

### Organization self-service — `/api/v1/billing/*` (9 routes)

| Route | Permission | Purpose |
| --- | --- | --- |
| `GET /billing/plans` | any authenticated user | Public-ish catalog (jobseeker core is free; the free plan is listed) |
| `GET /billing/subscription?organization_id=` | `billing.read` | Current live subscription (or `null`) |
| `POST /billing/subscriptions?organization_id=` | `billing.manage` | Start/replace a catalog-plan subscription |
| `POST /billing/subscriptions/cancel?organization_id=` | `billing.manage` | Cancel the live subscription (audited) |
| `GET /billing/entitlements?organization_id=` | `billing.read` | Plan limits + current usage per feature |
| `GET /billing/usage?organization_id=` | `billing.read` | Org-scoped usage summary |
| `GET /billing/invoices?organization_id=` | `billing.read` | Org invoice list |
| `GET /billing/invoices/{id}?organization_id=` | `billing.read` | Invoice detail (org-scoped — 404 for other orgs) |
| `POST /billing/webhooks/{provider}` | signature-gated (not auth) | Provider webhook intake |

Every org route requires the caller to be a member of the target org
WITH the role-scoped `billing.read` / `billing.manage` permission.
Membership alone is never enough. Rate-limit policy `billing.change`
(20/hour, org-keyed user) protects subscription state changes.

## 2. Billing roles and least privilege

From the canonical permission catalog:

- `org_admin` → `billing.read`, `billing.manage` (employer org).
- `hr`, `recruiter`, `hiring_manager` → NO billing permissions.
- `customer_support` (platform) → `billing.read` only.
- `finance` (platform) → `billing.read`, `billing.manage`,
  `finance.read`, `finance.manage`, `audit.read`.

A recruiter/hiring-manager cannot open billing even for their own
organization. A support agent can *view* billing context needed for a
case but can never mutate it and can never reach the `/finance`
platform surface (tests assert both directions).

## 3. Subscription lifecycle

Explicit, service-enforced transitions
(`SUBSCRIPTION_TRANSITIONS` in `app/models/enums.py`):

```
trial ──▶ active ──▶ past_due ──▶ active / cancelled / expired
  │                    │
  └── past_due ──▶ ... └── paused ──▶ active / cancelled / expired
cancelled / expired: terminal (no outgoing transitions)
```

- One live subscription per org (`active/trial/past_due/paused`);
  history rows are retained.
- Trial expiry is deterministic lazy expiry evaluated when the live
  subscription is next read (no scheduler required).
- Replacing a plan cancels the live row (`reason=replaced`) and starts
  a fresh subscription.
- Terminal states cannot be resurrected by the API (tested).

## 4. Catalog and pricing control

- `POST /subscriptions` accepts only `{plan_code, billing_interval}`.
- The plan must exist in the catalog AND be `active` and `published` —
  otherwise 404 (no invented plans, no client-supplied plan id/price).
- `billing_interval` is validated by schema (`month`/`year`) and must
  be offered by the plan.
- Money never crosses the client as a price input; amounts are always
  echoed from catalog/service records as strings over the wire.

## 5. Invoices

- Created `draft`, transitioned `issued`, then `paid` when linked to a
  settled payment transaction. `void` is reserved for operator flows.
- `invoice_number` is unique, generated as `INV-{ORG}-{seq}`.
- Line items are bounded (≤ 20), plain `{description, amount,
  quantity}` JSON — never free-form PII.
- Invoice totals are computed as `Decimal` and stored NUMERIC.
- `tax` is `0.00` (jurisdiction-specific tax configuration is
  explicitly out of scope for this phase).

## 6. Tests

Billing-specific assertions in the Phase-17 suite cover: plan catalog
content, RBAC (org_admin vs hr/recruiter/hiring_manager vs stranger),
cross-org isolation on every billing route, candidate exclusion,
subscription lifecycle and replacement, catalog-only plan codes,
invalid transitions, entitlement resolution, usage tenancy, and the
absence of any Athena path into billing.
