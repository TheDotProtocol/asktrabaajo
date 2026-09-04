# PHASE 13 — CANONICAL IDENTITY, STAGING DATABASE DEPLOYMENT & PRODUCTION-GRADE DATABASE SECURITY — REPORT

## Objective

Deploy and secure the canonical database architecture on the existing
Supabase project while preserving every legacy object and all legacy
data. Phase 13 was executed conservatively: the live project was
inspected **read-only** where possible, live changes were **blocked by
unavailable credentials** (hard-stop, reported rather than guessed), and
everything deployable was implemented, validated on local PostgreSQL, and
packaged for a documented runbook.

## What was implemented

1. **Live connectivity investigation (read-only).** The stored
   `DATABASE_URL` points at the retired `db.zrvrjqwboylvvzusorry.supabase.co`
   hostname (DNS NXDOMAIN); the pooler tenant `postgres.zrvrjqwboylvvzusorry`
   was not found on five regions; the public REST surface (anon key)
   confirmed the project is alive and carries the legacy careers corpus
   (≥115 companies, ≥222 jobs; `profiles`/`applications`/`job_offers`
   return 0 rows to anon — RLS-blocked or empty). **Direct SQL access:
   unavailable → live migration deployment stopped per hard-stop rules.**
2. **Canonical session-identity mechanism (backend).** `RLS_SESSION_CONTEXT`
   config (fail-fast validation), `set_session_identity`/
   `reset_session_identity` in `app/db/session.py`, wired into
   `get_current_user` (deps) after authentication and reset in
   `get_db().finally` — pool-safe, never client-supplied, inert unless
   explicitly enabled.
3. **Migration `0010` — RLS stage 1.** Idempotent owner-scoped policies
   (`app.current_user_id`) on 6 strictly private tables (career_goals,
   work_dna_profiles, work_dna_answers, career_milestones,
   person_visibility_settings, notification_preferences); no-op on
   SQLite; validated upgrade → downgrade → re-upgrade on PostgreSQL.
4. **Least-privilege runtime role artifact.** `scripts/db/app_role.sql` —
   `asktrabaajo_app` (LOGIN, no superuser/createdb/createrole), DML-only
   grants on the 62 canonical tables, explicit denial of `auth`/`storage`/
   `graphql`/`realtime` schemas, idempotent, verified on scratch PG.
5. **Corrected the Phase 9 RLS artifact** (`app/db/rls.py`) — column
   verification found `talent_pool_members` is person-scoped (indirect
   via `talent_pools`), not org-scoped.
6. **RLS hostile matrix tests (11)** in `tests_phase3/test_rls_phase13.py`
   — green on scratch PostgreSQL with the app role; skip cleanly on
   SQLite.
7. **Seven documents:** DATABASE_DRIFT, RLS_MATRIX, SECURITY_REVIEW,
   STORAGE_SECURITY, MIGRATION_PLAN, FRONTEND_DEPENDENCY_AUDIT, and this
   report.

## What was NOT done (and why)

- **No live migration applied** — no working SQL credential/endpoint
  (hard-stop; exact access required is documented in DATABASE_DRIFT and
  MIGRATION_PLAN).
- **No RLS enabled on the live project** — nothing live was modified.
- **No new canonical tables** — every requirement mapped onto existing
  tables; RLS is policies, the role is instance-level, session identity
  is connection-level. `NEW TABLES: NONE`.
- **No legacy object touched** — no drops, truncates, grants, or policy
  changes to legacy tables/buckets; buckets remain private and untouched.
- **No storage migration, no realtime enablement, no frontend changes.**
- **No Phase 14 work started.**

## Validation results

| Check | Result |
|---|---|
| Canonical suite (SQLite) | **153 passed, 11 skipped** (RLS tests skip without PG env) |
| RLS hostile matrix (local PostgreSQL 16, app role) | **11 passed** — cross-user read/update/delete denied, unauthenticated INSERT blocked (WITH CHECK), unauthenticated reads 0 rows, own-row insert OK, runtime-role DDL denied, legacy-schema privileges zero, concurrent-session identity isolation, config guard |
| Migration 0001→0010 fresh chain (PG) | PASS — 63 tables, head `0010` |
| Migration 0010 roundtrip (PG) | PASS — downgrade drops 6 policies + disables RLS; re-upgrade recreates |
| Migration chain on SQLite | PASS — `0010` no-op; 63 tables, head `0010` |
| Legacy backend import | PASS — 107 routes, untouched |
| Canonical routes | 192 `/api/v1` (unchanged — no new routes) |
| Frontend | Untouched (no Phase 13 changes; prior typecheck/lint/build remain valid) |

---

## FINAL STATUS

