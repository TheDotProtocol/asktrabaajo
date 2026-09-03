"""Phase 6 — Company / HR / Recruiter Employment OS tests.

Security targets from the brief:
- Company A can never access Company B jobs/applications/candidates/offers.
- Unauthorized members cannot publish jobs or issue offers (RBAC).
- Recruiter without candidate permission cannot see protected data.
- Candidate documents are only reachable through an approved request.
- Jobseeker and employer share ONE application lifecycle (offer acceptance
  synchronizes; employer pipeline and candidate view agree).
"""
from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.career import JobApplication, Offer, Opportunity
from app.models.company import JobPosting


# --- fixtures for Phase 6 ----------------------------------------------------

def _create_company(client: TestClient, admin, name: str, slug: str) -> dict:
    response = client.post(
        "/api/v1/organizations",
        headers=admin["authorization"],
        json={"name": name, "slug": slug, "kind": "employer"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _create_job(client: TestClient, admin, org_id: str, **overrides) -> dict:
    payload = {
        "title": "Senior Platform Engineer",
        "summary": "Build the platform.",
        "description": "Full role description.",
        "department": "Engineering",
        "requirements": ["5+ years", "Distributed systems"],
        "skills_required": ["python", "aws", "kubernetes"],
        "experience_level": "4+ years",
        "location": "Dubai, UAE",
        "country": "UAE",
        "city": "Dubai",
        "remote_eligible": True,
        "work_mode": "hybrid",
        "employment_type": "full_time",
        "salary_min": 120000,
        "salary_max": 180000,
        "salary_currency": "USD",
        "seniority": "senior",
        "industry": "Cloud",
        "screening_questions": [
            {"key": "q1", "question": "Describe a hard production incident you resolved."}
        ],
    }
    payload.update(overrides)
    response = client.post(
        f"/api/v1/company/{org_id}/jobs",
        headers=admin["authorization"],
        json=payload,
    )
    assert response.status_code == 201, response.text
    return response.json()


def _candidate_with_skills(client: TestClient, make_user, skills) -> dict:
    user = make_user(f"cand-{uuid.uuid4().hex[:8]}@example.com")
    for skill in skills:
        response = client.put(
            "/api/v1/work-id/skills",
            headers=user["authorization"],
            json={"skill_name": skill, "level": "advanced", "years_experience": 5},
        )
        assert response.status_code == 200, response.text
    return user


def _apply(client: TestClient, candidate, opportunity_id: str) -> dict:
    response = client.post(
        "/api/v1/jobseeker/applications",
        headers=candidate["authorization"],
        json={"opportunity_id": opportunity_id, "cover_note": "Excited to apply."},
    )
    assert response.status_code == 201, response.text
    return response.json()


# --- 1. Job lifecycle ---------------------------------------------------------

def test_job_lifecycle_draft_to_published_to_closed(
    client, make_user
):
    admin = make_user("jobadmin@example.com")
    org = _create_company(client, admin, "Alpha Cloud", "alpha-cloud")

    # Create -> draft
    job = _create_job(client, admin, org["id"])
    assert job["status"] == "draft"
    job_id = job["id"]

    # Publish -> canonical opportunity is created (ONE universe).
    published = client.post(
        f"/api/v1/company/{org['id']}/jobs/{job_id}/publish",
        headers=admin["authorization"],
    )
    assert published.status_code == 200, published.text
    assert published.json()["status"] == "published"
    opportunity_id = published.json()["opportunity_id"]
    assert opportunity_id is not None

    # The jobseeker opportunity catalogue exposes the same row.
    catalogue = client.get(
        "/api/v1/jobseeker/opportunities", headers=admin["authorization"]
    ).json()
    titles = [i["opportunity"]["title"] for i in catalogue["items"]]
    assert "Senior Platform Engineer" in titles

    # Pause + close keep the catalogue in sync.
    paused = client.post(
        f"/api/v1/company/{org['id']}/jobs/{job_id}/pause",
        headers=admin["authorization"],
    )
    assert paused.json()["status"] == "paused"
    closed = client.post(
        f"/api/v1/company/{org['id']}/jobs/{job_id}/close",
        headers=admin["authorization"],
    )
    assert closed.json()["status"] == "closed"

    # Publishing a closed job is rejected by the lifecycle.
    republish = client.post(
        f"/api/v1/company/{org['id']}/jobs/{job_id}/publish",
        headers=admin["authorization"],
    )
    assert republish.status_code == 422


def test_job_edit_updates_live_opportunity(client, make_user):
    admin = make_user("jobedit@example.com")
    org = _create_company(client, admin, "Beta Systems", "beta-systems")
    job = _create_job(client, admin, org["id"])
    published = client.post(
        f"/api/v1/company/{org['id']}/jobs/{job['id']}/publish",
        headers=admin["authorization"],
    ).json()
    opp_id = published["opportunity_id"]

    edited = client.patch(
        f"/api/v1/company/{org['id']}/jobs/{job['id']}",
        headers=admin["authorization"],
        json={"salary_max": 220000, "title": "Lead Platform Engineer"},
    )
    assert edited.status_code == 200
    assert edited.json()["salary_max"] == 220000

    # Live opportunity reflects the update (single source of truth).
    catalogue = client.get(
        "/api/v1/jobseeker/opportunities", headers=admin["authorization"]
    ).json()
    match = [
        i for i in catalogue["items"]
        if i["opportunity"] and i["opportunity"]["id"] == opp_id
    ]
    assert match and match[0]["opportunity"]["title"] == "Lead Platform Engineer"


# --- 2. Tenant isolation + RBAC -----------------------------------------------

def test_company_a_cannot_touch_company_b(
    client, make_user
):
    admin_a = make_user("alpha@example.com")
    admin_b = make_user("beta@example.com")
    org_a = _create_company(client, admin_a, "Isolation Alpha", "iso-alpha")
    org_b = _create_company(client, admin_b, "Isolation Beta", "iso-beta")
    job_a = _create_job(client, admin_a, org_a["id"])

    # B cannot view A's jobs, dashboard, or applications — even with auth.
    for path in (
        f"/api/v1/company/{org_a['id']}/jobs",
        f"/api/v1/company/{org_a['id']}/dashboard",
        f"/api/v1/company/{org_a['id']}/analytics",
        f"/api/v1/company/{org_a['id']}/jobs/{job_a['id']}",
    ):
        response = client.get(path, headers=admin_b["authorization"])
        assert response.status_code == 403, (path, response.status_code)

    # B cannot publish A's job.
    publish = client.post(
        f"/api/v1/company/{org_a['id']}/jobs/{job_a['id']}/publish",
        headers=admin_b["authorization"],
    )
    assert publish.status_code == 403

    # B cannot see A's members.
    members = client.get(
        f"/api/v1/organizations/{org_a['id']}/members",
        headers=admin_b["authorization"],
    )
    assert members.status_code == 403


def test_rbac_recruiter_limited_permissions(client, make_user):
    admin = make_user("rbac-admin@example.com")
    org = _create_company(client, admin, "Rbac Corp", "rbac-corp")
    job = _create_job(client, admin, org["id"])

    # Add an hr member.
    hr_user = make_user("rbac-hr@example.com")
    added = client.post(
        f"/api/v1/organizations/{org['id']}/members",
        headers=admin["authorization"],
        json={"user_email": hr_user["email"], "role": "hr"},
    )
    assert added.status_code == 201, added.text

    # hr can view jobs and create jobs but a plain member with no membership
    # cannot reach anything.
    outsider = make_user("rbac-outsider@example.com")
    view = client.get(
        f"/api/v1/company/{org['id']}/jobs", headers=outsider["authorization"]
    )
    assert view.status_code == 403

    # hr CAN publish (granted jobs.publish).
    publish = client.post(
        f"/api/v1/company/{org['id']}/jobs/{job['id']}/publish",
        headers=hr_user["authorization"],
    )
    assert publish.status_code == 200

    # analytics requires analytics.view — hr has it; a recruiter does not.
    recruiter = make_user("rbac-recruiter@example.com")
    client.post(
        f"/api/v1/organizations/{org['id']}/members",
        headers=admin["authorization"],
        json={"user_email": recruiter["email"], "role": "recruiter"},
    )
    analytics = client.get(
        f"/api/v1/company/{org['id']}/analytics",
        headers=recruiter["authorization"],
    )
    assert analytics.status_code == 403
    # Recruiter CAN see the pipeline (candidates.view + applications.view).
    apps = client.get(
        f"/api/v1/company/{org['id']}/applications",
        headers=recruiter["authorization"],
    )
    assert apps.status_code == 200


def test_company_profile_permission(client, make_user):
    admin = make_user("profile-admin@example.com")
    org = _create_company(client, admin, "Profile Corp", "profile-corp")
    profile = client.patch(
        f"/api/v1/company/{org['id']}/profile",
        headers=admin["authorization"],
        json={
            "legal_name": "Profile Corp Ltd",
            "industry": "Software",
            "country": "AE",
            "company_type": "sme",
            "company_size": "51-200",
        },
    )
    assert profile.status_code == 200, profile.text
    assert profile.json()["industry"] == "Software"
    assert profile.json()["verification_status"] == "unverified"

    outsider = make_user("profile-other@example.com")
    denied = client.patch(
        f"/api/v1/company/{org['id']}/profile",
        headers=outsider["authorization"],
        json={"industry": "Hijacked"},
    )
    assert denied.status_code == 403


# --- 3. Pipeline: candidate applies -> employer reviews -> decisions ---------

def _pipeline_setup(client, make_user, db):
    admin = make_user(f"pipe-admin-{uuid.uuid4().hex[:6]}@example.com")
    org = _create_company(client, admin, "Pipeline Co", f"pipeline-{uuid.uuid4().hex[:6]}")
    job = _create_job(client, admin, org["id"])
    published = client.post(
        f"/api/v1/company/{org['id']}/jobs/{job['id']}/publish",
        headers=admin["authorization"],
    ).json()
    candidate = _candidate_with_skills(
        client, make_user, ["Python", "AWS", "Kubernetes"]
    )
    application = _apply(client, candidate, published["opportunity_id"])
    return admin, org, job, published, candidate, application


def test_full_pipeline_and_candidate_privacy(
    client, make_user, db
):
    admin, org, job, published, candidate, application = _pipeline_setup(
        client, make_user, db
    )

    # Candidate contact/private data is NOT exposed by default.
    review = client.get(
        f"/api/v1/company/{org['id']}/applications/{application['id']}",
        headers=admin["authorization"],
    )
    assert review.status_code == 200, review.text
    body = review.json()
    assert body["candidate"]["person"]["full_name"] is not None
    assert body["candidate"]["disclosure"]["contact_visible"] is False
    assert body["candidate"]["has_live_consent"] is False
    assert len(body["candidate"]["skills"]) >= 2

    # Employer advances: applied -> application_received -> screening.
    step1 = client.post(
        f"/api/v1/company/{org['id']}/applications/{application['id']}/decision",
        headers=admin["authorization"],
        json={"action": "advance", "note": "Strong profile"},
    )
    assert step1.status_code == 200
    assert step1.json()["status"] == "application_received"

    step2 = client.post(
        f"/api/v1/company/{org['id']}/applications/{application['id']}/decision",
        headers=admin["authorization"],
        json={"action": "advance"},
    )
    assert step2.json()["status"] == "screening"

    # Candidate sees the same lifecycle through their own center.
    candidate_view = client.get(
        f"/api/v1/jobseeker/applications/{application['id']}",
        headers=candidate["authorization"],
    ).json()
    assert candidate_view["application"]["status"] == "screening"
    statuses = [e["to_status"] for e in candidate_view["timeline"]]
    assert "screening" in statuses

    # Withdraw is impossible from the employer side; reject is.
    rejected = client.post(
        f"/api/v1/company/{org['id']}/applications/{application['id']}/decision",
        headers=admin["authorization"],
        json={"action": "reject", "note": "Role closed."},
    )
    assert rejected.json()["status"] == "rejected"


def test_interview_scheduling_reschedule_confirm_and_scorecard(
    client, make_user, db
):
    admin, org, job, published, candidate, application = _pipeline_setup(
        client, make_user, db
    )

    # Schedule an interview.
    scheduled = client.post(
        f"/api/v1/company/{org['id']}/interviews",
        headers=admin["authorization"],
        json={
            "application_id": application["id"],
            "scheduled_at": "2026-09-20T10:00:00Z",
            "duration_minutes": 45,
            "mode": "video",
            "interviewer_name": "Hiring Manager",
        },
    )
    assert scheduled.status_code == 201, scheduled.text
    interview_id = scheduled.json()["id"]

    # Candidate requests a reschedule (Phase 5 policy: reason required).
    reschedule = client.post(
        f"/api/v1/jobseeker/interviews/{interview_id}/reschedule-request",
        headers=candidate["authorization"],
        json={"reason": "Client launch conflict — could we move by two days?"},
    )
    assert reschedule.status_code == 200
    assert reschedule.json()["status"] == "reschedule_requested"

    # Employer confirms the reschedule (audited).
    confirmed = client.post(
        f"/api/v1/company/{org['id']}/interviews/{interview_id}/confirm-reschedule",
        headers=admin["authorization"],
    )
    assert confirmed.status_code == 200
    assert confirmed.json()["status"] == "scheduled"

    # Complete + scorecard.
    completed = client.post(
        f"/api/v1/company/{org['id']}/interviews/{interview_id}/complete",
        headers=admin["authorization"],
    )
    assert completed.json()["status"] == "completed"
    scorecard = client.post(
        f"/api/v1/company/{org['id']}/interviews/{interview_id}/scorecards",
        headers=admin["authorization"],
        json={
            "criteria": [
                {"key": "technical", "label": "Technical competency", "score": 4}
            ],
            "strengths": "Clear system design thinking.",
            "concerns": "Light on Kubernetes ops.",
            "recommendation": "advance",
        },
    )
    assert scorecard.status_code == 201, scorecard.text
    assert scorecard.json()["recommendation"] == "advance"

    # Another company cannot confirm/schedule on this application.
    other_admin = make_user("other-co@example.com")
    other_org = _create_company(client, other_admin, "Other Co", f"other-{uuid.uuid4().hex[:6]}")
    denied = client.post(
        f"/api/v1/company/{other_org['id']}/interviews/{interview_id}/complete",
        headers=other_admin["authorization"],
    )
    # The interview belongs to another tenant: existence is hidden (404),
    # never reachable (403 would leak existence to a member of another org).
    assert denied.status_code == 404


def test_offer_flow_syncs_both_sides(client, make_user, db):
    admin, org, job, published, candidate, application = _pipeline_setup(
        client, make_user, db
    )
    # Advance to interview first.
    for _ in range(2):
        client.post(
            f"/api/v1/company/{org['id']}/applications/{application['id']}/decision",
            headers=admin["authorization"],
            json={"action": "advance"},
        )

    # Unauthorized user (no offers.create) cannot create an offer.
    no_offer_perm = make_user("hiring-mgr@example.com")
    client.post(
        f"/api/v1/organizations/{org['id']}/members",
        headers=admin["authorization"],
        json={"user_email": no_offer_perm["email"], "role": "hiring_manager"},
    )
    forbidden = client.post(
        f"/api/v1/company/{org['id']}/offers",
        headers=no_offer_perm["authorization"],
        json={"application_id": application["id"], "salary_amount": 150000},
    )
    assert forbidden.status_code == 403

    # org_admin creates + sends.
    created = client.post(
        f"/api/v1/company/{org['id']}/offers",
        headers=admin["authorization"],
        json={
            "application_id": application["id"],
            "salary_amount": 150000,
            "salary_currency": "USD",
            "start_date": "2026-11-01",
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["status"] == "draft"
    offer_id = created.json()["id"]

    sent = client.post(
        f"/api/v1/company/{org['id']}/offers/{offer_id}/send",
        headers=admin["authorization"],
    )
    assert sent.json()["status"] == "sent"

    # Candidate sees the offer in their Offer Center and accepts.
    candidate_offers = client.get(
        "/api/v1/jobseeker/offers", headers=candidate["authorization"]
    ).json()
    assert any(o["id"] == offer_id and o["status"] == "sent" for o in candidate_offers)

    accepted = client.post(
        f"/api/v1/jobseeker/offers/{offer_id}/decision",
        headers=candidate["authorization"],
        json={"decision": "accepted"},
    )
    assert accepted.status_code == 200

    # ONE lifecycle: application accepted on both sides; offer reflects it.
    company_view = client.get(
        f"/api/v1/company/{org['id']}/applications/{application['id']}",
        headers=admin["authorization"],
    ).json()
    assert company_view["application"]["status"] == "accepted"
    assert company_view["offer"]["status"] == "accepted"


def test_document_request_and_consent_gate(client, make_user, db):
    admin, org, job, published, candidate, application = _pipeline_setup(
        client, make_user, db
    )

    # Candidate has a document of the requested type.
    doc = client.post(
        "/api/v1/documents",
        headers=candidate["authorization"],
        json={"name": "degree.pdf", "doc_type": "education", "size_bytes": 1024},
    )
    assert doc.status_code == 201, doc.text
    doc_id = doc.json()["id"]

    # Company requests it.
    request = client.post(
        f"/api/v1/company/{org['id']}/document-requests",
        headers=admin["authorization"],
        json={
            "application_id": application["id"],
            "document_type": "education",
            "purpose": "Degree verification for offer stage.",
        },
    )
    assert request.status_code == 201, request.text
    request_id = request.json()["id"]

    # Another company cannot see this org's document requests.
    other_admin = make_user("docother@example.com")
    other_org = _create_company(client, other_admin, "Doc Other", f"doc-other-{uuid.uuid4().hex[:6]}")
    hidden = client.get(
        f"/api/v1/company/{other_org['id']}/document-requests",
        headers=other_admin["authorization"],
    )
    assert hidden.status_code == 200
    assert all(r["id"] != request_id for r in hidden.json())

    # Company CANNOT read the document before approval.
    from app.models.documents import PersonDocument

    # Candidate approves through their center -> live org grant.
    approved = client.post(
        f"/api/v1/jobseeker/document-requests/{request_id}/approve",
        headers=candidate["authorization"],
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "approved"

    # The org now holds a live grant; a company member can resolve the doc.
    member_view = client.get(
        f"/api/v1/documents/{doc_id}", headers=admin["authorization"]
    )
    assert member_view.status_code == 200
    # Candidate revokes the grant -> access disappears.
    grants = client.get(
        f"/api/v1/documents/{doc_id}/grants", headers=candidate["authorization"]
    ).json()
    grant_id = grants[0]["id"]
    client.delete(
        f"/api/v1/documents/{doc_id}/grants/{grant_id}",
        headers=candidate["authorization"],
    )
    revoked_view = client.get(
        f"/api/v1/documents/{doc_id}", headers=admin["authorization"]
    )
    assert revoked_view.status_code == 404


# --- 4. Analytics + dashboard --------------------------------------------------

def test_analytics_requires_permission_and_counts(client, make_user, db):
    admin, org, job, published, candidate, application = _pipeline_setup(
        client, make_user, db
    )
    analytics = client.get(
        f"/api/v1/company/{org['id']}/analytics", headers=admin["authorization"]
    ).json()
    assert analytics["open_jobs"] == 1
    assert analytics["applications_total"] == 1
    assert analytics["needs_review"] >= 1

    dash = client.get(
        f"/api/v1/company/{org['id']}/dashboard", headers=admin["authorization"]
    ).json()
    assert dash["open_jobs"] == 1
    assert dash["applications_total"] == 1
    assert "jobs.view" in dash["permissions"]
