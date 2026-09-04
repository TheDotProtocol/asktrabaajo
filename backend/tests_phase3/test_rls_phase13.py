"""Phase 13 — PostgreSQL RLS + session-identity security tests.

These tests run ONLY against a scratch/local PostgreSQL where migrations
0001-0010 have been applied and the least-privilege ``asktrabaajo_app``
role exists (see scripts/db/app_role.sql). They are skipped in the
default SQLite suite (conftest forces sqlite) unless:

    TEST_PG_URL=postgresql://asktrabaajo_app:...@127.0.0.1:5432/<scratch>
    TEST_PG_OWNER_URL=postgresql://<owner>@127.0.0.1:5432/<scratch>

Hostile paths are tested directly at the database layer: cross-user
private data, unauthenticated inserts, cross-user mutation, DDL by the
runtime role, session-identity leakage between concurrent sessions, and
the config guard that keeps the mechanism inert unless explicitly enabled.
"""
from __future__ import annotations

import os
import uuid

import pytest
from sqlalchemy import create_engine, text

APP_URL = os.environ.get("TEST_PG_URL")
OWNER_URL = os.environ.get("TEST_PG_OWNER_URL")

pytestmark = pytest.mark.skipif(
    not (APP_URL and OWNER_URL),
    reason="requires TEST_PG_URL (app role) + TEST_PG_OWNER_URL (owner) on scratch PG",
)

from app.db import session as db_session_module  # noqa: E402
from app.db.session import reset_session_identity, set_session_identity  # noqa: E402

PRIVATE_TABLES = [
    "career_goals",
    "work_dna_profiles",
    "work_dna_answers",
    "career_milestones",
    "person_visibility_settings",
    "notification_preferences",
]


@pytest.fixture()
def owner_engine():
    eng = create_engine(OWNER_URL, future=True)
    yield eng
    eng.dispose()


@pytest.fixture()
def app_engine():
    eng = create_engine(APP_URL, future=True)
    yield eng
    eng.dispose()


@pytest.fixture()
def persons(owner_engine):
    """Two users + person profiles + one career_goal each (owner inserts)."""
    u1, u2 = uuid.uuid4(), uuid.uuid4()
    p1, p2 = uuid.uuid4(), uuid.uuid4()
    g1, g2 = uuid.uuid4(), uuid.uuid4()
    with owner_engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO users (id, email, password_hash, full_name, status, token_version) "
                "VALUES (:i1,:e1,'x','User One','active',0),(:i2,:e2,'x','User Two','active',0)"
            ),
            {"i1": u1, "e1": f"{u1}@test.local", "i2": u2, "e2": f"{u2}@test.local"},
        )
        conn.execute(
            text("INSERT INTO person_profiles (id, user_id) VALUES (:p1,:u1),(:p2,:u2)"),
            {"p1": p1, "u1": u1, "p2": p2, "u2": u2},
        )
        conn.execute(
            text(
                "INSERT INTO career_goals (id, person_id, title, target_role, status) "
                "VALUES (:g1,:p1,'Goal A','Role A','active'),(:g2,:p2,'Goal B','Role B','active')"
            ),
            {"g1": g1, "p1": p1, "g2": g2, "p2": p2},
        )
    return {"u1": u1, "u2": u2, "p1": p1, "p2": p2, "g1": g1, "g2": g2}


@pytest.fixture()
def rls_ctx(monkeypatch):
    """Enable the session-identity mechanism for the duration of a test."""
    monkeypatch.setattr(db_session_module.settings, "rls_session_context", True)


def _as_user(app_engine, user_id, org_ids=None):
    """Context manager: session stamped with the given actor identity."""
    from contextlib import contextmanager

    @contextmanager
    def _cm():
        with app_engine.connect() as conn:
            set_session_identity(conn, user_id, org_ids)
            yield conn
            reset_session_identity(conn)
            conn.execute(text("COMMIT"))

    return _cm()


def _count(conn, table):
    return conn.execute(text(f"SELECT count(*) FROM {table}")).scalar()


# --------------------------------------------------------------------------
# Session identity: set / reset / concurrent isolation / config guard
# --------------------------------------------------------------------------

def test_session_identity_set_reset_and_concurrent_isolation(app_engine, rls_ctx):
    a, b = uuid.uuid4(), uuid.uuid4()
    with app_engine.connect() as ca, app_engine.connect() as cb:
        set_session_identity(ca, a, [uuid.uuid4(), uuid.uuid4()])
        set_session_identity(cb, b)
        got_a = ca.execute(
            text("SELECT current_setting('app.current_user_id', true)")
        ).scalar()
        got_b = cb.execute(
            text("SELECT current_setting('app.current_user_id', true)")
        ).scalar()
        assert got_a == str(a)
        assert got_b == str(b)
        # No cross-session contamination while both are open.
        assert got_a != got_b
        orgs_a = ca.execute(
            text("SELECT current_setting('app.current_org_ids', true)")
        ).scalar()
        assert orgs_a.count(",") == 1
        # Reset only session A; B must keep its identity.
        reset_session_identity(ca)
        assert ca.execute(
            text("SELECT current_setting('app.current_user_id', true)")
        ).scalar() == ""
        assert cb.execute(
            text("SELECT current_setting('app.current_user_id', true)")
        ).scalar() == str(b)
        ca.execute(text("COMMIT"))
        cb.execute(text("COMMIT"))


def test_session_identity_inert_without_config(app_engine):
    """The guard keeps the mechanism off unless RLS_SESSION_CONTEXT is on."""
    with app_engine.connect() as conn:
        before = conn.execute(
            text("SELECT current_setting('app.current_user_id', true)")
        ).scalar()
        set_session_identity(conn, uuid.uuid4(), [uuid.uuid4()])
        after = conn.execute(
            text("SELECT current_setting('app.current_user_id', true)")
        ).scalar()
        assert before is None and after is None
        conn.execute(text("COMMIT"))


