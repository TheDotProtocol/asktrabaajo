# PHASE 17 — FINANCE OPERATIONS

## 1. Separation of duties

Three distinct authority levels exist; none overlaps by accident:

| Actor | Scope | Can do |
| --- | --- | --- |
| Org `billing.manage` holder | Their own organization only | Change/cancel own subscription, view own billing |
| Platform `customer_support` | Org context for cases | Read billing context (`billing.read`); CANNOT mutate billing or reach finance |
| Platform `finance` role | Platform-wide finance | `finance.read`, `finance.manage` on `/finance/*` |

Crucially, `billing.manage` at the organization level NEVER satisfies a
platform finance permission. `has_platform_permission` additionally
requires membership in a `platform`-kind organization, so an employer's
org admin can never reach `/api/v1/finance/*` even with a valid
organization id (tested).

## 2. Routes — `/api/v1/finance/*` (5 routes)

| Route | Permission | Purpose |
| --- | --- | --- |
| `GET /finance/transactions` | `finance.read` | Transaction search (optional org filter) |
| `GET /finance/refunds` | `finance.read` | Refund inspection (optional org filter) |
| `GET /finance/invoices` | `finance.read` | Invoice search |
| `GET /finance/subscriptions` | `finance.read` | Subscription inspection |
| `POST /finance/refunds` | `finance.manage` | Authorize a refund against a transaction |

Output is deliberately narrow: transaction/refund rows expose provider
references, amounts, statuses and timestamps — never card data,
credentials, candidate data, or unrelated organization data (tests
assert the exact allowed key sets).

## 3. Refund workflow

1. A `finance.manage` holder submits `{transaction_id, amount, reason}`.
2. The transaction must exist and belong to a paid state.
3. The refund must be ≤ remaining refundable balance; org-mismatched
   transactions are rejected at the service layer.
4. The provider refund executes through the provider abstraction
   (mock in this phase), and the row records the provider reference.
5. Audit: `finance.refund.authorized`, `billing.refund.created`,
   `billing.refund.succeeded`. Transaction `refunded_amount` and status
   are updated (`partially_refunded` / `refunded`).
6. Replays of the identical refund are idempotent (return the existing
   refund row; no double refund).

Zero/negative amounts are rejected at the schema boundary (422).

## 4. What finance is NOT

- Finance surfaces never accept or expose candidate/person identifiers
  — candidate data is structurally unreachable here.
- Refunds are never autonomous: no Athena tool, no webhook, and no
  org-role can authorize one.
- No production money movement exists in this phase (mock provider).

## 5. Tests

`test_finance_requires_platform_role`, `test_support_and_org_admin_
cannot_authorize_refund`, `test_finance_refund_workflow_audited_and_
linked`, and `test_finance_surface_never_exposes_candidate_data` cover
the finance RBAC boundary, the refund lifecycle with audit and provider
linkage, schema-level amount validation, and output minimization.
