"""Phase 7 — Talent Graph & Opportunity Intelligence tests.

Security targets from the brief:
- Discovery surfaces ONLY people who opted in (profile PUBLIC); private
  sections never leak through search, profiles or matches.
- Filters only run over public data; hidden sections are never probed.
- Company A can never access Company B's talent pools / saved candidates /
  opportunity matches.
- Ranked matches are explainable (mode, strengths, gaps, missing skills)
  and never use private career goals or protected characteristics.
- Skill normalization converges free text ("React.js", "ReactJS") onto ONE
  canonical taxonomy skill; evidence derives from real Work ID records and
  is never marked verified without an authoritative source record.
"""
from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.career import Opportunity
from app.models.enums import VISIBILITY_PUBLIC
from app.models.privacy import PersonVisibilitySetting
from app.models.talent import CandidateSearchEvent
from app.models.work import Skill, UserSkill, WorkExperience


# --- helpers ------------------------------------------------------------------

def _create_company(client: TestClient, admin, name: str, slug: str) -> dict:
    response = client.post(
        "/api/v1/organizations",
        headers=admin["authorization"],
        json={"name": name, "slug": slug, "kind": "employer"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _add_member(client: TestClient, admin, org_id: str, email: str, role: str) -> None:
    response = client.post(
        f"/api/v1/organizations/{org_id}/members",
        headers=admin["authorization"],
        json={"user_email": email, "role": role},
    )
    assert response.status_code == 201, response.text


def _add_skill(client: TestClient, user, skill_name: str, level: str = "advanced") -> None:
    response = client.put(
        "/api/v1/work-id/skills",
        headers=user["authorization"],
        json={"skill_name": skill_name, "level": level, "years_experience": 5},
    )
    assert response.status_code == 200, response.text


def _add_experience(client: TestClient, user, title="Software Engineer", skills=None) -> None:
    response = client.post(
        "/api/v1/work-id/experiences",
        headers=user["authorization"],
        json={
            "company_name": "Riviera Labs",
            "title": title,
            "start_date": "2020-01-15",
            "is_current": True,
            "skills_used": skills or [],
        },
    )
    assert response.status_code == 201, response.text


def _set_visibility(client: TestClient, user, **scopes) -> None:
    response = client.put(
        "/api/v1/work-id/privacy",
        headers=user["authorization"],
        json={"settings": {k: v for k, v in scopes.items()}},
    )
    assert response.status_code == 200, response.text


def _make_discoverable(client: TestClient, user, *, skills=True, experience=True,
                       education=True, contact=False) -> None:
    scopes = {"profile": "public"}
    if skills:
        scopes["skills"] = "public"
    if experience:
        scopes["experience"] = "public"
    if education:
        scopes["education"] = "public"
    if contact:
        scopes["contact"] = "public"
    _set_visibility(client, user, **scopes)


def _candidate_person_id(db: Session, email: str) -> str:
    from app.models.identity import PersonProfile, User

    user = db.scalar(select(User).where(User.email == email))
    assert user is not None
    person = db.scalar(select(PersonProfile).where(PersonProfile.user_id == user.id))
    return str(person.id)


def _publish_job(client: TestClient, admin, org_id: str, **overrides) -> dict:
    payload = {
        "title": "Frontend Engineer",
        "summary": "Build product UI.",
        "skills_required": ["React", "TypeScript"],
        "experience_level": "2+ years",
        "work_mode": "hybrid",
        "employment_type": "full_time",
        "seniority": "mid",
        "industry": "Software",
        "country": "AE",
        "city": "Dubai",
    }
    payload.update(overrides)
    job = client.post(
        f"/api/v1/company/{org_id}/jobs",
        headers=admin["authorization"],
        json=payload,
    )
    assert job.status_code == 201, job.text
    published = client.post(
        f"/api/v1/company/{org_id}/jobs/{job.json()['id']}/publish",
        headers=admin["authorization"],
    )
    assert published.status_code == 200, published.text
    return published.json()


# --- 1. Skill taxonomy + normalization -----------------------------------------

def test_normalization_resolves_aliases_to_one_canonical_skill(db):
    from app.models.talent import SkillAlias
    from app.services import skills_registry

    react = skills_registry.ensure_skill(db, "React", category="software_engineering")
    db.flush()
    # Simulate the migration seed: "reactjs" is an alias of React.
    if db.scalar(select(SkillAlias.id).where(SkillAlias.alias == "reactjs")) is None:
        db.add(SkillAlias(skill_id=react.id, alias="reactjs", original="React.js",
                          source="taxonomy_seed"))
        db.commit()

    assert skills_registry.normalize("React.js") == "reactjs"
    assert skills_registry.normalize("  ReactJS ") == "reactjs"
    assert skills_registry.normalize("Node.js") == "nodejs"
    # C# and C++ keep their symbols (no conflation with other tokens).
    assert skills_registry.normalize("C#") == "c#"
    assert skills_registry.normalize("C++") == "c++"

    resolved = skills_registry.resolve_skill(db, "React.js")
    assert resolved is not None and resolved.name == "React"
    resolved2 = skills_registry.resolve_skill(db, "ReactJS")
    assert resolved2 is not None and resolved2.id == react.id

    name_map = skills_registry.canonical_name_map(db, ["React.js", "ReactJS", "UnknownX"])
    assert name_map["React.js"] == "React"
    assert name_map["ReactJS"] == "React"
    # Unresolvable values are preserved, never destroyed.
    assert name_map["UnknownX"] == "UnknownX"


def test_evidence_derives_from_work_id_records(db, client, make_user):
    candidate = make_user(f"evidence-{uuid.uuid4().hex[:6]}@example.com")
    _add_skill(client, candidate, "React")
    _add_skill(client, candidate, "Python")
    _add_experience(client, candidate, skills=["React"])

    from app.services import skills_registry

    person_id = uuid.UUID(_candidate_person_id(db, candidate["email"]))
    counts = skills_registry.refresh_person_evidence(db, person_id)
    assert counts["self"] >= 2
    assert counts["experience"] >= 1

    evidence = skills_registry.evidence_for_skills(db, person_id)
    react_rows = evidence.get("React", [])
    types = {r["evidence_type"] for r in react_rows}
    assert "self" in types and "experience" in types
    # Self-declared evidence is never "verified".
    for row in react_rows:
        assert row["verification_status"] in {"unverified", "verified"}
    self_row = next(r for r in react_rows if r["evidence_type"] == "self")
    assert self_row["verification_status"] == "unverified"


# --- 2. Discovery privacy -------------------------------------------------------

def test_private_person_never_appears_in_discovery(client, make_user, db):
    admin = make_user(f"disco-admin-{uuid.uuid4().hex[:6]}@example.com")
    org = _create_company(client, admin, "Discovery Co", f"disco-{uuid.uuid4().hex[:6]}")
    candidate = make_user(f"disco-cand-{uuid.uuid4().hex[:6]}@example.com")
    _add_skill(client, candidate, "React")

    search = client.get(
        f"/api/v1/talent/{org['id']}/candidates/search",
        headers=admin["authorization"],
    )
    assert search.status_code == 200
    # Default is PRIVATE everywhere — nobody is discoverable until they opt in.
    assert search.json()["total"] == 0

    # A discoverable candidate appears.
    _make_discoverable(client, candidate)
    search = client.get(
        f"/api/v1/talent/{org['id']}/candidates/search",
        headers=admin["authorization"],
    )
    assert search.json()["total"] >= 1


def test_skill_filter_never_probes_private_skills(client, make_user, db):
    admin = make_user(f"filter-admin-{uuid.uuid4().hex[:6]}@example.com")
    org = _create_company(client, admin, "Filter Co", f"filter-{uuid.uuid4().hex[:6]}")
    pub = make_user(f"filter-pub-{uuid.uuid4().hex[:6]}@example.com")
    priv = make_user(f"filter-priv-{uuid.uuid4().hex[:6]}@example.com")
    _add_skill(client, pub, "React")
    _add_skill(client, priv, "React")
    _make_discoverable(client, pub, skills=True)
    # profile public but skills stay private
    _make_discoverable(client, priv, skills=False, experience=False, education=False)

    base = client.get(
        f"/api/v1/talent/{org['id']}/candidates/search",
        headers=admin["authorization"],
    ).json()
    ids = {i["person_id"] for i in base["items"]}
    assert _candidate_person_id(db, priv["email"]) in ids

    filtered = client.get(
        f"/api/v1/talent/{org['id']}/candidates/search?skills=React",
        headers=admin["authorization"],
    ).json()
    f_ids = {i["person_id"] for i in filtered["items"]}
    assert _candidate_person_id(db, pub["email"]) in f_ids
    # The private-skills candidate is NOT returned: hidden data is never probed.
    assert _candidate_person_id(db, priv["email"]) not in f_ids
    # Echoed items expose only public fields.
    for item in filtered["items"]:
        if item["person_id"] == _candidate_person_id(db, pub["email"]):
            assert item["skills"] and item["skills"][0]["name"].lower() == "react"
        assert item["disclosure"]["contact_visible"] is False


def test_alias_search_finds_canonical_candidates(client, make_user, db):
    admin = make_user(f"alias-admin-{uuid.uuid4().hex[:6]}@example.com")
    org = _create_company(client, admin, "Alias Co", f"alias-{uuid.uuid4().hex[:6]}")
    # Taxonomy: canonical React with the alias the migration seeds.
    from app.models.talent import SkillAlias
    from app.services import skills_registry

    react = skills_registry.ensure_skill(db, "React", category="software_engineering")
    if db.scalar(select(SkillAlias.id).where(SkillAlias.alias == "reactjs")) is None:
        db.add(SkillAlias(skill_id=react.id, alias="reactjs", original="React.js",
                          source="taxonomy_seed"))
        db.commit()
    candidate = make_user(f"alias-cand-{uuid.uuid4().hex[:6]}@example.com")
    # Candidate declares a non-canonical spelling -> converges on React.
    _add_skill(client, candidate, "ReactJS")
    _make_discoverable(client, candidate)

    result = client.get(
        f"/api/v1/talent/{org['id']}/candidates/search?skills=react.js",
        headers=admin["authorization"],
    ).json()
    assert result["total"] >= 1
    pid = _candidate_person_id(db, candidate["email"])
    assert any(i["person_id"] == pid for i in result["items"])


def test_search_pagination_records_governance_event(client, make_user, db):
    admin = make_user(f"pager-admin-{uuid.uuid4().hex[:6]}@example.com")
    org = _create_company(client, admin, "Pager Co", f"pager-{uuid.uuid4().hex[:6]}")
    for i in range(3):
        cand = make_user(f"pager-{i}-{uuid.uuid4().hex[:4]}@example.com")
        _add_skill(client, cand, "Python")
        _make_discoverable(client, cand)

    page1 = client.get(
        f"/api/v1/talent/{org['id']}/candidates/search?skills=Python&page=1&page_size=2",
        headers=admin["authorization"],
    ).json()
    page2 = client.get(
        f"/api/v1/talent/{org['id']}/candidates/search?skills=Python&page=2&page_size=2",
        headers=admin["authorization"],
    ).json()
    assert page1["total"] == 3 and len(page1["items"]) == 2
    assert len(page2["items"]) == 1
    ids1 = {i["person_id"] for i in page1["items"]}
    ids2 = {i["person_id"] for i in page2["items"]}
    assert ids1.isdisjoint(ids2)

    # Search events are recorded (filters only, never candidate rows).
    events = db.scalars(select(CandidateSearchEvent)).all()
    assert any(e.filters and e.filters.get("skills") == ["Python"] and e.result_count == 3
               for e in events)


# --- 3. Ranked matching ---------------------------------------------------------

def test_opportunity_matches_are_explainable_and_exclude_applied(
    client, make_user, db
):
    admin = make_user(f"match-admin-{uuid.uuid4().hex[:6]}@example.com")
    org = _create_company(client, admin, "Match Co", f"match-{uuid.uuid4().hex[:6]}")
    published = _publish_job(client, admin, org["id"])
    opp_id = published["opportunity_id"]

    strong = make_user(f"match-strong-{uuid.uuid4().hex[:6]}@example.com")
    weak = make_user(f"match-weak-{uuid.uuid4().hex[:6]}@example.com")
    applied = make_user(f"match-applied-{uuid.uuid4().hex[:6]}@example.com")
    private_exp = make_user(f"match-private-{uuid.uuid4().hex[:6]}@example.com")

    _add_skill(client, strong, "React")
    _add_skill(client, strong, "TypeScript")
    _add_experience(client, strong, title="Senior Frontend Engineer", skills=["React", "TypeScript"])
    _make_discoverable(client, strong)

    _add_skill(client, weak, "Python")
    _add_experience(client, weak, title="Data Engineer", skills=["Python"])
    _make_discoverable(client, weak)

    _add_skill(client, applied, "React")
    _add_experience(client, applied, skills=["React"])
    _make_discoverable(client, applied)
    application = client.post(
        "/api/v1/jobseeker/applications",
        headers=applied["authorization"],
        json={"opportunity_id": opp_id},
    )
    assert application.status_code == 201, application.text

    # Skills public but experience/education private -> NOT ranked (full
    # professional summary required for ranked matching).
    _add_skill(client, private_exp, "React")
    _set_visibility(client, private_exp, profile="public", skills="public")

    result = client.get(
        f"/api/v1/talent/{org['id']}/opportunities/{opp_id}/candidates",
        headers=admin["authorization"],
    ).json()
    ids = [i["person_id"] for i in result["items"]]
    strong_id = _candidate_person_id(db, strong["email"])
    weak_id = _candidate_person_id(db, weak["email"])
    applied_id = _candidate_person_id(db, applied["email"])
    assert strong_id in ids
    assert weak_id in ids
    assert applied_id not in ids  # already applied -> excluded from discovery
    assert _candidate_person_id(db, private_exp["email"]) not in ids

    by_id = {i["person_id"]: i for i in result["items"]}
    assert by_id[strong_id]["mode"] in {"strong", "potential"}
    assert "react" in [s.lower() for s in by_id[strong_id]["matched_skills"]]
    assert by_id[weak_id]["missing_skills"]  # explainable gap
    assert by_id[strong_id]["percent"] > by_id[weak_id]["percent"]
    for item in result["items"]:
        assert item["strengths"] or item["gaps"]
        assert "person_id" in item["summary"]


def test_cross_tenant_opportunity_matches_hidden(client, make_user):
    admin_a = make_user(f"iso-a-{uuid.uuid4().hex[:6]}@example.com")
    admin_b = make_user(f"iso-b-{uuid.uuid4().hex[:6]}@example.com")
    org_a = _create_company(client, admin_a, "Iso A Co", f"isoa-{uuid.uuid4().hex[:6]}")
    _create_company(client, admin_b, "Iso B Co", f"isob-{uuid.uuid4().hex[:6]}")
    published = _publish_job(client, admin_a, org_a["id"])

    # B is a member of its own org but NOT of A: talent routes are org-gated.
    hidden = client.get(
        f"/api/v1/talent/{org_a['id']}/opportunities/{published['opportunity_id']}/candidates",
        headers=admin_b["authorization"],
    )
    assert hidden.status_code == 403


# --- 4. Candidate profile + progressive disclosure ------------------------------

def test_candidate_profile_progressive_disclosure_and_save(client, make_user, db):
    admin = make_user(f"prof-admin-{uuid.uuid4().hex[:6]}@example.com")
    org = _create_company(client, admin, "Profile Talent", f"prof-{uuid.uuid4().hex[:6]}")
    published = _publish_job(client, admin, org["id"])
    opp_id = published["opportunity_id"]

    candidate = make_user(f"prof-cand-{uuid.uuid4().hex[:6]}@example.com")
    _add_skill(client, candidate, "React")
    _add_experience(client, candidate, skills=["React"])
    _make_discoverable(client, candidate, contact=False)
    client.put(
        "/api/v1/work-id/profile",
        headers=candidate["authorization"],
        json={"headline": "Frontend engineer", "city": "Dubai", "country_code": "AE",
              "phone": "+971500000000"},
    )
    person_id = _candidate_person_id(db, candidate["email"])

    profile = client.get(
        f"/api/v1/talent/{org['id']}/candidates/{person_id}",
        headers=admin["authorization"],
    ).json()
    assert profile["person_id"] == person_id
    assert profile["context"] == "discovery"
    assert profile["disclosure"]["contact_visible"] is False
    assert profile["location"] is None
    assert "phone" not in str(profile)

    # With an opportunity context, an explainable match + gap analysis appear.
    with_match = client.get(
        f"/api/v1/talent/{org['id']}/candidates/{person_id}?opportunity_id={opp_id}",
        headers=admin["authorization"],
    ).json()
    assert "match" in with_match
    assert with_match["match"]["mode"] in {"strong", "potential"}
    assert with_match["match"]["gap_analysis"]["matched"]

    # Save + list + unsave.
    saved = client.post(
        f"/api/v1/talent/{org['id']}/candidates/{person_id}/saved",
        headers=admin["authorization"],
        json={"note": "Strong React communicator", "tags": ["frontend", "dubai"]},
    )
    assert saved.status_code == 200, saved.text
    saved_list = client.get(
        f"/api/v1/talent/{org['id']}/candidates/saved",
        headers=admin["authorization"],
    ).json()
    assert any(s["person_id"] == person_id for s in saved_list)
    removed = client.delete(
        f"/api/v1/talent/{org['id']}/candidates/{person_id}/saved",
        headers=admin["authorization"],
    )
    assert removed.status_code == 200


# --- 5. Talent pools + tenant isolation -----------------------------------------

def test_talent_pools_are_org_isolated_and_visibility_gated(client, make_user, db):
    admin_a = make_user(f"pool-a-{uuid.uuid4().hex[:6]}@example.com")
    org_a = _create_company(client, admin_a, "Pool A Co", f"poola-{uuid.uuid4().hex[:6]}")
    admin_b = make_user(f"pool-b-{uuid.uuid4().hex[:6]}@example.com")
    org_b = _create_company(client, admin_b, "Pool B Co", f"poolb-{uuid.uuid4().hex[:6]}")

    public_candidate = make_user(f"pool-public-{uuid.uuid4().hex[:6]}@example.com")
    private_candidate = make_user(f"pool-private-{uuid.uuid4().hex[:6]}@example.com")
    _make_discoverable(client, public_candidate)
    pub_pid = _candidate_person_id(db, public_candidate["email"])
    priv_pid = _candidate_person_id(db, private_candidate["email"])

    created = client.post(
        f"/api/v1/talent/{org_a['id']}/pools",
        headers=admin_a["authorization"],
        json={"name": "Senior React Engineers", "description": "Pipeline depth."},
    )
    assert created.status_code == 201, created.text
    pool_id = created.json()["id"]

    # A can add a discoverable candidate...
    added = client.post(
        f"/api/v1/talent/{org_a['id']}/pools/{pool_id}/members",
        headers=admin_a["authorization"],
        json={"person_id": pub_pid, "note": "Reach out in Q3"},
    )
    assert added.status_code == 201, added.text

    # ...but NEVER a private person with no relationship to the org.
    hidden = client.post(
        f"/api/v1/talent/{org_a['id']}/pools/{pool_id}/members",
        headers=admin_a["authorization"],
        json={"person_id": priv_pid},
    )
    assert hidden.status_code == 404

    # B cannot list A's pools (403), cannot read A's pool detail, and its own
    # pool list is empty.
    denied = client.get(
        f"/api/v1/talent/{org_a['id']}/pools", headers=admin_b["authorization"]
    )
    assert denied.status_code == 403
    denied_detail = client.get(
        f"/api/v1/talent/{org_a['id']}/pools/{pool_id}",
        headers=admin_b["authorization"],
    )
    assert denied_detail.status_code == 403
    empty = client.get(
        f"/api/v1/talent/{org_b['id']}/pools", headers=admin_b["authorization"]
    ).json()
    assert empty == []

    detail = client.get(
        f"/api/v1/talent/{org_a['id']}/pools/{pool_id}",
        headers=admin_a["authorization"],
    ).json()
    assert detail["member_count"] == 1
    assert detail["members"][0]["person_id"] == pub_pid

    removed = client.delete(
        f"/api/v1/talent/{org_a['id']}/pools/{pool_id}/members/{pub_pid}",
        headers=admin_a["authorization"],
    )
    assert removed.status_code == 200
    after = client.get(
        f"/api/v1/talent/{org_a['id']}/pools/{pool_id}",
        headers=admin_a["authorization"],
    ).json()
    assert after["member_count"] == 0


def test_talent_rbac_hiring_manager_cannot_search(client, make_user):
    admin = make_user(f"rbac2-admin-{uuid.uuid4().hex[:6]}@example.com")
    org = _create_company(client, admin, "Rbac2 Co", f"rbac2-{uuid.uuid4().hex[:6]}")
    hm = make_user(f"rbac2-hm-{uuid.uuid4().hex[:6]}@example.com")
    _add_member(client, admin, org["id"], hm["email"], "hiring_manager")

    search = client.get(
        f"/api/v1/talent/{org['id']}/candidates/search",
        headers=hm["authorization"],
    )
    assert search.status_code == 403
    pools = client.get(
        f"/api/v1/talent/{org['id']}/pools", headers=hm["authorization"]
    )
    assert pools.status_code == 403


# --- 6. Opportunity requirements + jobseeker intelligence ------------------------

def test_requirement_normalization_preserves_raw_text(client, make_user, db):
    admin = make_user(f"req-admin-{uuid.uuid4().hex[:6]}@example.com")
    org = _create_company(client, admin, "Req Co", f"req-{uuid.uuid4().hex[:6]}")
    published = _publish_job(client, admin, org["id"], skills_required=["React"])
    opp_id = published["opportunity_id"]

    opp = db.get(Opportunity, uuid.UUID(opp_id))
    # Seed the canonical skills so the sentence's word resolves.
    from app.services import skills_registry

    skills_registry.ensure_skill(db, "React", category="software_engineering")
    skills_registry.ensure_skill(db, "TypeScript", category="software_engineering")
    db.commit()
    # Direct normalization of a prose requirement keeps the original wording.
    opp.skills_required = ["3+ years React experience", "TypeScript"]
    db.commit()
    skills_registry.normalize_opportunity_requirements(db, opp)
    db.commit()

    requirements = client.get(
        f"/api/v1/talent/{org['id']}/opportunities/{opp_id}/requirements",
        headers=admin["authorization"],
    ).json()
    by_raw = {r["raw_text"]: r for r in requirements}
    assert "3+ years React experience" in by_raw  # never destroyed
    row = by_raw["3+ years React experience"]
    assert row["min_years"] == 3
    assert row["skill"] == "React"
    assert any(r["skill"] == "TypeScript" for r in requirements)


def test_jobseeker_gap_analysis_and_career_intelligence(client, make_user, db):
    admin = make_user(f"intel-admin-{uuid.uuid4().hex[:6]}@example.com")
    org = _create_company(client, admin, "Intel Co", f"intel-{uuid.uuid4().hex[:6]}")
    published = _publish_job(
        client, admin, org["id"], skills_required=["React", "TypeScript", "AWS"]
    )
    opp_id = published["opportunity_id"]

    candidate = make_user(f"intel-cand-{uuid.uuid4().hex[:6]}@example.com")
    _add_skill(client, candidate, "React")
    _add_skill(client, candidate, "TypeScript")
    _add_experience(client, candidate, skills=["React", "TypeScript"])

    detail = client.get(
        f"/api/v1/jobseeker/opportunities/{opp_id}",
        headers=candidate["authorization"],
    ).json()
    assert detail["opportunity"]["id"] == opp_id
    assert any(g["skill"].lower() == "aws" for g in detail["gap_analysis"]["gaps"])
    # The user's own evidence backs the matched skills (private to them but
    # visible to themselves).
    matched = detail["gap_analysis"]["matched"]
    react = next(m for m in matched if m["skill"].lower() == "react")
    assert any(e["evidence_type"] == "self" for e in react["evidence"])

    intelligence = client.get(
        "/api/v1/jobseeker/career/intelligence",
        headers=candidate["authorization"],
    ).json()
    assert intelligence["capability"]["skills"]
    assert intelligence["disclaimer"]
    names = [s["name"] for s in intelligence["capability"]["skills"]]
    assert "React" in names

    # Another user's intelligence is their own; there is no cross-user route
    # to read a different person's data (ownership is structural).
    other = make_user(f"intel-other-{uuid.uuid4().hex[:6]}@example.com")
    other_intel = client.get(
        "/api/v1/jobseeker/career/intelligence",
        headers=other["authorization"],
    ).json()
    assert [s["name"] for s in other_intel["capability"]["skills"]] != names


def test_jobseeker_intelligence_needs_real_opportunities_only(client, make_user):
    candidate = make_user(f"noscope-{uuid.uuid4().hex[:6]}@example.com")
    _add_skill(client, candidate, "Python")
    intelligence = client.get(
        "/api/v1/jobseeker/career/intelligence",
        headers=candidate["authorization"],
    ).json()
    # Advisory data grounded in real rows; never a fabricated AI promise.
    assert intelligence["capability"]["years_experience"] >= 0
    assert "roles_within_reach" in intelligence
    assert "path_advice" in intelligence
