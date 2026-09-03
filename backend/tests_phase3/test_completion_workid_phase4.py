"""Phase 4 — profile completion + extended Work ID sections."""
from __future__ import annotations

from sqlalchemy import select

from app.models.identity import User

PASSWORD = "StrongPass123!"


def _add_experience(client, headers):
    return client.post(
        "/api/v1/work-id/experiences",
        headers=headers,
        json={
            "company_name": "Acme Corp",
            "title": "Platform Engineer",
            "department": "Engineering",
            "location": "Dubai",
            "start_date": "2022-01-01",
            "is_current": True,
            "skills_used": ["python", "sql"],
        },
    )


def test_completion_starts_low_and_grows(client, make_user, db):
    user = make_user("complete@example.com", password=PASSWORD)
    headers = user["authorization"]

    r = client.get("/api/v1/work-id/completion", headers=headers)
    assert r.status_code == 200
    assert r.json()["percent"] == 0

    # identity + contact
    client.put(
        "/api/v1/work-id/profile",
        headers=headers,
        json={"headline": "Engineer", "city": "Dubai", "country_code": "AE"},
    )
    # education
    client.post(
        "/api/v1/work-id/educations",
        headers=headers,
        json={"institution": "Some University", "level": "undergraduate"},
    )
    # experience + employment
    assert _add_experience(client, headers).status_code == 201
    client.post(
        "/api/v1/work-id/employments",
        headers=headers,
        json={
            "company_name": "Acme Corp",
            "title": "Engineer",
            "employment_type": "full_time",
            "start_date": "2022-01-01",
            "is_current": True,
        },
    )
    # 3 skills + 1 credential
    for skill in ("python", "sql", "aws"):
        client.put(
            "/api/v1/work-id/skills",
            headers=headers,
            json={"skill_name": skill, "level": "advanced"},
        )
    client.post(
        "/api/v1/work-id/credentials",
        headers=headers,
        json={"name": "AWS Certified", "issuer": "AWS"},
    )

    r = client.get("/api/v1/work-id/completion", headers=headers)
    body = r.json()
    # Everything except a verified email is now met → 95%.
    assert body["percent"] == 95
    assert "verified_email" in body["missing"]
    assert body["sections"]["experience"]["met"] is True
    assert body["sections"]["skills"]["met"] is True
    assert body["sections"]["credentials"]["met"] is True

    # Authoritative email verification (the real flow is tested in
    # test_account_phase4) completes the profile → 100%.
    from datetime import datetime, timezone

    stored_user = db.scalar(
        select(User).where(User.email == "complete@example.com")
    )
    stored_user.email_verified_at = datetime.now(timezone.utc)
    db.commit()

    final = client.get("/api/v1/work-id/completion", headers=headers).json()
    assert final["percent"] == 100
    assert final["missing"] == []


def test_experience_new_fields_and_verification_state(client, make_user, db):
    user = make_user("fields@example.com", password=PASSWORD)
    created = _add_experience(client, user["authorization"])
    assert created.status_code == 201
    exp = created.json()
    assert exp["department"] == "Engineering"
    assert exp["skills_used"] == ["python", "sql"]
    assert exp["verification_status"] == "unverified"

    # Self-reported records never come back as verified.
    assert exp["verification_status"] != "verified"

    edu = client.post(
        "/api/v1/work-id/educations",
        headers=user["authorization"],
        json={
            "institution": "UAE University",
            "level": "postgraduate",
            "field_of_study": "Data Science",
        },
    )
    assert edu.status_code == 201
    assert edu.json()["level"] == "postgraduate"
    assert edu.json()["verification_status"] == "unverified"

    # Invalid education level → 422.
    bad = client.post(
        "/api/v1/work-id/educations",
        headers=user["authorization"],
        json={"institution": "X", "level": "wizardry"},
    )
    assert bad.status_code == 422


def test_employment_delete_and_workid_summary(client, make_user):
    user = make_user("empdel@example.com", password=PASSWORD)
    headers = user["authorization"]
    emp = client.post(
        "/api/v1/work-id/employments",
        headers=headers,
        json={
            "company_name": "Acme",
            "title": "Engineer",
            "department": "Engineering",
            "employment_type": "full_time",
            "start_date": "2021-01-01",
            "is_current": True,
        },
    )
    assert emp.status_code == 201
    emp_id = emp.json()["id"]
    assert emp.json()["department"] == "Engineering"

    summary = client.get("/api/v1/work-id", headers=headers).json()
    assert len(summary["employments"]) == 1

    deleted = client.delete(
        f"/api/v1/work-id/employments/{emp_id}", headers=headers
    )
    assert deleted.status_code == 200
    assert client.get("/api/v1/work-id", headers=headers).json()["employments"] == []
