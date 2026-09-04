# Phase 19 — Database Validation

## Status

**LIVE: READ-ONLY VALIDATED / NOT MUTATED** — pre-migration baseline captured and re-verified; execution skipped per operator decision. Local: full canonical validation on scratch PG 16.

## Pre-migration baseline (live, read-only)

| Legacy table | Rows |
|---|---|
| `company_departments` | 4,896 |
| `jobs` | 222 |
| `companies` | 117 |
| `department_catalog` | 48 |
| `offices` | 10 |
| `profiles` | 1 |
| 15 other legacy tables | 0 each (incl. `interviews` = 0) |

Plus: `alembic_version` absent, `asktrabaajo_app` absent, RLS 21/21, 36 policies, 36 FKs, 53 indexes, 5 triggers, 3 functions, 0 enum types/views/sequences, extensions `pg_stat_statements`/`pgcrypto`/`plpgsql`/`supabase_vault`/`uuid-ossp`.

## Interviews collision facts (re-verified live this phase)

- Rows: **0** · Incoming FKs: **0** · Columns unchanged (13, legacy prototype) · RLS on · 2 policies · 1 trigger.
- The validated rename (`interviews` → `legacy_asktrabaajo_interviews`) remains safe and ready; it was **not executed** (operator decision).

## Post-migration validation plan (for when gates pass)

1. `alembic_version` == `0014`.
2. Public table count == **101** (21 legacy + 80 canonical).
3. Every legacy row count == pre-migration baseline (no unexpected decrease).
4. Canonical FK/index/constraint presence sampled (migrations carry them; suite asserts parity models == migrations).
5. `asktrabaajo_app` exists with **316 grants** (79 × 4), zero legacy grants, no superuser/createdb/createrole.
6. RLS: canonical policies present; spot-check cross-tenant denial with the app role (suite pattern reusable).

## Local validation performed

- Scratch PG 16 at 0014: migration roundtrip + RLS suite 11/11 + staging smoke (`P19_STAGING_SMOKE_PASS`).
- Hermetic locks: `test_reconciliation_phase18.py` + `test_staging_phase19.py` (6 tests) pin the collision set, additive migrations, grant list, and the reconcile script's single-rename safety — all green.