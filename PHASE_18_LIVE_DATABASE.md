# Phase 18 — Live Database Baseline

Status: **READ-ONLY BASELINE COMPLETE — LIVE WRITES NOT PERFORMED**

## Connection facts

- **File:** `backend/.env` (gitignored, untracked, never committed). The operator supplied the connection string there in Phase 17; this document intentionally contains no secret material.
- **Endpoint type:** Supabase **Session Pooler** (port 5432).
- **Project ref:** `zrvrjqwboylvvzusorry` — identity **VERIFIED** (authentication happens against the project's own pooler; the reported project is the one the operator controls).
- **PostgreSQL version:** 17.6 (Supabase-managed).
- **Database:** `postgres` | **Schema:** `public` | **Timezone:** UTC.
- **Connection user:** the project's `postgres` role via the pooler. Note: this role has elevated (superuser-capable) privileges — all Phase 18 access was strictly read-only.

## Live migration history

- `alembic_version` table: **ABSENT**.
- Consequence: canonical migrations 0001–0014 have **never been applied** to this database. This is an empty-migration-history live DB with a populated legacy schema — it cannot be treated as a blank database, and a `stamp` must never be used as a shortcut.

## Table state (public schema)

| Measurement | Live value |
|---|---|
| Public tables | 21 (all legacy AskTrabaajo / Careers-era) |
| Canonical tables | 0 |
| Views | 0 |
| Sequences | 0 |
| User-defined enum types | 0 |
| Indexes | 53 |
| Foreign keys | 36 (outgoing), 0 referencing the colliding `interviews` table |
| Unique constraints | 8 |
| Check constraints | 14 |
| Triggers | 5 (all `update_*_updated_at`) |
| Functions | 3 (`handle_new_user`, `is_super_admin`, `update_updated_at_column`) |
| RLS | Enabled on all 21 tables |
| RLS policies | 36 |
| Extensions | `pg_stat_statements`, `pgcrypto`, `plpgsql`, `supabase_vault`, `uuid-ossp` |

## Row counts (real `COUNT(*)`, read-only)

Populated legacy tables:

| Table | Rows |
|---|---|
| `company_departments` | 4,896 |
| `jobs` | 222 |
| `companies` | 117 |
| `department_catalog` | 48 |
| `offices` | 10 |
| `profiles` | 1 |

All remaining 15 legacy tables (`application_stages`, `applications`, `candidate_certificates`, `candidate_resumes`, `company_admins`, `company_media`, `documents`, `interviews`, `job_offers`, `job_templates`, `notifications`, `payments`, `saved_jobs`, `talent_pool`, `test_results`) contain **0 rows**.

## Application role

- `asktrabaajo_app` role: **DOES NOT EXIST** on live. Creation + least-privilege grants (79 canonical tables × 4 privileges = 316 grants) is part of the reconciliation plan (validated in simulation; see `PHASE_18_DATABASE_RECONCILIATION.md`).

## Storage (read-only)

Supabase Storage contains 3 buckets, **all private** (`public = false`): `kyc-documents`, `kyc-selfies`, `user-documents`. No public bucket was found. Per-object policies were not enumerable from this connection; verifying storage policies from the dashboard is a launch-checklist item.

## Full inventory

The complete per-table inventory (columns, types, PKs, FKs, unique indexes, RLS policy names, row counts) is in **`PHASE_18_LIVE_SCHEMA_INVENTORY.md`**.

## Identity confirmation summary

All identity checks pass: project ref matches the operator's project, PostgreSQL is Supabase-managed 17.6, schema `public`, timezone UTC, database `postgres`. There is no evidence the connection points at any other environment.