```
PHASE 13 STATUS:
PASS WITH LIMITATIONS

SUPABASE PROJECT:
zrvrjqwboylvvzusorry

LIVE DATABASE INSPECTED:
PARTIAL — read-only public REST surface only (jobs=222, companies=115,
profiles/applications/job_offers anon-blocked); SQL-side inspection BLOCKED

LIVE DATABASE MODIFIED:
NO

LEGACY DATA:
PRESERVED — nothing touched, deleted, or truncated; legacy corpus
confirmed present (companies/jobs); private-table contents UNKNOWN

MIGRATION DRIFT:
REVIEW REQUIRED — repo-vs-artifacts: ZERO collisions (SAFE); live SQL
side unverifiable (REQUIRES LIVE ACCESS). No conflicts found in
available evidence; deployment blocked on credentials, not on drift

CANONICAL MIGRATIONS:
0001–0009: VALID on SQLite + local PG
0010 (new): VALID on local PG (roundtrip clean) + SQLite no-op
LIVE: NOT APPLIED (blocked — see BLOCKERS)

DATABASE ROLE:
CONFIGURED (local PG validation; artifact scripts/db/app_role.sql) /
NOT CONFIGURED on live (blocked)

RLS:
NOT ENABLED (live — no live changes)
PARTIALLY ENABLED (local PG: stage A, 6 owner-private tables, migration
0010; stages B/C designed in PHASE_13_RLS_MATRIX.md)

STORAGE:
SECURE BY DESIGN / LIVE NOT INSPECTED (buckets untouched, private;
canonical storage provider-neutral, not wired; kyc-selfies deprecated
for new writes)

IDENTITY:
PASS — canonical ACCOUNT → USER → PERSON PROFILE → WORK ID → CREDENTIALS
→ MEMBERSHIPS → RBAC chain intact; legacy `profiles.is_super_admin` and
`auth.uid()` remain legacy-only; session identity set server-side per
request (never client-supplied), pool-safe

TENANT ISOLATION:
PASS — existing app-level hostile tests green; database-level isolation
proven on scratch PG (RLS matrix); live DB-level isolation pending live
deployment

SECURITY:
PASS WITH LIMITATIONS — RLS stage 1 + least-privilege role proven at DB
layer; limitations: staged B/C groups, live credentials, secret
rotation backlog (all documented, none hidden)

NEW TABLES:
NONE

NEW MIGRATIONS:
0010_rls_stage1_private — enables owner-scoped RLS on 6 strictly private
tables (idempotent, reversible, no-op on SQLite)

TESTS:
164 PASSED (153 canonical + 11 RLS/PG)
0 FAILED
0 BLOCKED

PRODUCTION READINESS:
STAGING-CANDIDATE — canonical app + migrations + RLS stage 1 + app-role
design validated on local PostgreSQL; NOT deployed anywhere live; live
deployment + RLS stages B/C + secret rotation remain owner/deployment
actions

BLOCKERS:
1. No working live SQL credential/endpoint: stored direct hostname is
   retired (NXDOMAIN); pooler tenant not found on probed regions.
   Required: current pooler connection string + password from the
   Supabase dashboard (owner action).
2. Secret rotation backlog (Phase 1 carry): anon/service-role keys, DB
   password, SMTP, OpenAI, JWT secret, crypto wallets.
3. Live storage/realtime/extensions state unverifiable without SQL
   access.

OWNER ACTIONS:
1. Rotate all known-exposed credentials.
2. Provide the current pooler connection string (region + password) for
   project zrvrjqwboylvvzusorry, or grant approved read-only access.
3. Confirm Supabase-managed backup/PITR status in the dashboard.
4. Approve the live-deployment runbook (PHASE_13_MIGRATION_PLAN.md):
   alembic upgrade head → app_role.sql → app on asktrabaajo_app with
   RLS_SESSION_CONTEXT=true → staged RLS groups B/C.

PHASE 14 RECOMMENDATION:
1. Execute the Phase 13 runbook once credentials exist: deploy
   migrations 0001–0010 to the live project, create the runtime role,
   switch the app to it, enable RLS_SESSION_CONTEXT, and smoke-test
   auth/Work ID/governance as the least-privilege role.
2. Then the RLS stage-B group (two-party: outreach/conversations/
   documents/grants/applications + the elevated-writer mechanism for
   tokens/notifications) and stage-C (platform-role `app.current_roles`
   GUC for governance/enforcement/appeals/memberships).
3. Then the canonical document-storage workstream (provider-neutral
   upload/download with consent+grants+audit) and the frontend cutover
   order defined in PHASE_13_FRONTEND_DEPENDENCY_AUDIT.md.
4. Realtime transport and Athena remain behind the governance and
   deployed-infrastructure layers.
```