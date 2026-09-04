# Phase 18 — Database Reconciliation

## Objective

Answer with evidence: *can the real AskTrabaajo Supabase database and the canonical platform coexist safely and move toward production without legacy data loss or security weakening?*

**Answer: YES — via a rename-and-bootstrap strategy that was validated end-to-end in a local simulation of the exact live starting state. Live execution remains gated on operator confirmation of Backup/PITR (see §Gates).**

## Methodology

1. **Read-only live inventory** — complete metadata inventory of the live `public` schema (see `PHASE_18_LIVE_SCHEMA_INVENTORY.md`).
2. **Proper collision analysis** — parse all 14 canonical migrations (`alembic/versions/0001…0014`) for created tables, then diff against the 21 live legacy table names. Locked by a hermetic regression test (`tests_phase3/test_reconciliation_phase18.py`).
3. **Dependency analysis** — legacy + canonical code references for every colliding object.
4. **Local simulation** — recreate the exact live starting state (legacy schema, RLS, policies, triggers) on scratch PostgreSQL 16, then run the candidate strategies against it.
5. **Dry-run report** (§Dry-run) — object-level actions, reasons, data impact, reversibility, risk. No live mutation yet.

## Collision inventory

| Live table | Canonical migration | Rows | Domain classification | Strategy |
|---|---|---|---|---|
| `interviews` | 0003 (`app/models/career.py`, canonical `Interview`) | 0 | **Different domain.** Legacy: scheduling/meeting-link record for the retired legacy video/facial-analysis prototype (FKs → legacy `jobs`/`profiles`, CHECK constraints, trigger). Canonical: interview record under canonical tenancy/RLS. | Rename → `legacy_asktrabaajo_interviews`, then let 0003 create the canonical table. |
| All other 20 legacy tables | — | see inventory | No canonical table shares any of these names. | **No action.** Preserve untouched. |

Facts that make the reconciliation safe:

- **No incoming FKs** reference legacy `interviews` (0 constraints point at it), so renaming it breaks nothing structurally.
- **It is empty (0 rows)** — there is zero data-loss exposure.
- The legacy public surfaces (`companies`, `jobs`, `offices`, `company_departments`, `department_catalog` — careers site reads) are **not** collisions and keep their public-read RLS policies.
- Canonical migrations create **no** table named like any other live legacy table (`payments` in legacy vs canonical `payment_transactions`, etc.).
- Canonical migrations create **0** enum types, **0** views, **0** sequences, **0** standalone functions in `public` — no object-class collisions beyond the single table.

## Local simulation (scratch PostgreSQL 16, DB `p18_test`)

The live legacy schema was replicated faithfully on scratch PG from live metadata: 21 tables, 33–36 policies, 21 RLS enables, 5 triggers, 3 functions, all constraints and indexes — generated programmatically from live catalog queries (no row contents).

### Experiment 1 — naive `alembic upgrade head` (reproduce the failure)
Result: migrations 0001→0002 apply, then **0003 fails** with `relation "interviews" already exists`. The failed run rolls back completely; the legacy schema was verified unchanged afterward (`alembic_version` absent, 21 legacy tables intact, RLS/policies preserved). This confirms a naive upgrade is **safe but non-terminating** — it cannot damage legacy data, it simply cannot proceed.

### Experiment 2 — minimal reconciliation then full bootstrap
1. `ALTER TABLE public.interviews RENAME TO legacy_asktrabaajo_interviews;` (single statement, instant, no data movement).
2. `alembic upgrade head` — **all 14 migrations apply cleanly**.
3. Final state: `alembic_version = 0014`, **101 tables** in `public` = 21 legacy + 80 canonical. Revision confirmed by query.
4. Both domains verified coexisting: legacy tables, policies, triggers, and row counts intact; canonical tables present with their indexes and constraints.

### Experiment 3 — app role on the reconciled sim
`scripts/db/app_role.sql` applied to the reconciled simulation:
- **316 grants** = 79 canonical tables × 4 (`SELECT/INSERT/UPDATE/DELETE`), `alembic_version` excluded.
- **Zero grants** on any of the 21 legacy tables.
- Role has **no superuser**, **no createdb/createrole**, no unrestricted DDL.
- Least privilege confirmed by query (table-privilege audit + role attributes).