# --------------------------------------------------------------------------
# RLS hostile matrix (migration 0010 stage-1 private tables)
# --------------------------------------------------------------------------

def test_migration_0010_policies_present(app_engine):
    """The stage-1 policies from migration 0010 exist and RLS is enabled."""
    with app_engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT tablename, policyname FROM pg_policies "
                "WHERE schemaname = 'public' AND tablename = ANY(:tables) "
                "ORDER BY tablename"
            ),
            {"tables": PRIVATE_TABLES},
        ).all()
        by_table = {}
        for tablename, policyname in rows:
            by_table.setdefault(tablename, []).append(policyname)
        for table in PRIVATE_TABLES:
            assert f"{table}_owner" in by_table.get(table, []), table
        relrows = conn.execute(
            text(
                "SELECT relname, relrowsecurity FROM pg_class "
                "WHERE relname = ANY(:tables) AND relnamespace = "
                "(SELECT oid FROM pg_namespace WHERE nspname='public')"
            ),
            {"tables": PRIVATE_TABLES},
        ).all()
        assert all(rls for _name, rls in relrows), "RLS not enabled on every stage-1 table"


def test_rls_unauthenticated_session_sees_nothing(app_engine, persons):
    """No session identity => zero rows on private tables (deny by default)."""
    with app_engine.connect() as conn:
        assert _count(conn, "career_goals") == 0
        conn.execute(text("COMMIT"))


def test_rls_owner_sees_own_private_data_only(app_engine, persons, rls_ctx):
    """Positive control: own rows visible; other person's rows invisible."""
    with _as_user(app_engine, persons["p1"]) as conn:
        assert _count(conn, "career_goals") == 1
        titles = [
            r[0]
            for r in conn.execute(
                text("SELECT title FROM career_goals")
            ).all()
        ]
        assert titles == ["Goal A"]
        conn.execute(text("COMMIT"))


def test_rls_cross_user_read_denied(app_engine, persons, rls_ctx):
    """User A must never see user B's private data even knowing its UUID."""
    with _as_user(app_engine, persons["p1"]) as conn:
        row = conn.execute(
            text("SELECT title FROM career_goals WHERE id = :g2"),
            {"g2": persons["g2"]},
        ).fetchone()
        assert row is None
        conn.execute(text("COMMIT"))


def test_rls_cross_user_mutation_denied(app_engine, persons, rls_ctx):
    """User A cannot update or delete user B's rows (0 rows affected)."""
    with _as_user(app_engine, persons["p1"]) as conn:
        upd = conn.execute(
            text("UPDATE career_goals SET title = 'HACKED' WHERE id = :g2"),
            {"g2": persons["g2"]},
        )
        dele = conn.execute(
            text("DELETE FROM career_goals WHERE id = :g2"),
            {"g2": persons["g2"]},
        )
        assert upd.rowcount == 0
        assert dele.rowcount == 0
        conn.execute(text("COMMIT"))


def test_rls_unauthenticated_insert_denied(app_engine, persons):
    """WITH CHECK blocks inserts that do not match the session identity."""
    with app_engine.connect() as conn:
        with pytest.raises(Exception) as exc:
            conn.execute(
                text(
                    "INSERT INTO career_goals (id, person_id, title, target_role, status) "
                    "VALUES (:g,:p,'Sneaky','Role','active')"
                ),
                {"g": uuid.uuid4(), "p": persons["p1"]},
            )
        assert "row-level security" in str(exc.value).lower()
        conn.rollback()


def test_rls_owner_insert_allowed_with_identity(app_engine, persons, rls_ctx):
    """With the correct session identity, own-row inserts pass WITH CHECK."""
    with _as_user(app_engine, persons["p1"]) as conn:
        conn.execute(
            text(
                "INSERT INTO career_goals (id, person_id, title, target_role, status) "
                "VALUES (:g,:p,'Goal C','Role C','active')"
            ),
            {"g": uuid.uuid4(), "p": persons["p1"]},
        )
        conn.execute(text("COMMIT"))
    # Verify the row landed (owner view).
    with _as_user(app_engine, persons["p1"]) as conn:
        assert _count(conn, "career_goals") == 2
        conn.execute(text("COMMIT"))


# --------------------------------------------------------------------------
# Least privilege: the runtime role must not be able to change the schema
# --------------------------------------------------------------------------

def test_app_role_cannot_perform_ddl(app_engine):
    with app_engine.connect() as conn:
        with pytest.raises(Exception) as exc:
            conn.execute(text("ALTER TABLE career_goals ADD COLUMN pwned INTEGER"))
        msg = str(exc.value).lower()
        assert "permission denied" in msg or "must be owner" in msg
        conn.rollback()
    with app_engine.connect() as conn:
        is_super = conn.execute(
            text("SELECT rolsuper FROM pg_roles WHERE rolname = current_user")
        ).scalar()
        assert is_super is False
        conn.execute(text("COMMIT"))


def test_app_role_cannot_touch_legacy_schema(app_engine):
    """The runtime role has no privileges on legacy auth/storage surfaces."""
    with app_engine.connect() as conn:
        n = conn.execute(
            text(
                "SELECT count(*) FROM pg_namespace n "
                "WHERE n.nspname IN ('auth','storage') "
                "AND has_schema_privilege(current_user, n.nspname, 'USAGE')"
            )
        ).scalar()
        assert n == 0
        conn.execute(text("COMMIT"))