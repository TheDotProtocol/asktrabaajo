"""Schema parity: the ORM model set and the Alembic migration must agree.

Runs ``alembic upgrade head`` against a throwaway sqlite file in a
subprocess (with an isolated env) and compares the resulting table set with
``Base.metadata``. A mismatch fails loudly so models and migrations cannot
drift apart silently.
"""
from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent


def _alembic_tables(tmp_db: Path) -> set:
    env = {
        **os.environ,
        "ENVIRONMENT": "test",
        "DATABASE_URL": f"sqlite:///{tmp_db}",
        "SECRET_KEY": "parity-test-secret",
    }
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=str(BACKEND_DIR),
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    conn = sqlite3.connect(tmp_db)
    try:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
    finally:
        conn.close()
    tables.discard("alembic_version")
    return tables


def test_models_match_migration(tmp_path):
    from app.db.base import Base

    tmp_db = tmp_path / "parity.db"
    migrated = _alembic_tables(tmp_db)
    modeled = set(Base.metadata.tables.keys())

    assert modeled == migrated, (
        "ORM/migration drift:\n"
        f"  in models but not migration: {sorted(modeled - migrated)}\n"
        f"  in migration but not models: {sorted(migrated - modeled)}"
    )
    assert len(modeled) >= 15
