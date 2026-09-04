"""Phase 19 — staging / live-migration regression locks (hermetic, SQLite-safe).

These tests parse repository artifacts to lock the Phase 19 launch
controls so a future edit cannot silently weaken them:

1. The controlled reconciliation script (scripts/db/reconcile_legacy_interviews.sql)
   contains exactly one table mutation — the validated legacy `interviews`
   rename — and no destructive statements (no DROP/DELETE/TRUNCATE).
2. The script's pre-flight gates require the exact facts Phase 18/19 proved
   (0 rows, 0 incoming FKs) before allowing the rename.
3. Canonical migrations remain strictly additive and the app-role grant list
   still covers exactly the canonical table set (re-locked from the
   reconciliation suite's helpers).
"""
from __future__ import annotations

import re
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
ROOT = BACKEND.parent
RECONCILE = ROOT / "scripts" / "db" / "reconcile_legacy_interviews.sql"

MIGRATIONS = sorted((BACKEND / "alembic" / "versions").glob("00*.py"))


def test_reconcile_script_is_single_rename_only():
    text = RECONCILE.read_text()
    assert "ALTER TABLE public.interviews RENAME TO legacy_asktrabaajo_interviews;" in text
    # scan statements only (strip SQL comments) for destructive keywords
    statements = re.sub(r"--[^\n]*", "", text)
    for forbidden in ("DROP TABLE", "DROP COLUMN", "DELETE FROM", "TRUNCATE"):
        assert forbidden.upper() not in statements.upper(), f"forbidden {forbidden} in reconcile script"
    # only one ALTER TABLE statement (comments excluded)
    assert statements.count("ALTER TABLE") == 1


def test_reconcile_script_keeps_preflight_gates():
    text = RECONCILE.read_text()
    # gates must reference the live-proven facts (0 rows / 0 incoming FKs)
    assert "FROM interviews" in text and "count(*)" in text
    assert "confrelid = 'interviews'::regclass" in text
    assert "legacy_asktrabaajo_interviews" in text


def test_canonical_migrations_additive_and_grant_list_authoritative():
    from test_reconciliation_phase18 import _app_role_tables, _created_tables, MIGRATIONS as M

    assert _app_role_tables() == _created_tables(), "app_role.sql drift from migrations"
    assert len(_created_tables()) == 79
    for path in M:
        text = path.read_text()
        assert "TRUNCATE" not in text.upper()
        assert re.search(r"\bDROP\s+TABLE\b", text, re.I) is None