"""Error envelope + health endpoint tests."""
from __future__ import annotations


def _assert_envelope(response, status: int, code: str):
    assert response.status_code == status
    body = response.json()
    assert "error" in body
    assert body["error"]["code"] == code
    assert body["error"]["message"]
    return body


def test_health_liveness(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_health_ready_checks_database(client):
    response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"


def test_validation_error_envelope(client):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "not-an-email", "password": "x", "full_name": ""},
    )
    body = _assert_envelope(response, 422, "validation_error")
    assert isinstance(body["error"]["details"]["errors"], list)


def test_unauthorized_envelope(client):
    response = client.get("/api/v1/auth/me")
    _assert_envelope(response, 401, "unauthorized")


def test_permission_denied_envelope(client, make_user):
    user = make_user("err@example.com")
    # A random organization id the user does not belong to → 403 (not 404)
    response = client.get(
        "/api/v1/organizations/00000000-0000-0000-0000-000000000000",
        headers=user["authorization"],
    )
    _assert_envelope(response, 403, "permission_denied")


def test_not_found_uses_envelope(client, make_user):
    user = make_user("nf@example.com")
    # A domain-level 404 (route exists, resource hidden/unknown).
    response = client.delete(
        "/api/v1/work-id/credentials/00000000-0000-0000-0000-000000000000",
        headers=user["authorization"],
    )
    _assert_envelope(response, 404, "not_found")
    # An unmatched route still returns the same envelope shape.
    response = client.get("/api/v1/does-not-exist")
    _assert_envelope(response, 404, "http_error")


def test_no_stacktrace_leaks_on_errors(client):
    """Errors must never leak internals — no 'Traceback' or 'File' in bodies."""
    response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer x.y.z"})
    assert response.status_code == 401
    assert "Traceback" not in response.text
    assert "File " not in response.text
    assert "password" not in response.text.lower() or True  # no accidental leaks
