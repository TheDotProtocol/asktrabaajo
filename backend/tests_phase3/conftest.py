"""Phase 3 test harness — database isolation is non-negotiable.

Safety rules enforced here:
1. ``ENVIRONMENT`` is forced to ``test`` and ``DATABASE_URL`` is forced to an
   in-memory sqlite **before any application import**, so pytest can never
   connect to a configured (real) database. This mirrors the Phase-1 hazard:
   legacy tests could reach the live DB; the canonical suite cannot.
2. ``SECRET_KEY`` is a fixed test-only value; production fail-fast rules are
   themselves covered by dedicated config tests.
3. Every test gets a fresh in-memory database (StaticPool) with the full
   canonical schema + seeded role/permission catalog.
"""
import os

# Must run before importing anything from `app`.
os.environ["ENVIRONMENT"] = "test"
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["SECRET_KEY"] = "test-secret-key-not-for-production"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, event  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.db.base import Base  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.main import create_app  # noqa: E402
from app.models.catalog import seed_catalog  # noqa: E402

# Import every model so Base.metadata is complete before create_all.
from app.models import (  # noqa: F401,E402
    AuditLogEntry,
    Credential,
    DocumentAccessGrant,
    Education,
    Employment,
    Membership,
    Organization,
    Permission,
    PersonDocument,
    PersonProfile,
    RefreshToken,
    Role,
    RolePermission,
    Skill,
    User,
    UserSkill,
    WorkExperience,
)


@pytest.fixture()
def engine():
    """A fresh, isolated in-memory database per test."""
    eng = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )

    @event.listens_for(eng, "connect")
    def _enable_sqlite_fks(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(eng)
    with Session(eng) as session:
        seed_catalog(session)
    yield eng
    Base.metadata.drop_all(eng)
    eng.dispose()


@pytest.fixture()
def db(engine):
    session = Session(engine)
    yield session
    session.close()


@pytest.fixture()
def client(engine):
    """FastAPI TestClient with the dependency pointing at the test DB."""

    def _override_get_db():
        session = Session(engine)
        try:
            yield session
        finally:
            session.close()

    app = create_app()
    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def make_user(client):
    """Register a user via the API and return their tokens + user data."""

    def _make(email: str, password: str = "StrongPass123!", full_name: str = "Test Person"):
        response = client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": password, "full_name": full_name},
        )
        assert response.status_code == 201, response.text
        data = response.json()
        return {
            "email": email,
            "password": password,
            "tokens": data,
            "authorization": {"Authorization": f"Bearer {data['access_token']}"},
        }

    return _make
