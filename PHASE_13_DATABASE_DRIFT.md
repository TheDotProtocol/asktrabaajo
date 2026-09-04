# PHASE 13 — DATABASE DRIFT

## Method

Three sources were compared:

- **A. Repository migrations** — `backend/alembic/versions/0001…0010`
  (head `0010`; `0001`–`0009` shipped in Phases 3–11, `0010` added in
  Phase 13).
- **B. Legacy schema artifacts** — `supabase-schema.sql`,
  `supabase-careers-schema.sql`, `supabase-careers-ext.sql`,
  `supabase-storage.sql`, seed/update scripts.
- **C. Live Supabase project `zrvrjqwboylvvzusorry`** — **read-only REST
  inspection only** (public anon surface). Direct SQL inspection was
  attempted and is **BLOCKED** (see below).

## Connectivity findings (why live SQL is blocked)

| Probe | Result |
|---|---|
| `db.zrvrjqwboylvvzusorry.supabase.co:5432` (stored `DATABASE_URL`) | DNS NXDOMAIN — legacy direct hostname **retired** by Supabase |
| Pooler `aws-0-{us-east-1,us-west-1,eu-central-1,ap-southeast-1,ap-southeast-2}.pooler.supabase.com:6543` as `postgres.zrvrjqwboylvvzusorry` | `FATAL: tenant/user … not found` — region/tenant unknown; the stored password was never even evaluated |
| REST `https://zrvrjqwboylvvzusorry.supabase.co/rest/v1/` (anon key, read-only) | Reachable; public tables answer |

**Conclusion:** a working SQL credential/endpoint for the live project is
**not available from this environment**. Per the Phase 13 hard-stop rules
("credentials are unavailable… do not guess"), **no live migration was
applied and no live table was modified.** The drift analysis below is
therefore:

- **complete** for A vs B (both fully visible), and
- **partial** for C (public REST surface only); the SQL-side of C is
  marked `REQUIRES LIVE ACCESS` — the exact access required is listed at
  the end.

## A. Repository migrations vs B. legacy schema artifacts

| Object | A (repo migrations) | B (legacy artifacts) | Classification |
|---|---|---|---|
| `users`, `person_profiles`, … all 62 canonical tables | present (0001–0009) | absent | SAFE (canonical-only names) |
| `alembic_version` | created by Alembic | absent from artifacts | SAFE (new) |
| `profiles`, `jobs`, `applications`, `interviews`, `test_results`, `payments`, `notifications`, `documents` | absent | present (core schema) | SAFE (legacy-only names; no canonical collision) |
| `companies`, `offices`, `department_catalog`, `company_departments`, `company_media`, `saved_jobs`, `application_stages`, `candidate_resumes`, `candidate_certificates`, `company_admins`, `job_templates`, `talent_pool` | absent | present (careers) | SAFE |
| `job_offers` | absent | present (ext) | SAFE |
| storage buckets `user-documents`, `kyc-documents`, `kyc-selfies` | n/a | present (storage SQL) | SAFE (storage schema, not touched) |
| `handle_new_user()` trigger / `update_updated_at_column()` / `is_super_admin()` | absent | present | SAFE (legacy functions; canonical replaces them) |
| RLS policies keyed on `auth.uid()` | absent (canonical RLS keys on `app.current_user_id`) | present | SAFE (no policy-name collision: `*_owner`/`*_tenant` vs legacy names) |
| Migration `0010` policies (`career_goals_owner`, …) | present | absent | SAFE (new) |

**No name collisions exist between the canonical schema and the legacy
schema** — this was asserted in Phases 3–11 and re-verified here against
both artifact sets and the canonical `Base.metadata` (62 tables).

## B. Live project (public REST surface, read-only)

| Table | Row count (anon-visible) | Structural status |
|---|---|---|
| `jobs` | 222 | present; public-read policy active (active jobs visible) |
| `companies` | 115 | present; public-read policy active |
| `profiles` | 0 (anon) | present; anon sees no rows (RLS working or empty) |
| `applications` | 0 (anon) | present; anon blocked (RLS) or empty |
| `job_offers` | 0 (anon) | present; anon blocked (RLS) or empty |

Interpretation: the live project carries the **legacy careers corpus**
(≥115 companies, ≥222 jobs). Whether real user data exists in
`profiles`/`applications`/`documents`/`payments` **cannot be determined
from the public surface** — `REQUIRES LIVE ACCESS`.

## C. Live project (SQL side) — classified

| Object | Status |
|---|---|
| `alembic_version` remote | UNKNOWN — REQUIRES LIVE ACCESS |
| Remote canonical tables (0001–0009) | presumed ABSENT (no evidence of prior canonical deployment) — REQUIRES LIVE ACCESS to confirm |
| Remote legacy tables | PRESENT (REST evidence for jobs/companies; others unknown) |
| Remote schema drift vs artifacts (extra tables, modified objects, ad-hoc policies/functions) | UNKNOWN — REQUIRES LIVE ACCESS |
| Remote storage buckets/policies | UNKNOWN — REQUIRES LIVE ACCESS (REST cannot enumerate) |
| Remote extensions/realtime config | UNKNOWN — REQUIRES LIVE ACCESS |

## Classification summary

| Class | Items |
|---|---|
| **SAFE** | All canonical migration objects vs legacy artifacts (zero collisions); migration `0010` policies (new names) |
| **REQUIRES REVIEW** | None identified from available evidence (no conflicts found) |
| **BLOCKED** | Applying migrations to the live project: blocked on live SQL credentials/endpoint (hard-stop) |
| **UNKNOWN** | Full remote schema inventory, remote row counts of private tables, storage/realtime state |

## Exact access required to complete live validation

1. A **current working PostgreSQL connection string** for project
   `zrvrjqwboylvvzusorry`, e.g.
   `postgresql://postgres.zrvrjqwboylvvzusorry@aws-0-<region>.pooler.supabase.com:6543/postgres`
   with the **current** database password (the legacy direct hostname and
   stored credentials are dead). The pooler region can be read from the
   Supabase dashboard (Project Settings → Database).
2. Owner approval to run **read-only** inspection SQL against it
   (schema inventory, `pg_policies`, `pg_namespace`, row counts — counts
   only, never PII).
3. After inspection confirms the drift expectations above, approval to
   apply `alembic upgrade head` (0001→0010) — strictly additive, no
   legacy object touched.

Until then: **MIGRATION DRIFT: REVIEW REQUIRED (live side unverifiable);
no live changes made.**