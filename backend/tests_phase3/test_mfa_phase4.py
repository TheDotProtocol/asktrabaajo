"""Phase 4 — MFA (TOTP) foundation tests.

Codes are generated with the same stdlib TOTP implementation the API uses,
so tests exercise real application logic.
"""
from __future__ import annotations

from sqlalchemy import select

from app.models.audit import AuditLogEntry
from app.models.identity import User
from app.services import mfa as mfa_service

PASSWORD = "StrongPass123!"


def test_mfa_enable_confirm_and_login_flow(client, make_user, db):
    user = make_user("mfa@example.com", password=PASSWORD)
    headers = user["authorization"]

    enabled = client.post("/api/v1/auth/mfa/enable", headers=headers)
    assert enabled.status_code == 200, enabled.text
    secret = enabled.json()["secret"]
    assert enabled.json()["confirmed"] is False
    assert "otpauth://totp/AskTrabaajo:mfa@example.com" in enabled.json()["otpauth_uri"]

    # Wrong code rejected.
    wrong = client.post(
        "/api/v1/auth/mfa/confirm", headers=headers, json={"code": "000000"}
    )
    assert wrong.status_code == 400

    # Correct code confirms.
    code = mfa_service.current_code(secret)
    confirmed = client.post(
        "/api/v1/auth/mfa/confirm", headers=headers, json={"code": code}
    )
    assert confirmed.status_code == 200
    assert confirmed.json()["confirmed"] is True
    assert client.get("/api/v1/auth/me", headers=headers).json()["mfa_enabled"] is True

    # Login now demands the second step.
    r = client.post(
        "/api/v1/auth/login",
        json={"email": "mfa@example.com", "password": PASSWORD},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["mfa_required"] is True
    assert body["mfa_token"]
    assert body["access_token"] is None

    # Wrong MFA code fails; correct code returns a real token pair.
    bad = client.post(
        "/api/v1/auth/mfa/verify",
        json={"mfa_token": body["mfa_token"], "code": "000000"},
    )
    assert bad.status_code == 400

    good = client.post(
        "/api/v1/auth/mfa/verify",
        json={"mfa_token": body["mfa_token"], "code": mfa_service.current_code(secret)},
    )
    assert good.status_code == 200, good.text
    assert good.json()["access_token"]

    # Audit trail exists for enable + failed second step.
    assert db.scalar(
        select(AuditLogEntry).where(AuditLogEntry.action == "auth.mfa_enabled")
    )
    assert db.scalar(
        select(AuditLogEntry).where(AuditLogEntry.action == "auth.mfa.verify_failed")
    )


def test_mfa_disable_requires_current_code(client, make_user):
    user = make_user("mfa-off@example.com", password=PASSWORD)
    headers = user["authorization"]
    secret = client.post("/api/v1/auth/mfa/enable", headers=headers).json()["secret"]
    code = mfa_service.current_code(secret)
    assert client.post(
        "/api/v1/auth/mfa/confirm", headers=headers, json={"code": code}
    ).status_code == 200

    wrong = client.post(
        "/api/v1/auth/mfa/disable", headers=headers, json={"code": "000000"}
    )
    assert wrong.status_code == 400

    off = client.post(
        "/api/v1/auth/mfa/disable",
        headers=headers,
        json={"code": mfa_service.current_code(secret)},
    )
    assert off.status_code == 200
    assert client.get("/api/v1/auth/me", headers=headers).json()["mfa_enabled"] is False


def test_totp_verification_utilities():
    secret = mfa_service.generate_secret()
    assert len(secret) >= 16
    code = mfa_service.current_code(secret)
    assert len(code) == 6 and code.isdigit()
    assert mfa_service.verify_code(secret, code) is True
    assert mfa_service.verify_code(secret, "000000") is False
    assert mfa_service.verify_code("", "000000") is False
    assert mfa_service.verify_code(secret, "abc") is False
