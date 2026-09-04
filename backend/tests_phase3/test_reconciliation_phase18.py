"""Phase 18 — live-reconciliation regression locks (hermetic, SQLite-safe).

These tests lock the database-reconciliation evidence so a future schema
or grant-list change cannot silently reintroduce a collision or a
privilege leak:

1. The ONLY canonical-table-name collision with the live legacy schema
   (the 21 known AskTrabaajo legacy tables) is ``interviews`` — the
   reconciled coexistence strategy depends on that being exactly one.
2. The app-role grant list (scripts/db/app_role.sql) covers exactly the
   canonical migration table set and nothing else.
3. Canonical migrations 0001-0014 are strictly additive: no TRUNCATE,
   no DROP TABLE of another migration's table, no destructive rewrite.

None of these tests touch any database — they parse repository files.
"""
from __future__ import annotations

import re
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
MIGRATIONS = sorted((BACKEND / "alembic" / "versions").glob("00*.py"))

# The 21 live legacy tables discovered in Phase 17/18 read-only inventory.
LEGACY_TABLES = {
    "application_stages", "applications", "candidate_certificates",
    "candidate_resumes", "companies", "company_admins", "company_departments",
    "company_media", "department_catalog", "documents", "interviews",
    "job_offers", "job_templates", "jobs", "notifications", "offices",
    "payments", "profiles", "saved_jobs", "talent_pool", "test_results",
}


def _created_tables() -> set[str]:
    tables: set[str] = set()
    for path in MIGRATIONS:
        text = path.read_text()
        tables.update(re.findall(r'create_table\(\s*"([a-z_0-9]+)"', text))
    return tables


def _app_role_tables() -> set[str]:
    text = (BACKEND.parent / "scripts" / "db" / "app_role.sql").read_text()
    match = re.search(r"IN \(\s*(.*?)\s*\)", text, re.S)
    assert match, "could not locate the canonical table list in app_role.sql"
    return {name.strip().strip("'") for name in match.group(1).split(",") if name.strip()}


def test_legacy_collision_set_is_exactly_interviews():
    collisions = _created_tables() & LEGACY_TABLES
    assert collisions == {"interviews"}, (
        "Canonical/legacy collision set changed; re-run the Phase 18 "
        f"reconciliation analysis before proceeding. Found: {sorted(collisions)}"
    )


def test_app_role_grant_list_matches_canonical_tables():
    canonical = _created_tables()
    granted = _app_role_tables()
    assert canonical == granted, (
        f"app_role.sql drift: in migrations but not granted {sorted(canonical - granted)}; "
        f"granted but not migrations {sorted(granted - canonical)}"
    )
    assert len(granted) == 79, f"expected 79 canonical tables, got {len(granted)}"


def test_canonical_migrations_are_strictly_additive():
    for path in MIGRATIONS:
        text = path.read_text()
        assert "TRUNCATE" not in text.upper(), f"{path.name} contains TRUNCATE"
        assert re.search(r"\bDROP\s+TABLE\b", text, re.I) is None, (
            f"{path.name} contains DROP TABLE (migrations must stay additive)"
        )
