# PHASE 8 — Government data model

Wave 8 adds **no new canonical tables**. Government intelligence is computed live from existing Work ID, skills, jobs, and company tables.

Hosted Supabase is **UNTOUCHED**. No Alembic revision was required. No `supabase db push`.

## Canonical sources

| Source | Use | Never returned |
|---|---|---|
| `person_profiles` | Country / state / city cohort keys | `user_id`, phone, preferred name, raw profile |
| `user_skills` + `skills` | Skill supply | Person-skill rows |
| `work_experiences` | `is_current` employment-record split | Employer names on a person |
| `education` | Education-level distribution | Institution names on a person |
| `job_postings` (published) | Hiring demand, industry, location, work mode | Salary, screening answers, descriptions |
| `company_profiles` | Employer counts by industry / geo | Legal name, contacts, website |
| `organizations` + `memberships` | Government tenancy / RBAC | — |
| `audit_log_entries` | Query / export audit | Cell values |

Employment status is **derived**: people with at least one `WorkExperience.is_current = true` vs those without. There is no official labour-force status field.

Industry values come from existing `JobPosting.industry` / `CompanyProfile.industry` strings. No duplicate industry taxonomy was created.

Skills come from the canonical `Skill` registry (`skills_registry.ensure_skill`). No duplicate skills taxonomy.

## Aggregate queries

All person-facing counts use SQL `COUNT` / `COUNT(DISTINCT)` / `GROUP BY` through SQLAlchemy. The service does not load person rows into Python to count them.

Skill **demand** is open published jobs whose `skills_required` JSON lists the skill, after the same geo/industry job filters.

Skill **gap** is `demand - supply` only when supply is an unsuppressed person cohort. Otherwise the cell is `INSUFFICIENT DATA`.

## Indexes

Wave 8 does not add indexes. Existing primary keys and foreign keys are used:

- `person_profiles.user_id` (unique)
- `user_skills.person_id` / `skill_id`
- `job_postings.organization_id` + status filter
- `company_profiles.organization_id`

Future warehouse work may add `(country_code, state_province, city)` and published-job industry indexes if volume requires it. That is **FUTURE**.

## Privacy application

Person `GROUP BY` results pass `_buckets_from_rows` (k-threshold, hide complementary totals).

Job and company `GROUP BY` results pass `_volume_buckets` (counts allowed; no names).

## Migration strategy

| Step | Status |
|---|---|
| Scratch SQLite schema (`Base.metadata.create_all`) | Used by tests + local bootstrap |
| Alembic upgrade / downgrade | **NOT REQUIRED** — no new revision |
| PostgreSQL schema parity | Unchanged vs Wave 7 head |
| Hosted `supabase db push` | **NOT PERFORMED** |
| `workforce_aggregates` materialized table | **FUTURE** |

## DEV fixtures

`scripts/wave7_local_bootstrap.py` → `seed_wave8_workforce()`:

- AskTrabaajo DEV Company industry `Technology` in Development City
- Extra published job `DEV Python Role` (`skills_required=["Python"]`)
- 11 `dev+gov.wf.NN@example.com` people in Development City with Python + current employment
- 3 `dev+gov.sparse.NN@example.com` people in Sparse Town with `RareSkillDEV` (below K=10)

These are inspectable DEV records, not national statistics.

## Future tables (not created)

A later analytics wave may introduce:

- `workforce_aggregates` (precomputed snapshots)
- `government_disclosure_grants` (person-consented, scoped, expiring Work ID share)
- `government_industry_threads` (authorized org-to-org outreach)

None of these are safe to invent in Wave 8.
