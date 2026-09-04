# Phase 18 — Legacy Compatibility

## What must keep working

- **Legacy backend:** 107 routes (verified unchanged this phase by importing `backend/main.py` and counting path routes).
- **Legacy public careers surfaces:** the careers site reads `companies`, `jobs`, `offices`, `company_departments`, `department_catalog` — these tables are **not** collisions and keep their public-read RLS policies untouched.
- **Canonical platform:** 246 `/api/v1` routes (verified unchanged this phase), 80 canonical tables, RLS, Athena, AI interview, commerce.
- **The 63 carried Phase-1 working-tree entries:** untouched, unstaged by this phase's commits.

## The single collision and its dependency map

### Legacy `interviews`
- **Schema:** `id`, `job_id` (FK → legacy `jobs`), `applicant_id` (FK → legacy `profiles`), `employer_id` (FK → legacy `profiles`), `scheduled_at`, `duration_minutes`, `interview_type`, `status`, `meeting_link`, `notes`, `feedback:jsonb`, `created_at`, `updated_at`. Unique/check constraints exist; RLS: "Employers can manage interviews / Users can view own interviews"; trigger `update_interviews_updated_at`.
- **Rows:** 0. **Incoming FKs:** 0. **Referenced by:** no other legacy table.
- **Legacy code:** `backend/api/routes/interviews.py` (legacy router mounted at `/api/interviews`) — the retired video/facial-analysis interview prototype. Superseded by the canonical AI Interview Engine (Phase 16), which deliberately prohibits the facial-analysis class of feature.
- **Canonical counterpart:** `interviews` created by migration **0003**, model `app/models/career.py::Interview` — an interview record inside the canonical tenancy/RLS/audit model. Structurally unrelated to the legacy table (different columns, FKs, ownership model).

### Other 20 legacy tables
No canonical migration creates a same-named object. Canonical naming avoids the concepts (`payments` legacy vs `payment_transactions` canonical; legacy `documents` vs canonical document tables created under canonical names, etc.). Full diff is locked by `tests_phase3/test_reconciliation_phase18.py::test_legacy_collision_set_is_exactly_interviews`.

## Compatibility strategy

| Concern | Approach | Evidence |
|---|---|---|
| Legacy data | Preserved in place; only the empty `interviews` table is renamed | 0-row table; counts verified read-only |
| Legacy careers public reads | Untouched (no collision) | Inventory + RLS policy review |
| Legacy backend import | Must keep importing at 107 routes | Import + route-count validation run this phase |
| Legacy interviews feature | Retired prototype, superseded by canonical AI interviews; 0 rows | Code analysis of `interviews.py` route + row count |
| Canonical bootstrap | Proceeds after the rename; fully transactional | Simulation Experiment 2 (see reconciliation doc) |
| App role | Grants only the 79 canonical tables; zero legacy grants | Simulation Experiment 3 |

## Compatibility boundary (explicit)

- Legacy tables are **legacy data**, not canonical data. No legacy→canonical data migration is performed or implied by Phase 18.
- Canonical RLS is defense-in-depth over the canonical domain; legacy RLS remains exactly as deployed. A future staged RLS unification (if any) is a separate documented activity.
- `legacy_asktrabaajo_interviews` keeps its RLS and trigger so any hypothetical legacy read path still behaves identically after the rename.