## Reconciliation strategy (validated)

```
LIVE (Supabase, project zrvrjqwboylvvzusorry)
  1. READ-ONLY gates pass (identity ✓, inventory ✓, PITR — operator)
  2. Single safe statement:
       ALTER TABLE public.interviews RENAME TO legacy_asktrabaajo_interviews;
     - preserves all rows (0), columns, constraints, indexes, RLS, policies, trigger
     - legacy interviews feature is retired; nothing references this table
  3. alembic upgrade head            (transactional; verified additive 0001-0014)
  4. Create app role + grants:       scripts/db/app_role.sql  (316 grants, canonical only)
  5. Verify: revision 0014; 101 tables; legacy counts unchanged; canonical constraints
     valid; role has no elevated attributes
```

Notes:

- **Why rename and not drop/move:** the phase forbids dropping and forbids choosing a schema move before dependency analysis. The rename is the smallest reversible step that preserves the object completely. It also keeps PostgREST behavior intact for every other table.
- **Why not `CREATE TABLE` over it / `DROP`:** destructive, unnecessary, and explicitly forbidden.
- **Why not a compatibility view named `interviews`:** PostgreSQL refuses to create a table when a same-name relation exists in the schema, so a view would not make room — and nothing needs the legacy table under its old name (empty, no incoming FKs, feature retired).
- **Alternative (not required):** moving the table to a `legacy_asktrabaajo` schema with `search_path` handling is possible but adds moving parts for zero benefit today (no public exposure of `interviews`, no anon read policy). Recorded for future consideration.
- **Legacy data migration:** none is performed. Legacy rows stay in their own tables as legacy data. If a controlled legacy→canonical data migration is ever required (e.g. careers `jobs` → canonical job postings), it must be its own documented, field-mapped, reversible activity — not part of this phase.

## Dry-run report (live, NOT executed)

| Object | Action | Why | Data impact | Reversible? | Risk |
|---|---|---|---|---|---|
| `public.interviews` | `RENAME TO legacy_asktrabaajo_interviews` | Free the canonical table name | None (0 rows); constraints/policies/triggers move with the table | Yes — instant reverse rename | Low; nothing references the old name |
| `alembic_version` | created by alembic | Canonical migration history | New table only | Yes (drop row + table if needed) | Low |
| 80 canonical tables | `CREATE TABLE` via migrations 0001–0014 | Canonical platform bootstrap | New objects only | Yes — `alembic downgrade base` (each migration has downgrade; all strictly additive) | Medium — mitigated by simulation + roundtrip tests |
| `asktrabaajo_app` role | `CREATE ROLE` + 316 grants | Least-privilege app identity | New role only | Yes — `DROP ROLE` (after revoke) | Low |

**No TRUNCATE, no DELETE, no DROP of any legacy object, no data transformation, no legacy RLS change, no storage change** is part of the plan.

## Gates

Live execution of the plan above is **BLOCKED** until both:

1. **Backup/PITR confirmed** — operator must verify Supabase dashboard → Project Settings → Backups / PITR (scheduled backups and/or point-in-time recovery enabled) for project `zrvrjqwboylvvzusorry`. SQL cannot establish this; it is a project-level setting.
2. **Operator go-ahead** — the operator explicitly approves running step 1–5 above (all reversible, but it is the first live write since the project was created).

Every hard-stop condition in the phase brief was checked: identity verified, no unknown collisions, migration is non-destructive (Experiment 1 proved failure rolls back cleanly), legacy dependencies understood, RLS/app-role strategy verified in simulation, no credential exposure, no real-money path, no stamping.

## Rollback plan

| Change | Reverse |
|---|---|
| Renamed table | `ALTER TABLE legacy_asktrabaajo_interviews RENAME TO interviews;` (instant) |
| Canonical schema | `alembic downgrade base` (all 0014→0001 migrations are additive with downgrades; verified by SQLite + PG roundtrips in every prior phase) |
| App role | Revoke grants, then `DROP ROLE asktrabaajo_app` |

What cannot be reversed without restore: none in this plan — no legacy data is modified, transformed, or deleted. If a full restore were ever needed, Supabase Restore relies on backup/PITR (gate #1), which is why that gate precedes execution.
