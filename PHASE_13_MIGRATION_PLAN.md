# PHASE 13 — MIGRATION PLAN

## What exists

- Canonical Alembic chain `0001`–`0010` (head `0010`), 63 tables on
  PostgreSQL (62 canonical + `alembic_version`).
- `0010` is the Phase 13 RLS stage-1 migration: idempotent
  owner-scoped policies on 6 strictly private tables; no-op on SQLite.
- `scripts/db/app_role.sql` — guarded artifact creating the
  least-privilege `asktrabaajo_app` runtime role + table-DML grants on
  the 62 canonical tables (idempotent; verified on scratch PG).

## Deployment status

| Step | Status |
|---|---|
| Migrations `0001`–`0009` on SQLite | DONE (Phases 3–11) |
| Migrations `0001`–`0010` on local PostgreSQL | DONE (Phase 13: fresh `upgrade head`; `0010` downgrade → re-upgrade) |
| App-role SQL on local PostgreSQL | DONE (scratch DB; idempotent re-run OK) |
| RLS hostile tests on local PostgreSQL | DONE (11/11 green) |
| Migrations on the **live Supabase project** | **BLOCKED — live SQL credentials/endpoint unavailable** (retired direct hostname; pooler tenant not found on probed regions). No live change was made |

## Exact live-deployment runbook (for when credentials are approved)

Preconditions (owner actions):

1. **Rotate** Supabase anon + service-role keys, DB password, SMTP,
   OpenAI, JWT secret (Phase 1/12 backlog). Never reuse exposed values.
2. From the Supabase dashboard (Project Settings → Database) obtain the
   **current** connection string:
   `postgresql://postgres.zrvrjqwboylvvzusorry@aws-0-<region>.pooler.supabase.com:6543/postgres`
   (transaction pooler; use `?sslmode=require`).
3. Provide it as `DATABASE_URL` + `SECRET_KEY` via a secrets manager.

Steps (each is reversible / additive; nothing touches legacy objects):

```bash
# 1. Read-only inspection (counts only, no PII) — confirm drift expectations
psql "$DATABASE_URL" -c "\dt public"                      # legacy + canonical inventory
psql "$DATABASE_URL" -c "SELECT version_num FROM alembic_version"  # expected: absent or empty

# 2. Apply canonical migrations (0001 -> 0010) as the migration owner
cd backend
ENVIRONMENT=production DATABASE_URL="$DATABASE_URL" SECRET_KEY="$SECRET_KEY" \
  .venv/bin/alembic upgrade head
# Verify: 63 public tables, head 0010, 6 *_owner policies in pg_policies

# 3. Create the least-privilege runtime role (superuser, once)
psql "$DATABASE_URL" -f scripts/db/app_role.sql

# 4. Point the app at the runtime role (NOT the owner)
#    DATABASE_URL=postgresql://asktrabaajo_app:<password>@.../postgres
#    RLS_SESSION_CONTEXT=true

# 5. Smoke: /health, /health/ready, one auth + one Work ID flow, one
#    governance read, one RLS-denied check as the app role
```

Rollback strategy:

- Migration chain: `alembic downgrade -1` drops `0010`'s policies and
  disables RLS (validated). Further downgrades drop only canonical
  objects created by their own revision — never legacy objects.
- Runtime role: `REASSIGN OWNED … ; DROP OWNED BY asktrabaajo_app; DROP
  ROLE asktrabaajo_app;` (documented in the artifact header).
- No backup/restore is claimed: Supabase-managed PITR is assumed for the
  live project but is **unverified** (owner must confirm in dashboard);
  staging restore drills remain a documented requirement.

## Why no new canonical tables in Phase 13

Every Phase 13 requirement maps onto existing tables/columns:
session identity is a connection-level mechanism (no table), RLS is
policies (migration `0010`), the runtime role is instance-level (SQL
artifact). No new table was genuinely required; none was created.
`NEW TABLES: NONE`.