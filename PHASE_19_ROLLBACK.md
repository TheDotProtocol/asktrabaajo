# Phase 19 — Rollback

## Status

No live change was made, so no rollback is required today. This document defines the rollback contract for when the gated reconciliation runs.

## Database rollback

| Change | Reversal | When safe |
|---|---|---|
| `interviews` → `legacy_asktrabaajo_interviews` rename | `ALTER TABLE legacy_asktrabaajo_interviews RENAME TO interviews;` | **Only before** canonical `interviews` exists (i.e., before/within migration 0003). After 0003 creates the canonical table, **do NOT reverse** — both tables coexist. |
| Canonical schema (0001–0014) | `alembic downgrade base` | Any time; all migrations are additive with downgrades (verified roundtrips on SQLite + PG) |
| App role | `REVOKE` grants, then `DROP ROLE asktrabaajo_app` | Any time; zero legacy grants to clean |
| Legacy data | Never touched by the plan | N/A |

## Application rollback

- Backend/frontend: redeploy the previous release from the repo (runbook item); no schema coupling beyond the canonical tables.
- Configuration: revert `backend/.env` values (single source, gitignored) or the secret manager entries.

## What cannot be reversed

- Nothing in the reconciliation plan — it modifies no legacy rows and creates only new objects plus one rename. A full restore path (if ever needed) depends on the Supabase backup/PITR gate, which is why the gate precedes execution.

## Rollback testing

- Migration downgrades: verified in every prior phase (SQLite + PG roundtrips).
- Rename reversal: trivially tested in the Phase 18 simulation (Experiment 2 repeated cleanly).
- Restore-from-backup: **not tested** — requires operator-confirmed backup/PITR; listed in the launch checklist.