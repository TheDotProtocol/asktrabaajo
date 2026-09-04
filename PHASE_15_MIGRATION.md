# Phase 15 — Migration 0012

One additive, non-destructive migration was required:
`backend/alembic/versions/0012_interview_prep.py`.

## Why a new table

The requirement: a candidate-owned container for interview-preparation flows
with real state (status, expiry, counters, anchors). Existing tables were
checked first:

- `athena_sessions` / `athena_messages` — chat-scoped, governed by Athena
  retention; conflating prep state with chat state would entangle two domains
  and two retention policies.
- `career_goals` / `career_milestones` — goal and milestone state, not a
  per-flow preparation container.
- `interviews` — real employer/candidate interview records; prep practice must
  never write there.
- `applications` — application pipeline records.

No existing table represents "a preparation flow existed, for this focus, with
these counters, expiring at this time". Hence one new table.

## Table: `interview_prep_sessions`

| Column | Type | Notes |
|---|---|---|
| `id` | uuid PK | default uuid4 |
| `person_id` | uuid FK → person_profiles.id | ON DELETE CASCADE, indexed — owner |
| `opportunity_id` | uuid FK → opportunities.id | ON DELETE SET NULL, indexed, nullable anchor |
| `application_id` | uuid FK → job_applications.id | ON DELETE SET NULL, indexed, nullable anchor |
| `interview_id` | uuid FK → interviews.id | ON DELETE SET NULL, indexed, nullable anchor |
| `athena_session_id` | uuid FK → athena_sessions.id | ON DELETE SET NULL, indexed, nullable anchor |
| `status` | varchar(20) | active / completed / expired |
| `focus_areas` | JSON | candidate's bounded, sanitized focus |
| `questions_generated` | int | counter |
| `answers_evaluated` | int | counter |
| `last_activity_at` | timestamptz | server default now() |
| `expires_at` | timestamptz | deterministic lazy expiry |
| `completed_at` | timestamptz | nullable |

Deliberately **not** stored: questions, answers, transcripts (see
PHASE_15_DATA_POLICY.md — narratives are never retained by default).

## Domain / tenancy / RBAC / RLS / audit

- **Domain:** jobseeker career intelligence (preparation).
- **Tenancy:** person-scoped (candidate-owned); no org cross-reads.
- **RBAC:** self-only via service-layer owner checks; jobseeker-only Athena
  tools.
- **RLS:** designed for the future stage-B owner-scoped group (same shape as
  the Phase 13 private-table policies); not enabled in this phase — the
  service-layer owner check is enforced and tested on SQLite and PostgreSQL.
- **Audit:** session/tool/confirmation metadata only, never answer content
  (tested).
- **Retention:** lazy expiry + owner delete; future purge job documented.
- **Indexes:** person_id, each nullable anchor FK, plus PK.

## Constraints & safety

- Additive only: no legacy or canonical object is altered or dropped.
- Deterministic; no idempotency hack needed (plain upgrade).
- Downgrade drops only this table.
- `scripts/db/app_role.sql` updated to the 67-table canonical set (268 DML
  grants verified on scratch PostgreSQL).

## Validation

| Check | Result |
|---|---|
| SQLite upgrade 0011 → 0012 | clean (67 canonical tables) |
| PostgreSQL upgrade 0011 → 0012 | clean (alembic_version 0012; 68 public tables incl. alembic_version) |
| Downgrade 0012 → 0011 → re-upgrade | clean on SQLite **and** PostgreSQL 16 |
| App-role grants after 0012 | 268 = 67 tables × 4 DML |
| Full test suite with 0012 applied | 195 passed / 11 skipped / 0 failed (SQLite); 11/11 RLS on PG |
| PG end-to-end smoke | PASS (session create → questions → answer → complete → delete) |

Migrations 0001–0011 were not modified. No migration was applied to any live
or shared database.
