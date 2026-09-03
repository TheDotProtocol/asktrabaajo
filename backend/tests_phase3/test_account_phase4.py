"""Phase 4 — account lifecycle: password change/reset, email verification,
session management, and auth rate limiting."""
from __future__ import annotations

import uuid

from sqlalchemy import select

from app.models.audit import AuditLogEntry
from app.models.identity import (
    EmailVerificationToken,
    PasswordResetToken,
    RefreshToken,
    User,
)

PASSWORD = "StrongPass123!"


def _user_id(db, email):
    return db.scalar(select(User).where(User.email == email)).id


def test_change_password_rotates_everything(client, make_user, db):
    user = make_user("pw-change@example.com", password=PASSWORD)
    old_access = user["tokens"]["access_token"]
    old_refresh = user["tokens"]["refresh_token"]
    auth_old = {"Authorization": f"Bearer {old_access}"}

    # Wrong current password → 401.
    r = client.post(
        "/api/v1/auth/change-password",
        headers=auth_old,
        json={"current_password": "WrongPass123!", "new_password": "NewStrongPass1!"},
    )
    assert r.status_code == 401

    # Correct change → new token pair; old access token is dead.
    r = client.post(
        "/api/v1/auth/change-password",
        headers=auth_old,
        json={"current_password": PASSWORD, "new_password": "NewStrongPass1!"},
    )
    assert r.status_code == 200, r.text
    new_tokens = r.json()
    assert new_tokens["access_token"] != old_access
    assert client.get("/api/v1/auth/me", headers=auth_old).status_code == 401
    assert client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {new_tokens['access_token']}"},
    ).status_code == 200

    # Old refresh token is revoked; new password works, old does not.
    assert (
        client.post(
            "/api/v1/auth/refresh", json={"refresh_token": old_refresh}
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/api/v1/auth/login",
            json={"email": "pw-change@example.com", "password": PASSWORD},
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/api/v1/auth/login",
            json={"email": "pw-change@example.com", "password": "NewStrongPass1!"},
        ).status_code
        == 200
    )
    assert db.scalar(
        select(AuditLogEntry).where(AuditLogEntry.action == "auth.password_changed")
    )


def test_forgot_and_reset_password(client, make_user, db):
    make_user("forgot@example.com", password=PASSWORD)

    # Unknown emails and known emails both return the same message.
    for email in ("forgot@example.com", "missing@example.com"):
        r = client.post(
            "/api/v1/auth/forgot-password", json={"email": email}
        )
        assert r.status_code == 200
        assert "has been sent" in r.json()["message"]

    user_id = _user_id(db, "forgot@example.com")
    rows = db.scalars(
        select(PasswordResetToken).where(PasswordResetToken.user_id == user_id)
    ).all()
    assert len(rows) == 1

    # The token is never exposed: fetch the stored row and reset with it via
    # a fresh issuance path is impossible — instead rotate a second token and
    # validate expiry/single-use semantics on the row level.
    row = rows[0]
    assert row.used_at is None
    # Emulate the emailed token by inserting a known-hash token directly
    # (email transport is intentionally unreadable in tests).
    from app.core.security import hash_token, generate_random_token

    plain = generate_random_token()
    db.add(
        PasswordResetToken(
            user_id=user_id, token_hash=hash_token(plain), expires_at=rows[0].expires_at
        )
    )
    db.commit()

    # Wrong token → 401.
    assert (
        client.post(
            "/api/v1/auth/reset-password",
            json={"token": "not-a-real-token-aaaaaaaaaaaaaaaa", "new_password": "ResetPass123!"},
        ).status_code
        == 401
    )

    # Correct token → password reset, all sessions dead.
    r = client.post(
        "/api/v1/auth/reset-password",
        json={"token": plain, "new_password": "ResetPass123!"},
    )
    assert r.status_code == 200, r.text

    # Replay is refused.
    assert (
        client.post(
            "/api/v1/auth/reset-password",
            json={"token": plain, "new_password": "ResetPass123!"},
        ).status_code
        == 401
    )

    assert (
        client.post(
            "/api/v1/auth/login",
            json={"email": "forgot@example.com", "password": PASSWORD},
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/api/v1/auth/login",
            json={"email": "forgot@example.com", "password": "ResetPass123!"},
        ).status_code
        == 200
    )
    assert db.scalar(
        select(AuditLogEntry).where(AuditLogEntry.action == "auth.password_reset")
    )


def test_email_verification_flow(client, make_user, db):
    user = make_user("verify@example.com", password=PASSWORD)
    headers = user["authorization"]
    assert client.get("/api/v1/auth/me", headers=headers).json()["email_verified"] is False

    r = client.post("/api/v1/auth/verify-email/send", headers=headers)
    assert r.status_code == 200

    user_id = _user_id(db, "verify@example.com")
    rows = db.scalars(
        select(EmailVerificationToken).where(
            EmailVerificationToken.user_id == user_id
        )
    ).all()
    assert len(rows) == 1

    # Emulate the emailed token (hashed at rest — never readable).
    from app.core.security import generate_random_token, hash_token

    plain = generate_random_token()
    db.add(
        EmailVerificationToken(
            user_id=user_id,
            token_hash=hash_token(plain),
            expires_at=rows[0].expires_at,
        )
    )
    db.commit()

    assert (
        client.post(
            "/api/v1/auth/verify-email",
            json={"token": "garbage-token-aaaaaaaaaaaaaaaa"},
        ).status_code
        == 401
    )

    r = client.post("/api/v1/auth/verify-email", json={"token": plain})
    assert r.status_code == 200
    assert r.json()["email_verified"] is True

    # Replay refused; me now reports verified; resend short-circuits.
    assert (
        client.post("/api/v1/auth/verify-email", json={"token": plain}).status_code
        == 401
    )
    assert client.get("/api/v1/auth/me", headers=headers).json()["email_verified"] is True
    r = client.post("/api/v1/auth/verify-email/send", headers=headers)
    assert r.status_code == 200
    assert "already verified" in r.json()["message"]
    assert db.scalar(
        select(AuditLogEntry).where(AuditLogEntry.action == "auth.email_verified")
    )


def test_session_list_and_revoke_all(client, make_user, db):
    user = make_user("sessions@example.com", password=PASSWORD)
    headers = user["authorization"]

    # register issued one refresh session; logging in adds a second.
    client.post(
        "/api/v1/auth/login",
        json={"email": "sessions@example.com", "password": PASSWORD},
    )
    sessions = client.get("/api/v1/auth/sessions", headers=headers).json()
    assert len(sessions) == 2
    assert all("id" in s and "created_at" in s for s in sessions)

    r = client.post("/api/v1/auth/sessions/revoke-all", headers=headers)
    assert r.status_code == 200
    assert client.get("/api/v1/auth/sessions", headers=headers).json() == []
    assert (
        client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": user["tokens"]["refresh_token"]},
        ).status_code
        == 401
    )


def test_login_rate_limit(client, make_user):
    """Rate limiter protects the login endpoint (10/min per client ip)."""
    make_user("ratelimit@example.com", password=PASSWORD)
    attempts = 0
    for _ in range(10):
        r = client.post(
            "/api/v1/auth/login",
            json={"email": "ratelimit@example.com", "password": "WrongPass123!"},
        )
        attempts += 1
        assert r.status_code == 401
    r = client.post(
        "/api/v1/auth/login",
        json={"email": "ratelimit@example.com", "password": PASSWORD},
    )
    assert r.status_code == 429
    assert r.json()["error"]["code"] == "rate_limited"
