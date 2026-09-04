-- Phase 19 — Controlled legacy/canonical reconciliation (project zrvrjqwboylvvzusorry)
--
-- PURPOSE
--   The ONLY canonical/legacy table-name collision is `interviews` (validated in
--   Phase 18 and re-verified live in Phase 19): the legacy table is EMPTY (0 rows),
--   has 0 incoming foreign keys, belongs to the retired legacy interview
--   prototype, and is structurally unrelated to the canonical `interviews`
--   table created by migration 0003.
--
-- GATES (must ALL hold before running)
--   1. Backup/PITR confirmed by the operator from the Supabase dashboard.
--   2. Operator explicitly approves executing this script.
--   3. Verification queries below still show: interviews rows = 0 and
--      incoming FKs = 0. If either changed, STOP — do not run.
--
-- EXECUTION
--   Run this script as the project owner/pooler role BEFORE `alembic upgrade head`.
--   It performs ONE rename and nothing else: no DROP, no DELETE, no TRUNCATE,
--   no row movement, no changes to any other legacy table.
--
-- REVERSIBILITY
--   Before the canonical `interviews` table exists, the rename is instantly
--   reversible: ALTER TABLE legacy_asktrabaajo_interviews RENAME TO interviews;
--   AFTER migration 0003 creates the canonical table, do NOT reverse it.

-- ---------------------------------------------------------------------------
-- STEP 0 — Pre-flight verification (read-only; must print the expected values)
-- ---------------------------------------------------------------------------
SELECT 'interviews_rows' AS check_name, count(*) AS value FROM interviews;
SELECT 'incoming_fks' AS check_name, count(*) AS value
  FROM pg_constraint WHERE contype = 'f' AND confrelid = 'interviews'::regclass;
SELECT 'alembic_version_present' AS check_name,
       (to_regclass('public.alembic_version') IS NOT NULL) AS value;
SELECT 'app_role_exists' AS check_name,
       (to_regrole('asktrabaajo_app') IS NOT NULL) AS value;

-- ---------------------------------------------------------------------------
-- STEP 1 — The single reconciliation statement (validated in simulation)
-- ---------------------------------------------------------------------------
ALTER TABLE public.interviews RENAME TO legacy_asktrabaajo_interviews;

-- ---------------------------------------------------------------------------
-- STEP 2 — Post-rename verification
-- ---------------------------------------------------------------------------
SELECT 'legacy_table_present' AS check_name,
       (to_regclass('public.legacy_asktrabaajo_interviews') IS NOT NULL) AS value;
SELECT 'canonical_name_free' AS check_name,
       (to_regclass('public.interviews') IS NULL) AS value;
SELECT 'legacy_rows_preserved' AS check_name, count(*) AS value
  FROM legacy_asktrabaajo_interviews;

-- After this script, run:
--   alembic upgrade head        (from backend/, using the project DATABASE_URL)
--   psql ... -f scripts/db/app_role.sql   (create asktrabaajo_app + 316 grants)