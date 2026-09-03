"""Work ID foundation tests — ownership isolation + behavior."""
from __future__ import annotations

import uuid

from sqlalchemy import select

from app.models.work import Credential, Education, UserSkill, WorkExperience

EXP_PAYLOAD = {
    "company_name": "Acme Corp",
    "title": "Platform Engineer",
    "start_date": "2022-01-01",
    "is_current": True,
    "description": "Built things.",
}


def test_profile_update(client, make_user):
    user = make_user("workid@example.com")
    response = client.put(
        "/api/v1/work-id/profile",
        headers=user["authorization"],
        json={"headline": "Engineer", "location": "Dubai", "country_code": "AE"},
    )
    assert response.status_code == 200
    assert response.json()["headline"] == "Engineer"

    me = client.get("/api/v1/auth/me", headers=user["authorization"]).json()
    assert me["person"]["headline"] == "Engineer"


def test_experience_crud(client, make_user):
    user = make_user("exp@example.com")
    created = client.post(
        "/api/v1/work-id/experiences",
        headers=user["authorization"],
        json=EXP_PAYLOAD,
    )
    assert created.status_code == 201, created.text
    exp_id = created.json()["id"]

    listed = client.get("/api/v1/work-id/experiences", headers=user["authorization"])
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    patched = client.patch(
        f"/api/v1/work-id/experiences/{exp_id}",
        headers=user["authorization"],
        json={"title": "Senior Platform Engineer"},
    )
    assert patched.status_code == 200
    assert patched.json()["title"] == "Senior Platform Engineer"

    deleted = client.delete(
        f"/api/v1/work-id/experiences/{exp_id}", headers=user["authorization"]
    )
    assert deleted.status_code == 200
    assert client.get("/api/v1/work-id/experiences", headers=user["authorization"]).json() == []


def test_user_a_cannot_touch_user_b_work_id(client, make_user, db):
    """PHASE-3 REGRESSION: cross-user access to Work ID data returns 404."""
    alice = make_user("alice@example.com")
    bob = make_user("bob@example.com")

    created = client.post(
        "/api/v1/work-id/experiences",
        headers=alice["authorization"],
        json=EXP_PAYLOAD,
    )
    assert created.status_code == 201
    exp_id = created.json()["id"]

    # Bob cannot read/update/delete Alice's record — existence is hidden.
    response = client.patch(
        f"/api/v1/work-id/experiences/{exp_id}",
        headers=bob["authorization"],
        json={"title": "Hijacked"},
    )
    assert response.status_code == 404
    response = client.delete(
        f"/api/v1/work-id/experiences/{exp_id}", headers=bob["authorization"]
    )
    assert response.status_code == 404

    stored = db.get(WorkExperience, uuid.UUID(exp_id))
    assert stored.title == "Platform Engineer"  # unchanged


def test_education_skill_credential_flows(client, make_user, db):
    user = make_user("full@example.com")

    # Education
    edu = client.post(
        "/api/v1/work-id/educations",
        headers=user["authorization"],
        json={"institution": "Some University", "degree": "BSc", "is_current": False},
    )
    assert edu.status_code == 201
    assert client.get("/api/v1/work-id/educations", headers=user["authorization"]).status_code == 200

    # Skills (catalog-less auto-create)
    skill = client.put(
        "/api/v1/work-id/skills",
        headers=user["authorization"],
        json={"skill_name": "Python", "level": "advanced"},
    )
    assert skill.status_code == 200, skill.text
    skill_id = skill.json()["skill_id"]
    mine = client.get("/api/v1/work-id/skills", headers=user["authorization"])
    assert len(mine.json()) == 1

    # Credentials default to UNVERIFIED and verification fields are not settable.
    cred = client.post(
        "/api/v1/work-id/credentials",
        headers=user["authorization"],
        json={
            "name": "AWS Certified Developer",
            "issuer": "AWS",
            "credential_type": "certification",
        },
    )
    assert cred.status_code == 201, cred.text
    assert cred.json()["status"] == "unverified"
    assert cred.json()["verified_at"] is None
    assert db.scalar(
        select(Credential).where(Credential.name == "AWS Certified Developer")
    ).status == "unverified"

    # Owner cannot self-verify through the update schema (field absent).
    updated = client.patch(
        f"/api/v1/work-id/credentials/{cred.json()['id']}",
        headers=user["authorization"],
        json={"name": "AWS Certified Developer - Associate"},
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "unverified"

    # Employment
    emp = client.post(
        "/api/v1/work-id/employments",
        headers=user["authorization"],
        json={
            "company_name": "Acme",
            "title": "Engineer",
            "employment_type": "full_time",
            "start_date": "2021-06-01",
            "is_current": True,
        },
    )
    assert emp.status_code == 201
    assert client.get("/api/v1/work-id/employments", headers=user["authorization"]).status_code == 200

    # Bad employment type rejected.
    bad = client.post(
        "/api/v1/work-id/employments",
        headers=user["authorization"],
        json={
            "company_name": "X",
            "title": "Y",
            "employment_type": "galactic",
            "start_date": "2021-06-01",
        },
    )
    assert bad.status_code == 422

    # Skill removal.
    removed = client.delete(
        f"/api/v1/work-id/skills/{skill_id}", headers=user["authorization"]
    )
    assert removed.status_code == 200
    assert client.get("/api/v1/work-id/skills", headers=user["authorization"]).json() == []


def test_work_id_summary_returns_sections(client, make_user):
    user = make_user("summary@example.com")
    response = client.get("/api/v1/work-id", headers=user["authorization"])
    assert response.status_code == 200
    body = response.json()
    for section in ("person", "experiences", "educations", "skills", "credentials", "employments"):
        assert section in body
    assert body["experiences"] == []
