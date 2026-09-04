# PHASE 17 — MIGRATION

## Migration 0014 — `commerce, billing, payments, entitlements, usage`

- Revision file: `backend/alembic/versions/0014_commerce_billing_payments.py`
- Down revision: `0013`
- Type: STRICTLY ADDITIVE. No existing table, column, index, constraint,
  or policy is modified or dropped. Rollback drops exactly the eight new
  tables and the FREE-plan seed rows.
- Table count: 72 → 80 (79 canonical tables + `alembic_version`).

## Tables created

1. `commerce_plans`
2. `commerce_plan_entitlements`
3. `commerce_subscriptions`
4. `commerce_invoices`
5. `usage_records`
6. `payment_transactions`
7. `payment_refunds`
8. `payment_webhook_events`

Justification for each table (why existing tables are insufficient) is
in `PHASE_17_COMMERCE_ARCHITECTURE.md` §4.

## Seed data

The FREE plan catalog row (`code='free'`, price `0.00`) plus its eight
entitlement rows are inserted idempotently by the migration. A service
helper (`commerce.ensure_default_catalog`) mirrors the same seed for
environments built with `create_all` (the test harness).

## Validation performed

### SQLite (canonical test suite)
- Migration upgrades to head cleanly; schema-parity test asserts
  `Base.metadata` == alembic head table set (80 tables) — this test
  caught and forced the fix of a string-quoting syntax error in the
  seed block before it could reach any environment.
- Full suite: **244 passed, 11 skipped, 0 failed**.

### PostgreSQL 16 (scratch `p14_test`, local only)
- `upgrade head`: 0013 → 0014 clean (80 tables).
- `downgrade 0013`: clean (72 tables).
- `upgrade head` again: clean (0014, 80 tables).
- Least-privilege grants re-applied: 79 canonical tables × 4 DML =
  **316 privileges** for `asktrabaajo_app` (no DDL, no superuser, no
  legacy-schema grants).
- RLS suite: **11/11 passing** with migration 0014 present.
- End-to-end commerce smoke (`P17_PG_SMOKE_PASS`): free subscription,
  Decimal money, idempotent payment, bounded/partial refunds,
  cross-org refund denial, signed webhook processing + duplicate
  rejection, invoice settlement, billing notifications, tenant-scoped
  usage.

## Live database policy

Migration 0014 has been applied to the scratch PostgreSQL ONLY. It has
NOT been applied to the live Supabase project
(`zrvrjqwboylvvzusorry`) because live database access remains blocked
(see `PHASE_17_SUPABASE_CONNECTION.md`). No destructive operation, no
`alembic stamp`, and no manual repair was performed anywhere.
