"""Auth foundation tests — register/login/me/refresh/logout + token security."""
from __future__ import annotations

from sqlalchemy import select

from app.models.audit import AuditLogEntry
from app.models.identity import PersonProfile, RefreshToken, User


def test_register_creates_user_and_person_profile(db, client, make_user):
    user = make_user("register@example.com")
    assert user["tokens"]["token_type"] == "bearer"
    assert user["tokens"]["access_token"]
    assert user["tokens"]["refresh_token"]

    stored = db.scalar(select(User).where(User.email == "register@example.com"))
    assert stored is not None
    assert stored.password_hash.startswith("$2")  # bcrypt, never plaintext
    assert stored.password_hash != "StrongPass123!"

    person = db.scalar(
        select(PersonProfile).where(PersonProfile.user_id == stored.id)
    )
    assert person is not None
    assert db.scalar(select(AuditLogEntry).where(AuditLogEntry.action == "auth.register"))


def test_register_rejects_duplicate_email(client, make_user):
    make_user("dup@example.com")
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "dup@example.com", "password": "StrongPass123!", "full_name": "X"},
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "conflict"


def test_register_rejects_weak_password(client):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "weak@example.com", "password": "short", "full_name": "X"},
    )
    assert response.status_code == 422


def test_login_wrong_password_does_not_reveal_existence(client, make_user):
    make_user("secret@example.com")
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "secret@example.com", "password": "WrongPass123!"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@example.com", "password": "WrongPass123!"},
    )
    assert response.status_code == 401


def test_me_round_trip(client, make_user):
    user = make_user("me@example.com")
    response = client.get("/api/v1/auth/me", headers=user["authorization"])
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "me@example.com"
    assert body["full_name"] == "Test Person"
    assert body["person"] is not None
    assert body["super_admin"] is False
    assert "admin.manage" not in body["permissions"]


def test_me_requires_token(client):
    assert client.get("/api/v1/auth/me").status_code == 401
    assert (
        client.get(
            "/api/v1/auth/me", headers={"Authorization": "Bearer garbage"}
        ).status_code
        == 401
    )


def test_refresh_rotation_and_reuse_detection(client, make_user):
    user = make_user("rotate@example.com")
    first_refresh = user["tokens"]["refresh_token"]

    # Rotate: old refresh is revoked, new pair issued.
    response = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": first_refresh}
    )
    assert response.status_code == 200
    second = response.json()

    # Replaying the old token = theft signal: everything revoked.
    response = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": first_refresh}
    )
    assert response.status_code == 401

    # Even the freshly issued token is now dead (family revocation).
    response = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": second["refresh_token"]}
    )
    assert response.status_code == 401


def test_register_issues_single_persistent_refresh(db, client, make_user):
    user = make_user("persist@example.com")
    stored_user = db.scalar(select(User).where(User.email == "persist@example.com"))
    rows = db.scalars(
        select(RefreshToken).where(RefreshToken.user_id == stored_user.id)
    ).all()
    assert len(rows) == 1  # one refresh token from register
    assert rows[0].revoked_at is None
    assert user["tokens"]["refresh_token"]


def test_logout_revokes_refresh(client, db, make_user):
    make_user("logout@example.com")
    response = client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": "placeholder-token-aaaaaaaaaaaaaaaaaaaa"},
    )
    # Unknown token: still succeeds, nothing to revoke.
    assert response.status_code == 200

    user = make_user("logout2@example.com")
    response = client.post(
        "/api/v1/auth/logout", json={"refresh_token": user["tokens"]["refresh_token"]}
    )
    assert response.status_code == 200
    stored_user = db.scalar(select(User).where(User.email == "logout2@example.com"))
    rows = db.scalars(
        select(RefreshToken).where(RefreshToken.user_id == stored_user.id)
    ).all()
    assert len(rows) == 1
    assert rows[0].revoked_at is not None
    assert db.scalar(
        select(AuditLogEntry).where(AuditLogEntry.action == "auth.logout")
    )


def test_access_token_uses_typed_claims(client, make_user):
    user = make_user("claims@example.com")
    response = client.get("/api/v1/auth/me", headers=user["authorization"])
    assert response.status_code == 200
