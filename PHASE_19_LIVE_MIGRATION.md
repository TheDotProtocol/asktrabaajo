# Phase 19 — Live Migration

## Status

**LIVE RECONCILIATION: NOT APPLIED** — the operator chose to skip live writes pending Backup/PITR confirmation (mandatory gate). Everything below is the validated, ready-to-execute plan with the exact commands.

## Pre-migration baseline (captured read-only, project `zrvrjqwboylvvzusorry`)

Re-verified live at Phase 19 start — identical to the Phase 18 baseline:

| Check | Value |
|---|---|
| PostgreSQL / DB / schema / TZ | 17.6 / `postgres` / `public` / UTC |
| `alembic_version` | ABSENT |
| `asktrabaajo_app` | ABSENT |
| Public tables | 21 (all legacy) |
| Legacy row counts | `company_departments` 4,896 · `jobs` 222 · `companies` 117 · `department_catalog` 48 · `offices` 10 · `profiles` 1 · remaining 15 tables 0 |
| `interviews` facts | **0 rows · 0 incoming FKs · RLS on · 2 policies · 1 trigger** — unchanged |

The `interviews` facts were re-verified live immediately before this phase's decision point; all conditions for the validated rename still hold. The full baseline is preserved in this phase's records (not in this repository).

## Execution plan (validated in simulation, NOT run)

```bash
# 1. Pre-flight (read-only): expect interviews_rows=0, incoming_fks=0
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f scripts/db/reconcile_legacy_interviews.sql   # step 0 only

# 2. Single controlled rename (nothing else)
ALTER TABLE public.interviews RENAME TO legacy_asktrabaajo_interviews;

# 3. Bootstrap the canonical schema (transactional; additive 0001-0014)
alembic upgrade head

# 4. Least-privilege app role + 316 grants (79 canonical tables x 4)
psql "$DATABASE_URL" -f scripts/db/app_role.sql
```

Expected post state: `alembic_version=0014`; **101 tables** (21 legacy + 80 canonical); legacy counts unchanged; role not superuser, no createdb/createrole, zero legacy grants.

## Gates

1. **Backup/PITR confirmed by operator** (dashboard → Project Settings → Backups / PITR) — currently **NOT CONFIRMED**.
2. Operator go-ahead — currently **DECLINED** (skip live writes).
3. Re-run the pre-flight verification immediately before execution; if `interviews` gains rows or incoming FKs, STOP.

## Rollback

- Rename reversal (only before canonical `interviews` exists): `ALTER TABLE legacy_asktrabaajo_interviews RENAME TO interviews;`
- Canonical schema: `alembic downgrade base` (all migrations additive with downgrades).
- Role: revoke grants, `DROP ROLE asktrabaajo_app`.

Nothing in this plan modifies, deletes, or transforms any legacy row.