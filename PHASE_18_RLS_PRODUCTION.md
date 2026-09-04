# Phase 18 — RLS Production Readiness

## Current state (two domains)

**Live legacy domain (Supabase project `zrvrjqwboylvvzusorry`):**
- All 21 legacy tables have RLS **enabled** (36 policies). Public-read tables (`companies`, `jobs`, `offices`, `company_departments`, `department_catalog`) expose active rows to unauthenticated REST reads, which is the intended behavior of the public careers site.
- Legacy RLS is untouched by Phase 18. No policy was created, altered, or dropped.

**Canonical domain (80 tables via migrations 0001–0014, local + simulated PG):**
- RLS policies are created inside canonical migrations using **session-identity expressions** — e.g. stage-1 private tables (migration 0010) enforce `owner_id = current_setting('app.current_user_id', true)`, and org-scoped tables use the `app.current_org_ids` session array. Policies are inert unless the app sets the session context.
- The app sets/resets the context on every request via `app/db/session.py` (`set_session_identity` / `reset_session_identity` using session-level `set_config`, not `SET LOCAL`), gated by the `RLS_SESSION_CONTEXT` config flag (which refuses sqlite in staging/production).

## Verification performed

- **RLS suite: 11/11 passing** on scratch PostgreSQL 16 at migration 0014 (owner vs least-privilege role paths; cross-user private reads fail; unauthenticated inserts fail; cross-user mutation fails; DDL by the runtime role fails; session-identity leakage between concurrent sessions fails; the config guard is inert unless enabled).
- **Session identity:** server-side only — set from the authenticated actor, reset on session close and at checkout. Not client-controlled.
- **Least-privilege role:** `asktrabaajo_app` (validated in the reconciled simulation): 316 grants over 79 canonical tables ×4, **zero** grants on legacy tables, no superuser/createdb/createrole, no unrestricted DDL.

## Staged rollout for live

RLS is already *enabled with policies* in canonical migrations — there is no separate "enable later" switch, and the stage-1 policy set (migration 0010) was deliberately designed as the conservative first tier (private per-owner data). Recommended live sequence, after the reconciliation gates pass:

1. Bootstrap canonical schema (migrations 0001–0014) — policies ship with the tables.
2. Create `asktrabaajo_app` + grants (`scripts/db/app_role.sql`).
3. Run canonical app with `RLS_SESSION_CONTEXT=1` connecting as `asktrabaajo_app` only; verify representative cross-tenant probes fail (candidate↔candidate, org↔org, candidate↔employer, platform finance isolation).
4. Verify the legacy REST/public-read domain still functions (careers reads use the `anon`/REST path and legacy policies — unchanged).

## Do-not list

- Do **not** naively re-point legacy tables at canonical owner policies (would break the public careers reads and legacy REST writes).
- Do **not** grant `asktrabaajo_app` anything over legacy tables (keeps the two domains' privilege surfaces disjoint).
- Do **not** run canonical traffic as a superuser-capable role (the pooler `postgres` role bypasses RLS entirely).

## Residual items

- **Session-context concurrency** is covered by the RLS suite (concurrent sessions do not leak identity); a live soak with real pooled traffic is a launch-checklist item.
- Legacy table policies remain operator-owned (Supabase dashboard); a full legacy-policy re-review is listed in `PHASE_18_LAUNCH_CHECKLIST.md`.
