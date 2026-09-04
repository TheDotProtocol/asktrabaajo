# PHASE 17 — SUPABASE CONNECTION STATUS

> This document describes exactly how the application expects its
> database connection, what was verified, and what the operator must do
> to clear the remaining blocker. **No connection string, password, or
> secret appears anywhere in this document.**

## 1. Project under preservation

- Project ref: `zrvrjqwboylvvzusorry`
- Project URL: `https://zrvrjqwboylvvzusorry.supabase.co`
- The same project must be preserved: no new project, no reset, no
  replacement database, no deletion/truncation of legacy data.

## 2. How the application expects its connection (verified in code)

- `backend/app/core/config.py` → `Settings(BaseSettings)` reads
  environment (and `.env` relative to the process working directory).
- `settings.database_url` is the single connection input
  (`DATABASE_URL` env var). Non-test environments require a PostgreSQL
  URL; the config fails fast otherwise.
- `backend/app/db/session.py` → `create_engine(settings.database_url)`
  directly. The URL scheme selects the driver: `postgresql://…` /
  `postgresql+psycopg2://…` both work; pooler/direct/SSL differences
  are expressed inside the URL (e.g. `?sslmode=require`), so the
  application can consume either a direct Supabase host or the
  Supabase pooler host without code changes.
- The operator-facing secret file is **`backend/.env`** — verified
  gitignored (`.env` and `backend/.env` are both ignored). It holds the
  `DATABASE_URL` for the live project supplied by the operator (value
  never reproduced in documentation).

## 3. What was verified this phase (read-only only)

First connection attempt used the stored (retired) direct hostname
(`db.zrvrjqwboylvvzusorry.supabase.co` → NXDOMAIN, per Phase 13). After
the operator supplied a current pooler connection string into
`backend/.env`, the following read-only checks ran successfully:

| Check | Result |
| --- | --- |
| Code expects `DATABASE_URL` (SQLAlchemy URL) | CONFIRMED |
| Secret location (`backend/.env`, gitignored, untracked) | CONFIRMED |
| Session-pooler connectivity | CONNECTED — Supabase pooler answered on port 5432 |
| PostgreSQL version | 17.6 (Supabase-managed) |
| Database name / user / schema | `postgres` / project postgres role / `public` |
| Server timezone | UTC |
| `alembic_version` present | NO — canonical migrations 0001–0014 have never been applied to the live database |
| Live base tables | 21 — ALL legacy (see inventory below) |
| Legacy jobs / companies present | YES (`jobs`, `companies`, `applications`, `interviews`, `payments`, `profiles`, …) |
| Canonical tables present (`users`, `organizations`, `job_postings`) | NO |
| RLS on legacy tables | 21/21 tables have RLS enabled |
| `asktrabaajo_app` runtime role exists | NO |

Live table inventory (21 legacy tables): `application_stages`,
`applications`, `candidate_certificates`, `candidate_resumes`,
`companies`, `company_admins`, `company_departments`, `company_media`,
`department_catalog`, `documents`, `interviews`, `job_offers`,
`job_templates`, `jobs`, `notifications`, `offices`, `payments`,
`profiles`, `saved_jobs`, `talent_pool`, `test_results`.

### Drift finding — `interviews` table-name collision

Local migration analysis (0001–0014, 79 canonical tables) found that the
canonical schema creates a table named **`interviews`**, and the live
legacy database already contains a populated legacy `interviews` table.
A naive `alembic upgrade` against the live database would therefore
fail (or worse, collide) at that step. **Resolution is a separate,
controlled legacy-data activity** (e.g., a reviewed pre-migration
rename of the legacy table and remapping of its legacy references)
before the canonical migrations may be applied. No such step was
performed in this phase.

## 4. Status summary

- **SUPABASE CONNECTION: CONNECTED** (session pooler, operator-supplied
  string in `backend/.env`).
- **DATABASE IDENTITY: VERIFIED** — host is the `aws-0-ap-northeast-1`
  Supabase pooler and the role authenticates as project
  `zrvrjqwboylvvzusorry`; database `postgres` holds exactly the known
  legacy AskTrabaajo schema.
- **BACKUP / PITR: UNKNOWN** — not verifiable over SQL; the operator
  must confirm backup/PITR in the Supabase dashboard before any live
  migration.
- **LIVE MIGRATION REVISION: NONE** (no `alembic_version`; canonical
  schema never applied).
- **LOCAL MIGRATION REVISION: `0014`** (79 canonical tables; applied to
  scratch PostgreSQL only — see `PHASE_17_MIGRATION.md`).
- **SCHEMA DRIFT: FOUND** — live is legacy-only (21 tables) and cannot
  absorb the canonical migrations without first resolving the
  `interviews` name collision and creating the `asktrabaajo_app` role.
- **LIVE RLS: ENABLED ON LEGACY TABLES** (21/21) — untouched; staged
  canonical RLS follows the Phase 13 matrix after migrations land.
- **APP ROLE:** absent on live; verified on scratch PostgreSQL only
  (79 canonical tables × 4 DML = 316 grants, no DDL/superuser/legacy
  grants).

Because backup/PITR is unverified and the `interviews` collision is
unresolved, **no live migration was applied. Live migration remains
blocked pending operator verification and a controlled legacy
reconciliation step.**

## 5. Operator actions remaining (post-connection)

Step 1-4 (obtain the Session-pooler string and place it in
`backend/.env` under `DATABASE_URL=…`) are COMPLETE. The remaining
operator actions before any live migration are:

1. **Confirm backup/PITR availability** for project
   `zrvrjqwboylvvzusorry` in the Supabase dashboard (Settings →
   Backups / PITR). Without verified backup/PITR the live migration
   stays blocked: "Live migration blocked pending backup/PITR
   verification."
2. **Approve a controlled legacy-reconciliation plan** for the
   `interviews` table-name collision (rename + reference remapping,
   reviewed separately) and the creation of the least-privilege
   `asktrabaajo_app` runtime role. These are deliberate, documented
   steps — never run ad hoc.
3. **Rotate the supplied database password** in the Supabase dashboard
   when the connection is no longer needed, and mirror the new value
   into `backend/.env` (gitignored) — never into git or docs.

## 6. Read-only verification gate (after the string is supplied)

STATUS of the read-only gate (all completed over the live connection):

1. PostgreSQL version/database/user/schema/timezone — DONE (17.6,
   postgres, UTC).
2. `alembic_version` presence and live Alembic history vs local
   `0001…0014` — DONE (no live alembic history; local head `0014`).
3. Live table inventory (legacy + canonical) vs local canonical count
   — DONE (21 legacy tables; local 79 canonical).
4. Database identity == project `zrvrjqwboylvvzusorry` — DONE
   (VERIFIED).
5. Backup/PITR availability — **PENDING (operator dashboard check)**;
   live migration stays blocked until verified.
6. Drift report — DONE (migrations 0001–0014: all `PENDING` on live;
   `interviews` name collision FOUND).
7. App-role state (`asktrabaajo_app`) and grant coverage — DONE
   (role absent on live; grants verified on scratch PG only).
8. Storage buckets + policies (inspect only — no deletion) —
   **PENDING (operator inspection in the dashboard)**.

Only when every gate passes may the Phase-13 migration runbook be
executed, and even then commerce schema deployment waits for the
established baselines (identity → migrations → RLS → app role →
storage) described in the phase brief.
