"""Engine + session management for the canonical backend.

Phase 13: PostgreSQL RLS session identity. When ``RLS_SESSION_CONTEXT`` is
enabled (staging/production), every request stamps its database session
with ``app.current_user_id`` / ``app.current_org_ids`` from the
authenticated actor (set in ``app.api.deps``) and resets them when the
request ends, so pooled connections can never leak identity into the next
request and database-level RLS policies see the canonical identity.
"""
from __future__ import annotations

import uuid
from typing import Iterable, Optional

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.db.base import Base  # noqa: F401  (re-export for callers/tests)

settings = get_settings()

_engine_kwargs = {"pool_pre_ping": True, "future": True}
if settings.database_url.startswith("sqlite"):
    # sqlite is used only for local dev + the isolated test harness.
    _engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(settings.database_url, **_engine_kwargs)


def _force_utc_session(dbapi_connection, connection_record) -> None:
    """Every PostgreSQL connection runs in UTC.

    Canonical code stores naive-UTC datetimes (see ``app.core.timeutil``).
    PostgreSQL interprets naive values in the session TimeZone, so a server
    whose default zone is not UTC (e.g. Asia/Kolkata) would silently shift
    every stored instant by its offset and make expiry/window comparisons
    wrong. Pin the session zone so the naive-write -> aware-read round trip
    is exact and identical to the SQLite test frame.
    """
    if engine.dialect.name == "postgresql":
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("SET TIME ZONE 'UTC'")
        finally:
            cursor.close()


if engine.dialect.name == "postgresql":
    event.listen(engine, "connect", _force_utc_session)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)


_SESSION_KEYS = ("app.current_user_id", "app.current_org_ids")


def _rls_ctx_enabled(db) -> bool:
    """Only PostgreSQL + explicit opt-in carry the RLS session context.

    Accepts both ``Session`` (``.bind``) and ``Connection`` (``.engine``).
    """
    if not settings.rls_session_context:
        return False
    engine = getattr(db, "bind", None) or getattr(db, "engine", None)
    return engine is not None and engine.dialect.name == "postgresql"


def set_session_identity(
    db: Session,
    user_id: Optional[uuid.UUID],
    org_ids: Optional[Iterable[uuid.UUID]] = None,
) -> None:
    """Stamp the current DB session with the canonical actor identity.

    Uses session-level ``set_config`` (not ``SET LOCAL``) so the values
    survive service-layer commits within the request; ``get_db`` resets
    them in ``finally`` so pooled connections are never contaminated.
    Values are empty strings (never NULL) so policies compare safely.
    """
    if not _rls_ctx_enabled(db):
        return
    uid = str(user_id) if user_id is not None else ""
    orgs = (
        ",".join(str(o) for o in sorted({str(x) for x in (org_ids or [])}))
        if org_ids is not None
        else ""
    )
    db.execute(
        text("SELECT set_config(:k1, :v1, false), set_config(:k2, :v2, false)"),
        {"k1": "app.current_user_id", "v1": uid, "k2": "app.current_org_ids", "v2": orgs},
    )


def reset_session_identity(db: Session) -> None:
    """Clear the RLS session identity (called when the request ends)."""
    if not _rls_ctx_enabled(db):
        return
    db.execute(
        text("SELECT set_config(:k1, '', false), set_config(:k2, '', false)"),
        {"k1": "app.current_user_id", "k2": "app.current_org_ids"},
    )


def get_db():
    """FastAPI dependency yielding a scoped session.

    The RLS session identity is always cleared before the session closes so
    a returned pooled connection can never carry another actor's identity.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        if _rls_ctx_enabled(db):
            try:
                reset_session_identity(db)
                db.commit()
            except Exception:
                db.rollback()
        db.close()
