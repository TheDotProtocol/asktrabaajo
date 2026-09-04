# Wave 2 — Development database classification

**Date:** 2026-09-05  
**Decision:** Isolated canonical sqlite for Wave 2 validation. **Hosted Supabase project `zrvrjqwboylvvzusorry` was not migrated, reset, or written to.**

This report exists because Wave 2 authorized a development-database rebuild *if required*, after classify-first. Production remains untouched.

---

## 1. What exists

| Surface | State |
|---|---|
| Canonical schema (code) | Alembic `0001`–`0014`, **80** tables, UUID PKs, RLS in `0010+` |
| Canonical tests | `backend/tests_phase3` forces `ENVIRONMENT=test` + in-memory sqlite **before** app import |
| Hosted PostgreSQL | Same project id as prior sprints. Owner states it is **pre-launch / no real users** |
| `backend/.env` | Points at that hosted project. **Not used** by Wave 2 tests or this classification run |
| Legacy SQL dumps | `supabase-careers-schema.sql`, `scripts/seed-*.sql` — Careers-era, not canonical |

## 2. Canonical tables (authoritative)

Identity spine and Employment OS as defined in `backend/app/models/` and migrations `0001`–`0014`:

- `users`, `refresh_tokens`, `person_profiles`, memberships, organizations, RBAC catalog
- Work ID: experiences, educations, skills, credentials, employments, consents, privacy
- Documents + grants + document requests
- Career OS: goals, milestones, work DNA, opportunities, applications, interviews, offers
- Talent / communications / notifications / events
- Athena, interview-prep, AI interviews, commerce, governance

These are the only tables the Candidate OS may use.

## 3. Legacy tables (do not resurrect)

Hosted `public` still carries Careers-era artifacts from the last sprint (order-of-magnitude **21** tables historically counted): `profiles`, `companies`, `jobs`, `payments`, `interviews` (legacy shape), and related objects that assume Supabase Auth / `auth.uid()`.

**Not** the identity spine. **Not** to be wired into Wave 2 UI.

## 4. Useful seed / reference data

- Skills taxonomy and catalog seeds inside `seed_catalog` / commerce plan seeds (code-level, deterministic)
- Legacy Careers SQL seeds (`scripts/seed-careers-platform.sql`) — **reference only** for the legacy site
- No real candidate, employer, payment, Work ID, or application history to preserve

## 5. Obsolete development artifacts

- Sprint demo rows that look like real customers
- Legacy unrestricted document access models
- `is_super_admin` / `profiles` as identity
- Facial-analysis interview tables from the legacy backend

## 6. Genuinely valuable data

**None that must be preserved.** Owner confirmed: no real users, no real payments, no real Work IDs.

What *is* valuable is the **canonical migration history** (`0001`–`0014`) and the test harness that rebuilds it.

## 7. Migration state

- Repo head: Alembic `0014`
- Hosted project: **not reconciled** in this wave (still the previous live-reconciliation plan)
- Isolated tests: `Base.metadata.create_all` + catalog seed (equivalent schema for sqlite)

## 8. Foreign keys / RLS

- Canonical FKs are UUID → User / Person / Organization
- RLS policies exist in migrations `0010+` and are exercised by PostgreSQL-specific tests when a scratch Postgres is provided
- Sqlite tests enable `PRAGMA foreign_keys=ON`

## 9. What will be removed / rebuilt / remain

| Action | Target | Why |
|---|---|---|
| **Not executed** | Hosted Supabase schema | `.env` still points at the shared project. Rebuilding it from this machine would be a live write. Wave 2 does not need that write. |
| **Remain** | Hosted project as-is | Operator can later run the Phase 19 reconciliation plan when they want a hosted canonical DB |
| **Used** | Isolated sqlite (`scripts/wave2_candidate_e2e.py`) | Clean canonical schema + clearly marked `dev+…@asktrabaajo.local` users |
| **Remain** | Alembic `0001`–`0014` unmodified | Architecture is already correct |

## 10. Why this is the cleanest safe approach

A full hosted rebuild *is* authorized, but it is **not required** to make the Candidate OS work:

- The canonical API already creates the schema in test/dev sqlite
- Wave 2 is a frontend client of `/api/v1`
- Pointing Alembic at `backend/.env` would mutate the hosted project from the developer laptop
- Isolated sqlite proves register → Work ID → apply → advisor without touching hosted data

If a later wave needs a **local Postgres** scratch database:

1. Create a *new* local Postgres (not the hosted pooler URL)
2. `alembic upgrade head`
3. Seed only `dev+…@asktrabaajo.local` fixtures
4. Never use the hosted project URL for that rebuild

## 11. Validation

- `scripts/wave2_candidate_e2e.py` — isolated sqlite Candidate journey + cross-user denial
- `backend/tests_phase3` — existing ownership, disclosure, application, interview, AI interview suites
- Hosted project: **untouched**
