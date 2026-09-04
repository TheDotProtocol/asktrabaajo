"""Wave 8 — government intelligence: aggregation, k-threshold, isolation."""
from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.identity import User
from app.models.tenancy import Membership, Organization
from app.models.work import UserSkill, WorkExperience
from app.services import government as gov
from app.services.auth_service import get_person_for_user, register_user
from app.services import skills_registry
from datetime import date

PASSWORD = "Wave8-gov-test!"


def _headers(client: TestClient, email: str) -> dict:
    r = client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _register(client: TestClient, email: str, name: str = "DEV Gov") -> None:
    r = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": PASSWORD, "full_name": name},
    )
    assert r.status_code == 201, r.text


def _gov_membership(db: Session, user_id, name: str = "DEV Gov Org") -> Organization:
    org = Organization(
        name=name,
        slug=f"dev-gov-{uuid.uuid4().hex[:8]}",
        kind="government",
        created_by=user_id,
    )
    db.add(org)
    db.flush()
    db.add(
        Membership(
            user_id=user_id,
            organization_id=org.id,
            role_code="government_user",
            created_by=user_id,
        )
    )
    db.commit()
    return org


def _person_with_skill(db: Session, email: str, city: str, skill_name: str) -> None:
    register_user(db, email=email, password=PASSWORD, full_name=email.split("@")[0])
    user = db.query(User).filter(User.email == email).one()
    person = get_person_for_user(db, user.id)
    person.city = city
    person.country_code = "DEV"
    skill = skills_registry.ensure_skill(db, skill_name)
    db.add(UserSkill(person_id=person.id, skill_id=skill.id, level="intermediate"))
    db.add(
        WorkExperience(
            person_id=person.id,
            company_name="DEV Co",
            title="DEV",
            start_date=date(2024, 1, 1),
            is_current=True,
        )
    )
    db.commit()


def test_government_requires_membership(client: TestClient, make_user):
    created = make_user("plain@example.com", password=PASSWORD)
    r = client.get(
        "/api/v1/government/overview",
        headers=created["authorization"],
    )
    assert r.status_code == 403


def test_no_person_lookup_route(client: TestClient):
    r = client.get("/api/v1/government/person/00000000-0000-0000-0000-000000000001")
    assert r.status_code in {401, 404, 405}


def test_k_threshold_and_isolation(client: TestClient, db: Session, make_user):
    gov_email = f"gov-{uuid.uuid4().hex[:6]}@example.com"
    other_email = f"emp-{uuid.uuid4().hex[:6]}@example.com"
    _register(client, gov_email, "DEV Government Analyst")
    _register(client, other_email, "DEV Employer")
    gov_user = db.query(User).filter(User.email == gov_email).one()
    org_a = _gov_membership(db, gov_user.id, "DEV Government A")
    org_b = Organization(
        name="DEV Government B",
        slug=f"dev-gov-b-{uuid.uuid4().hex[:6]}",
        kind="government",
    )
    db.add(org_b)
    db.commit()

    for i in range(12):
        email = f"wf-{i}-{uuid.uuid4().hex[:4]}@example.com"
        _person_with_skill(db, email, "Development City", "Python")

    for i in range(3):
        email = f"sp-{i}-{uuid.uuid4().hex[:4]}@example.com"
        _person_with_skill(db, email, "Sparse Town", "RareSkillDEV")

    headers = _headers(client, gov_email)
    overview = client.get("/api/v1/government/overview", headers=headers)
    assert overview.status_code == 200, overview.text
    body = overview.json()
    assert "id" not in str(body.get("cards"))
    assert body["cards"]["registered_workforce"]["status"] == "ok"
    assert body["cards"]["registered_workforce"]["value"] >= 12
    assert "email" not in overview.text.lower() or "privacy" in overview.text.lower()

    skills = client.get("/api/v1/government/skills", headers=headers).json()
    python = next(b for b in skills["supply"]["buckets"] if b["key"] == "Python")
    rare = next(b for b in skills["supply"]["buckets"] if b["key"] == "RareSkillDEV")
    assert python["status"] == "ok"
    assert python["value"] >= 12
    assert rare["status"] == "suppressed"
    assert rare["value"] is None

    geo = client.get(
        "/api/v1/government/workforce/geography",
        headers=headers,
        params={"city": "Sparse Town"},
    ).json()
    assert geo["status"] == "insufficient_cohort"

    forbidden = client.get(
        f"/api/v1/government/overview?organization_id={org_b.id}",
        headers=headers,
    )
    assert forbidden.status_code == 403

    emp = client.post(
        "/api/v1/organizations",
        headers=_headers(client, other_email),
        json={"name": "DEV Emp Wave8", "kind": "employer"},
    )
    assert emp.status_code == 201
    emp_headers = _headers(client, other_email)
    assert client.get("/api/v1/government/overview", headers=emp_headers).status_code == 403

    settings = client.get("/api/v1/government/settings", headers=headers).json()
    assert settings["individual_lookup"] is False
    assert settings["privacy_threshold"] == 10

    report = client.get("/api/v1/government/reports/workforce", headers=headers)
    assert report.status_code == 200
    exported = client.get("/api/v1/government/exports/workforce?format=json", headers=headers)
    assert exported.status_code == 200
    assert exported.json()["contains_person_records"] is False

    # Athena government tools exist and are aggregate-only.
    tools = client.get("/api/v1/athena/tools?mode=government", headers=headers).json()
    names = {t["name"] for t in tools}
    assert "government.get_workforce_summary" in names
    assert "government.search_person" not in names
    assert "government.get_work_id" not in names


def test_suppression_helper_does_not_leak_count():
    rows = [("Visible", 12), ("Hidden", 3)]
    out = gov._buckets_from_rows(rows)
    hidden = next(b for b in out["buckets"] if b["key"] == "Hidden")
    assert hidden["value"] is None
    assert out["visible_sum"] is None


def test_volume_buckets_are_not_person_cohorts():
    out = gov._volume_buckets([("Technology", 1), ("Hospitality", 2)])
    assert out["visible_sum"] == 3
    assert out["any_suppressed"] is False
    assert all(bucket["value"] is not None for bucket in out["buckets"])


def test_invalid_filter_and_export_format(client: TestClient, db: Session):
    email = f"gov-fmt-{uuid.uuid4().hex[:6]}@example.com"
    register_user(db, email=email, password=PASSWORD, full_name="DEV Format")
    user = db.query(User).filter(User.email == email).one()
    _gov_membership(db, user.id)
    headers = _headers(client, email)
    too_long = client.get(
        "/api/v1/government/overview",
        headers=headers,
        params={"city": "x" * 81},
    )
    assert too_long.status_code == 422
    bad_format = client.get(
        "/api/v1/government/exports/workforce",
        headers=headers,
        params={"format": "pdf"},
    )
    assert bad_format.status_code == 422
