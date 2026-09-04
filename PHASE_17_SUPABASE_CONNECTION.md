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
  gitignored (`.env` and `backend/.env` are both ignored). It currently
  contains only a `DATABASE_URL` line whose hostname is the retired
  direct database host for this project.

## 3. What was verified this phase (read-only only)

| Check | Result |
| --- | --- |
| Code expects `DATABASE_URL` (SQLAlchemy URL) | CONFIRMED |
| Secret location (`backend/.env`, gitignored) | CONFIRMED |
| Read-only connection attempt with the stored `DATABASE_URL` | BLOCKED — the stored hostname (`db.zrvrjqwboylvvzusorry.supabase.co`) no longer resolves (NXDOMAIN), consistent with the Phase 13 finding that the direct host was retired |
| Project host liveness (public REST, read-only) | HOST ALIVE — `zrvrjqwboylvvzusorry.supabase.co` answers |
| Stored anon key | STALE — REST returns 401 (key has been rotated since it was recorded) |
| Region/host guessing (pooler regions, alternate hosts) | NOT ATTEMPTED — explicitly forbidden by phase policy |

## 4. Status summary

- **SUPABASE CONNECTION: BLOCKED** — no current, valid PostgreSQL
  connection string is available to the repository.
- **DATABASE IDENTITY: BLOCKED** (cannot be verified without a
  connection).
- **BACKUP / PITR: UNKNOWN** (cannot be verified without a connection;
  nothing is assumed).
- **LIVE MIGRATION REVISION: UNKNOWN** (not connected).
- **LOCAL MIGRATION REVISION: `0014`** (applied to scratch PostgreSQL
  only; see `PHASE_17_MIGRATION.md`).
- **SCHEMA DRIFT: UNKNOWN** (not connected).
- **LIVE RLS: UNKNOWN** (never enabled blindly; Phase 13 staged-RLS
  matrix governs any future rollout).
- **APP ROLE:** verified on scratch PostgreSQL only — 79 canonical
  tables × 4 DML = 316 grants, no DDL/superuser/legacy grants.

Because identity, backup/PITR, and migration history cannot be
verified, **no live migration was applied and none will be attempted
until a valid connection exists and the verification gates below pass.**

## 5. Operator action required (clears the blocker)

1. Open the Supabase dashboard for project `zrvrjqwboylvvzusorry`
   (Project Settings → Database → Connection string).
2. Copy the **PostgreSQL connection string** that the architecture
   supports — direct connection if the dashboard offers one, otherwise
   the **pooler** connection for the same project (prefer session
   pooling for SQLAlchemy/Alembic). Do not invent a host or region —
   copy exactly what the dashboard shows.
3. Paste it into the gitignored file:
   ```
   backend/.env
   ```
   as:
   ```
   DATABASE_URL=<PASTE_CONNECTION_STRING_HERE>
   ```
   The value is read by `backend/app/core/config.py` and consumed by
   SQLAlchemy/Alembic unchanged (add `?sslmode=require` if the URL has
   no SSL parameter and the connection requires it).
4. Do NOT commit the file, print the value, or paste it into a
   document or chat prompt.

## 6. Read-only verification gate (after the string is supplied)

Before ANY live migration, run only read-only statements and confirm:

1. PostgreSQL version, database name, current user, schema, timezone.
2. `alembic_version` presence and live Alembic history vs local
   `0001…0014`.
3. Live table inventory (legacy + canonical) vs local canonical count.
4. Database identity == project `zrvrjqwboylvvzusorry` (else STOP).
5. Backup/PITR availability on the Supabase project (else STOP:
   "Live migration blocked pending backup/PITR verification.").
6. Drift report: Migration | Local | Live | Status for 0001–0014.
7. App-role state (`asktrabaajo_app`) and grant coverage.
8. Storage buckets + policies (inspect only — no deletion).

Only when every gate passes may the Phase-13 migration runbook be
executed, and even then commerce schema deployment waits for the
established baselines (identity → migrations → RLS → app role →
storage) described in the phase brief.
