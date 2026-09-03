"""Talent Graph service — candidate discovery, ranked matching, pools and the
jobseeker career-intelligence side of the same graph (Phase 7).

Privacy is the architecture, not a filter:
- Passive discovery ONLY surfaces people who opted in by setting their
  ``profile`` Work ID section to PUBLIC (default is private everywhere).
- Results echo ONLY public sections. Filters (skills, location) are applied
  only against public data: a person whose relevant section is private is
  excluded from that filtered search — hidden data is never probed.
- Ranked opportunity→candidate matching requires the candidate's profile,
  skills, experience AND education sections to be public (a fully
  discoverable professional summary). A person's private career goals are
  NEVER read by employers — jobseeker-side matching is the only consumer of
  goals, and only for their owner.
- Saved candidates and talent pools are organization-scoped; notes stay
  inside the organization. Company A can never read Company B's lists.

Match explanations are deterministic and evidence-grounded. No protected
characteristics, no facial/emotion analysis, no predictive claims — a
"career transition" label means the person's public skills cover only part
of the requirements while their experience suggests adaptability, and the
explanation always says so.
"""
from __future__ import annotations

import uuid
from typing import Dict, List, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import (
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from app.models.career import CareerGoal, JobApplication, Opportunity
from app.models.enums import (
    MATCH_MODE_CAREER_TRANSITION,
    MATCH_MODE_EXPLORE,
    MATCH_MODE_POTENTIAL,
    MATCH_MODE_STRONG,
    USER_STATUS_ACTIVE,
    VISIBILITY_PUBLIC,
)
from app.models.identity import PersonProfile, User
from app.models.privacy import PersonVisibilitySetting
from app.models.talent import (
    CandidateSearchEvent,
    SavedCandidate,
    SkillEvidence,
    TalentPool,
    TalentPoolMember,
)
from app.models.tenancy import Organization
from app.models.work import Education, Skill, UserSkill, WorkExperience
from app.services import matching as matching_service
from app.services import skills_registry

# Work ID sections that form a fully discoverable professional summary.
DISCOVERY_PUBLIC_SCOPES = {"profile", "skills", "experience", "education"}
# Section whose visibility decides passive search membership.
PASSIVE_SCOPE = "profile"


# --- privacy helpers ---------------------------------------------------------


def _visibility_map(db: Session, person_id: uuid.UUID) -> Dict[str, str]:
    rows = db.scalars(
        select(PersonVisibilitySetting).where(
            PersonVisibilitySetting.person_id == person_id
        )
    ).all()
    result = {s: "private" for s in PASSIVE_SCOPE}
    defaulted = {
        "profile": "private", "contact": "private", "education": "private",
        "experience": "private", "employment": "private", "skills": "private",
        "credentials": "private", "documents": "private",
    }
    for row in rows:
        defaulted[row.scope] = row.visibility
    return defaulted


def _user_active(db: Session, user_id) -> bool:
    user = db.get(User, user_id)
    return user is not None and user.status == USER_STATUS_ACTIVE


def _display_name(db: Session, person: PersonProfile) -> Optional[str]:
    user = db.get(User, person.user_id)
    if person.preferred_name:
        return person.preferred_name
    return user.full_name if user else None


def _latest_experience(db: Session, person_id: uuid.UUID) -> Optional[dict]:
    exp = db.scalar(
        select(WorkExperience)
        .where(WorkExperience.person_id == person_id)
        .order_by(WorkExperience.start_date.desc())
        .limit(1)
    )
    if exp is None:
        return None
    return {
        "title": exp.title,
        "company_name": exp.company_name,
        "is_current": exp.is_current,
    }


def _years_experience(db: Session, person_id: uuid.UUID) -> float:
    rows = db.scalars(
        select(WorkExperience).where(WorkExperience.person_id == person_id)
    ).all()
    years = 0.0
    for exp in rows:
        years = max(years, _span_years(exp))
    return years


def _span_years(exp) -> float:
    from datetime import date

    try:
        end = exp.end_date if exp.end_date else date.today()
        return max(0.0, (end - exp.start_date).days / 365.25)
    except Exception:
        return 0.0


def _has_application_with(db: Session, person_id: uuid.UUID, organization_id: uuid.UUID) -> bool:
    row = db.execute(
        select(JobApplication.id)
        .join(Opportunity, Opportunity.id == JobApplication.opportunity_id)
        .where(
            JobApplication.person_id == person_id,
            Opportunity.company_id == organization_id,
        )
        .limit(1)
    ).first()
    return row is not None


def person_visible_to_org(
    db: Session, person_id: uuid.UUID, organization_id: uuid.UUID
) -> bool:
    """A candidate a company may legitimately see: someone who opted into
    discovery OR has an application in this organization (pipeline context)."""
    person = db.get(PersonProfile, person_id)
    if person is None or not _user_active(db, person.user_id):
        return False
    visibility = _visibility_map(db, person.id)
    if visibility.get(PASSIVE_SCOPE) == VISIBILITY_PUBLIC:
        return True
    return _has_application_with(db, person_id, organization_id)


def _require_member(db: Session, organization_id: uuid.UUID, actor_id: uuid.UUID) -> None:
    from app.services import authz

    if not authz.get_org_membership(db, actor_id, organization_id):
        raise PermissionDeniedError("You are not a member of this organization.")


def _org(db: Session, organization_id: uuid.UUID) -> Organization:
    org = db.get(Organization, organization_id)
    if org is None:
        raise NotFoundError("Organization not found.")
    return org


def _person(db: Session, person_id: uuid.UUID) -> PersonProfile:
    person = db.get(PersonProfile, person_id)
    if person is None:
        raise NotFoundError("Candidate not found.")
    return person


def _public_skills(db: Session, person_id: uuid.UUID) -> List[dict]:
    rows = db.execute(
        select(UserSkill, Skill)
        .join(Skill, Skill.id == UserSkill.skill_id)
        .where(UserSkill.person_id == person_id)
        .order_by(Skill.name)
    ).all()
    return [
        {
            "name": skill.name,
            "category": skill.category,
            "level": us.level,
            "years_experience": us.years_experience,
        }
        for us, skill in rows
    ]


def _public_experiences(db: Session, person_id: uuid.UUID) -> List[dict]:
    rows = db.scalars(
        select(WorkExperience)
        .where(WorkExperience.person_id == person_id)
        .order_by(WorkExperience.start_date.desc())
    ).all()
    return [
        {
            "company_name": e.company_name,
            "title": e.title,
            "is_current": e.is_current,
            "start_date": e.start_date,
            "end_date": e.end_date,
        }
        for e in rows[:10]
    ]


def _public_educations(db: Session, person_id: uuid.UUID) -> List[dict]:
    rows = db.scalars(
        select(Education)
        .where(Education.person_id == person_id)
        .order_by(Education.start_date.desc())
    ).all()
    return [
        {
            "institution": e.institution,
            "level": e.level,
            "degree": e.degree,
            "field_of_study": e.field_of_study,
        }
        for e in rows[:6]
    ]


def _evidence_snapshot(
    db: Session, person_id: uuid.UUID, own_view: bool = False
) -> Dict[str, List[dict]]:
    """Skill -> evidence rows (refresh once).

    For the person's own view every section is visible (they own it); for an
    employer view only PUBLIC source sections pass the filter.
    """
    skills_registry.refresh_person_evidence(db, person_id)
    visibility = _visibility_map(db, person_id)
    rows = db.execute(
        select(SkillEvidence, Skill.name)
        .join(Skill, Skill.id == SkillEvidence.skill_id)
        .where(SkillEvidence.person_id == person_id)
    ).all()
    scope_by_evidence = {
        "self": "skills",
        "experience": "experience",
        "employment": "employment",
        "certification": "credentials",
    }
    result: Dict[str, List[dict]] = {}
    for ev, name in rows:
        scope = scope_by_evidence.get(ev.evidence_type, "skills")
        if not own_view and visibility.get(scope) != VISIBILITY_PUBLIC:
            continue
        result.setdefault(name.lower(), []).append(
            {
                "evidence_type": ev.evidence_type,
                "verification_status": ev.verification_status,
            }
        )
    return result


def _public_evidence(
    db: Session, person_id: uuid.UUID, skill_name: str
) -> List[dict]:
    return _evidence_snapshot(db, person_id).get(skill_name.lower(), [])


# --- search -------------------------------------------------------------------


def _candidate_eligibility(
    db: Session, require_full_discovery: bool
):
    """Query of eligible person ids.

    ``require_full_discovery`` gates ranked matching on all professional
    scopes being public; passive search only needs ``profile`` public.
    """
    persons = db.scalars(
        select(PersonProfile)
        .join(User, User.id == PersonProfile.user_id)
        .where(User.status == USER_STATUS_ACTIVE)
    ).all()
    required = DISCOVERY_PUBLIC_SCOPES if require_full_discovery else {PASSIVE_SCOPE}
    result = []
    for person in persons:
        vis = _visibility_map(db, person.id)
        if all(vis.get(scope) == VISIBILITY_PUBLIC for scope in required):
            result.append(person)
    return result


def search_candidates(
    db: Session,
    organization_id: uuid.UUID,
    actor_id: uuid.UUID,
    *,
    q: Optional[str] = None,
    skills: Optional[List[str]] = None,
    location: Optional[str] = None,
    country: Optional[str] = None,
    min_years: Optional[float] = None,
    seniority: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> Dict:
    """Discoverable-candidate search over PUBLIC Work ID data only."""
    _require_member(db, organization_id, actor_id)
    _org(db, organization_id)
    candidates = _candidate_eligibility(db, require_full_discovery=False)

    if skills:
        skill_filters = [s for s in skills if s.strip()]
        wanted = list(skills_registry.canonical_name_map(db, skill_filters).values())
        wanted_lower = {w.lower() for w in wanted}
        # People with a private skills section are excluded from skill search:
        # hidden data is never probed.
        candidates = [
            p for p in candidates
            if _visibility_map(db, p.id).get("skills") == VISIBILITY_PUBLIC
            and _has_any_skill(db, p.id, wanted_lower)
        ]

    if location or country:
        candidates = [
            p for p in candidates
            if _visibility_map(db, p.id).get("contact") == VISIBILITY_PUBLIC
            and _matches_location(db, p, location=location, country=country)
        ]

    scored: List[dict] = []
    for person in candidates:
        vis = _visibility_map(db, person.id)
        years = _years_experience(db, person.id) if vis.get("experience") == VISIBILITY_PUBLIC else 0.0
        if min_years is not None and years < min_years:
            continue
        if seniority and vis.get("experience") == VISIBILITY_PUBLIC:
            latest = _latest_experience(db, person.id)
            if latest is None:
                continue
        score = _search_relevance(db, person, q=q, skills=skills)
        scored.append({"person": person, "score": score, "years": years})

    scored.sort(key=lambda r: (-r["score"], -r["years"]))
    total = len(scored)
    start = (page - 1) * page_size
    page_items = scored[start:start + page_size]

    items = [_discovery_summary(db, r["person"]) for r in page_items]
    # Governance record: who searched, in which org, with which filters.
    db.add(
        CandidateSearchEvent(
            organization_id=organization_id,
            user_id=actor_id,
            query=(q or "")[:300],
            filters={
                "skills": skills, "location": location, "country": country,
                "min_years": min_years, "seniority": seniority,
            },
            result_count=total,
        )
    )
    db.commit()
    return {
        "items": items, "total": total, "page": page, "page_size": page_size,
    }


def _has_any_skill(db: Session, person_id: uuid.UUID, wanted_lower: set) -> bool:
    names = db.scalars(
        select(Skill.name)
        .join(UserSkill, UserSkill.skill_id == Skill.id)
        .where(UserSkill.person_id == person_id)
    ).all()
    return any(n.lower() in wanted_lower for n in names)


def _matches_location(db: Session, person, location=None, country=None) -> bool:
    if location:
        text = f"{person.city or ''} {person.country_code or ''}".lower()
        if location.lower() not in text:
            return False
    if country and person.country_code:
        if person.country_code.lower() != country.lower():
            return False
    return True


def _search_relevance(
    db: Session, person: PersonProfile, *, q: Optional[str], skills: Optional[List[str]]
) -> int:
    score = 0
    vis = _visibility_map(db, person.id)
    if q:
        name = (_display_name(db, person) or "").lower()
        headline = (person.headline or "").lower()
        needle = q.lower()
        if needle in name:
            score += 5
        if needle in headline:
            score += 4
    if skills and vis.get("skills") == VISIBILITY_PUBLIC:
        wanted = set(skills_registry.canonical_name_map(db, skills).values())
        names = [s["name"].lower() for s in _public_skills(db, person.id)]
        score += sum(1 for w in wanted if w.lower() in names) * 6
    return score


def _discovery_summary(db: Session, person: PersonProfile) -> Dict:
    vis = _visibility_map(db, person.id)
    skills = (
        [{"name": s["name"], "level": s["level"]} for s in _public_skills(db, person.id)][:8]
        if vis.get("skills") == VISIBILITY_PUBLIC
        else []
    )
    latest = _latest_experience(db, person.id) if vis.get("experience") == VISIBILITY_PUBLIC else None
    return {
        "person_id": str(person.id),
        "name": _display_name(db, person),
        "headline": person.headline,
        "location": (
            _person_location(person) if vis.get("contact") == VISIBILITY_PUBLIC else None
        ),
        "skills": skills,
        "experience_years": round(_years_experience(db, person.id), 1)
        if vis.get("experience") == VISIBILITY_PUBLIC else None,
        "latest_role": latest,
        "disclosure": {
            "profile": True,
            "skills_visible": vis.get("skills") == VISIBILITY_PUBLIC,
            "experience_visible": vis.get("experience") == VISIBILITY_PUBLIC,
            "contact_visible": vis.get("contact") == VISIBILITY_PUBLIC,
        },
    }


def _person_location(person: PersonProfile) -> Optional[str]:
    if person.city:
        return f"{person.city}{', ' + person.country_code if person.country_code else ''}"
    return person.country_code


# --- ranked opportunity -> candidates -----------------------------------------


def match_mode_label(score: float, coverage: float, years: float, needed_min: float) -> str:
    if score >= 0.7 and coverage >= 0.66:
        return MATCH_MODE_STRONG
    if score >= 0.55 or coverage >= 0.5:
        return MATCH_MODE_POTENTIAL
    if coverage >= 0.3 and years >= needed_min * 0.7:
        return MATCH_MODE_CAREER_TRANSITION
    return MATCH_MODE_EXPLORE


def match_candidates_for_opportunity(
    db: Session,
    organization_id: uuid.UUID,
    opportunity_id: uuid.UUID,
    actor_id: uuid.UUID,
    *,
    exclude_applied: bool = True,
    page: int = 1,
    page_size: int = 20,
) -> Dict:
    """Rank discoverable candidates for one opportunity (explainable)."""
    _require_member(db, organization_id, actor_id)
    _org(db, organization_id)
    opp = db.get(Opportunity, opportunity_id)
    if opp is None:
        raise NotFoundError("Opportunity not found.")
    if opp.company_id != organization_id:
        raise NotFoundError("Opportunity not found.")

    candidates = _candidate_eligibility(db, require_full_discovery=True)
    applied_ids = set()
    if exclude_applied:
        applied_ids = set(
            db.scalars(
                select(JobApplication.person_id).where(
                    JobApplication.opportunity_id == opp.id
                )
            ).all()
        )
    pool = [p for p in candidates if p.id not in applied_ids]

    required = [str(s) for s in (opp.skills_required or [])]
    name_map = skills_registry.canonical_name_map(db, required) if required else {}
    goal = None  # employers never read the candidate's private career goals

    ranked = []
    for person in pool:
        profile = matching_service.load_candidate_profile(db, person.id)
        result = matching_service.match_opportunity(
            profile, opp, goal, name_map=name_map
        )
        skills_comp = result["components"].get("skills", {})
        matched = skills_comp.get("matched", [])
        missing = skills_comp.get("missing", [])
        coverage = len(matched) / (len(matched) + len(missing)) if (matched or missing) else 1.0
        needed_min = _min_years_from_opp(opp)
        mode = match_mode_label(
            result["score"], coverage, profile.years_experience, needed_min
        )
        ranked.append(
            {
                "person": person,
                "profile": profile,
                "match": result,
                "mode": mode,
                "coverage": coverage,
            }
        )

    # Deterministic ordering: strong first, then score.
    order = {MATCH_MODE_STRONG: 0, MATCH_MODE_POTENTIAL: 1,
             MATCH_MODE_CAREER_TRANSITION: 2, MATCH_MODE_EXPLORE: 3}
    ranked.sort(key=lambda r: (order[r["mode"]], -r["match"]["score"]))
    total = len(ranked)
    start = (page - 1) * page_size
    page_rows = ranked[start:start + page_size]

    items = []
    for row in page_rows:
        person = row["person"]
        match = row["match"]
        summary = _discovery_summary(db, person)
        skills_comp = match.get("components", {}).get("skills", {})
        items.append(
            {
                "person_id": str(person.id),
                "summary": summary,
                "percent": match["percent"],
                "score": match["score"],
                "mode": row["mode"],
                "coverage": round(row["coverage"], 3),
                "strengths": match.get("strengths", [])[:4],
                "gaps": match.get("gaps", [])[:4],
                "matched_skills": skills_comp.get("matched", [])[:12],
                "missing_skills": skills_comp.get("missing", [])[:12],
            }
        )
    return {"items": items, "total": total, "page": page, "page_size": page_size,
            "opportunity_id": str(opp.id)}


def _min_years_from_opp(opp: Opportunity) -> float:
    from app.services.matching import _EXPERIENCE_YEARS

    lo, _hi = _EXPERIENCE_YEARS.get((opp.experience_level or "").lower(), (0, 15))
    return float(lo)


# --- candidate profile (progressive disclosure) --------------------------------


def candidate_profile_for_org(
    db: Session,
    organization_id: uuid.UUID,
    person_id: uuid.UUID,
    actor_id: uuid.UUID,
    opportunity_id: Optional[uuid.UUID] = None,
) -> Dict:
    """Employer-side candidate view respecting progressive disclosure.

    Discovery context shows only PUBLIC sections. Pipeline context (person
    applied to this org) additionally shows the same disclosure the Phase 6
    review flow allows.
    """
    _require_member(db, organization_id, actor_id)
    _org(db, organization_id)
    if not person_visible_to_org(db, person_id, organization_id):
        raise NotFoundError("Candidate not found.")
    person = _person(db, person_id)
    vis = _visibility_map(db, person.id)
    applied = _has_application_with(db, person_id, organization_id)

    if vis.get(PASSIVE_SCOPE) == VISIBILITY_PUBLIC:
        summary = _discovery_summary(db, person)
        if vis.get("experience") == VISIBILITY_PUBLIC:
            summary["experience"] = _public_experiences(db, person.id)
        if vis.get("education") == VISIBILITY_PUBLIC:
            summary["education"] = _public_educations(db, person.id)
    else:
        # Pipeline context: same minimum-necessary view as application review.
        from app.services.company_os import candidate_summary

        apps = db.scalars(
            select(JobApplication).where(
                JobApplication.person_id == person.id,
                JobApplication.opportunity_id.in_(
                    select(Opportunity.id).where(
                        Opportunity.company_id == organization_id
                    )
                ),
            )
        ).all()
        if not apps:
            raise NotFoundError("Candidate not found.")
        summary = candidate_summary(db, organization_id, apps[0], actor_id)
        summary["person_id"] = str(person.id)

    summary.setdefault("person_id", str(person.id))
    summary["context"] = "pipeline" if applied else "discovery"
    summary["saved"] = _is_saved(db, organization_id, actor_id, person_id)
    summary["pool_names"] = _pool_names_for_person(db, organization_id, person_id)

    if opportunity_id:
        opp = db.get(Opportunity, opportunity_id)
        if opp is not None and opp.company_id == organization_id:
            profile = matching_service.load_candidate_profile(db, person.id)
            name_map = skills_registry.canonical_name_map(
                db, [str(s) for s in (opp.skills_required or [])]
            )
            match = matching_service.match_opportunity(
                profile, opp, None, name_map=name_map
            )
            comp = match.get("components", {}).get("skills", {})
            matched = comp.get("matched", [])
            missing = comp.get("missing", [])
            coverage = (
                len(matched) / (len(matched) + len(missing))
                if (matched or missing) else 1.0
            )
            summary["match"] = {
                "percent": match["percent"],
                "score": match["score"],
                "mode": match_mode_label(
                    match["score"], coverage, profile.years_experience,
                    _min_years_from_opp(opp),
                ),
                "strengths": match.get("strengths", [])[:4],
                "gaps": match.get("gaps", [])[:4],
                "matched_skills": matched[:12],
                "missing_skills": missing[:12],
                "gap_analysis": _gap_analysis(db, person.id, opp),
            }
    return summary


def _is_saved(db: Session, organization_id, user_id, person_id) -> bool:
    return (
        db.scalar(
            select(SavedCandidate.id).where(
                SavedCandidate.organization_id == organization_id,
                SavedCandidate.user_id == user_id,
                SavedCandidate.person_id == person_id,
            ).limit(1)
        )
        is not None
    )


def _pool_names_for_person(db: Session, organization_id, person_id) -> List[str]:
    rows = db.execute(
        select(TalentPool.name)
        .join(TalentPoolMember, TalentPoolMember.pool_id == TalentPool.id)
        .where(
            TalentPool.organization_id == organization_id,
            TalentPoolMember.person_id == person_id,
        )
    ).all()
    return [r[0] for r in rows]


def _gap_analysis(
    db: Session, person_id: uuid.UUID, opp: Opportunity, own_view: bool = False
) -> Dict:
    """Skill gap between a person and one opportunity (evidence-grounded)."""
    name_map = skills_registry.canonical_name_map(
        db, [str(s) for s in (opp.skills_required or [])]
    )
    profile = matching_service.load_candidate_profile(db, person_id)
    result = matching_service.skill_component(profile, opp, name_map=name_map)
    matched = result.get("matched", [])
    missing = result.get("missing", [])
    evidence = _evidence_snapshot(db, person_id, own_view=own_view)
    return {
        "matched": [
            {"skill": s, "evidence": evidence.get(s.lower(), [])}
            for s in matched
        ],
        "gaps": [{"skill": s, "source": "opportunity_requirement"} for s in missing],
        "coverage": round(
            len(matched) / (len(matched) + len(missing)), 3
        ) if (matched or missing) else 1.0,
    }


def own_skill_gap_analysis(
    db: Session, person_id: uuid.UUID, opportunity_id: uuid.UUID
) -> Dict:
    """Jobseeker-side gap analysis over the person's OWN Work ID."""
    opp = db.get(Opportunity, opportunity_id)
    if opp is None or opp.status != "active":
        raise NotFoundError("Opportunity not found.")
    return _gap_analysis(db, person_id, opp, own_view=True)


# --- saved candidates ----------------------------------------------------------


def save_candidate(
    db: Session,
    organization_id: uuid.UUID,
    person_id: uuid.UUID,
    actor_id: uuid.UUID,
    *,
    note: Optional[str] = None,
    tags: Optional[List[str]] = None,
) -> SavedCandidate:
    _require_member(db, organization_id, actor_id)
    _org(db, organization_id)
    if not person_visible_to_org(db, person_id, organization_id):
        raise NotFoundError("Candidate not found.")
    existing = db.scalar(
        select(SavedCandidate).where(
            SavedCandidate.organization_id == organization_id,
            SavedCandidate.user_id == actor_id,
            SavedCandidate.person_id == person_id,
        )
    )
    if existing is not None:
        existing.note = note
        existing.tags = tags
        db.commit()
        db.refresh(existing)
        return existing
    saved = SavedCandidate(
        organization_id=organization_id,
        user_id=actor_id,
        person_id=person_id,
        note=note,
        tags=tags,
    )
    db.add(saved)
    db.commit()
    db.refresh(saved)
    return saved


def unsave_candidate(
    db: Session, organization_id: uuid.UUID, person_id: uuid.UUID, actor_id: uuid.UUID
) -> None:
    _require_member(db, organization_id, actor_id)
    saved = db.scalar(
        select(SavedCandidate).where(
            SavedCandidate.organization_id == organization_id,
            SavedCandidate.user_id == actor_id,
            SavedCandidate.person_id == person_id,
        )
    )
    if saved is None:
        raise NotFoundError("Saved candidate not found.")
    db.delete(saved)
    db.commit()


def list_saved_candidates(
    db: Session, organization_id: uuid.UUID, actor_id: uuid.UUID
) -> List[dict]:
    _require_member(db, organization_id, actor_id)
    rows = db.scalars(
        select(SavedCandidate)
        .where(
            SavedCandidate.organization_id == organization_id,
            SavedCandidate.user_id == actor_id,
        )
        .order_by(SavedCandidate.updated_at.desc())
    ).all()
    items = []
    for saved in rows:
        person = db.get(PersonProfile, saved.person_id)
        if person is None:
            continue
        vis = _visibility_map(db, person.id)
        items.append(
            {
                "id": str(saved.id),
                "person_id": str(saved.person_id),
                "name": _display_name(db, person),
                "headline": person.headline,
                "note": saved.note,
                "tags": saved.tags,
                "saved_at": saved.created_at,
                "context": (
                    "discovery"
                    if vis.get(PASSIVE_SCOPE) == VISIBILITY_PUBLIC
                    else "pipeline"
                ),
            }
        )
    return items


# --- talent pools ---------------------------------------------------------------


def create_pool(
    db: Session,
    organization_id: uuid.UUID,
    actor_id: uuid.UUID,
    *,
    name: str,
    description: Optional[str] = None,
) -> TalentPool:
    _require_member(db, organization_id, actor_id)
    _org(db, organization_id)
    existing = db.scalar(
        select(TalentPool.id).where(
            TalentPool.organization_id == organization_id,
            func.lower(TalentPool.name) == name.strip().lower(),
        ).limit(1)
    )
    if existing is not None:
        raise ConflictError("A pool with this name already exists.")
    pool = TalentPool(
        organization_id=organization_id, name=name.strip(),
        description=description, created_by=actor_id,
    )
    db.add(pool)
    db.commit()
    db.refresh(pool)
    return pool


def list_pools(
    db: Session, organization_id: uuid.UUID, actor_id: uuid.UUID
) -> List[dict]:
    _require_member(db, organization_id, actor_id)
    pools = db.scalars(
        select(TalentPool)
        .where(TalentPool.organization_id == organization_id)
        .order_by(TalentPool.created_at.desc())
    ).all()
    return [
        {
            "id": str(p.id),
            "name": p.name,
            "description": p.description,
            "created_at": p.created_at,
            "member_count": len(
                db.scalars(
                    select(TalentPoolMember.id).where(
                        TalentPoolMember.pool_id == p.id
                    )
                ).all()
            ),
        }
        for p in pools
    ]


def _owned_pool(db: Session, organization_id, pool_id) -> TalentPool:
    pool = db.get(TalentPool, pool_id)
    if pool is None or pool.organization_id != organization_id:
        raise NotFoundError("Talent pool not found.")
    return pool


def pool_detail(
    db: Session, organization_id: uuid.UUID, pool_id: uuid.UUID, actor_id: uuid.UUID
) -> Dict:
    _require_member(db, organization_id, actor_id)
    pool = _owned_pool(db, organization_id, pool_id)
    members = db.scalars(
        select(TalentPoolMember)
        .where(TalentPoolMember.pool_id == pool.id)
        .order_by(TalentPoolMember.created_at.desc())
    ).all()
    people = []
    for m in members:
        person = db.get(PersonProfile, m.person_id)
        if person is None:
            continue
        people.append(
            {
                "person_id": str(m.person_id),
                "name": _display_name(db, person),
                "headline": person.headline,
                "note": m.note,
                "added_at": m.created_at,
            }
        )
    return {
        "id": str(pool.id),
        "name": pool.name,
        "description": pool.description,
        "members": people,
        "member_count": len(people),
    }


def add_pool_member(
    db: Session,
    organization_id: uuid.UUID,
    pool_id: uuid.UUID,
    person_id: uuid.UUID,
    actor_id: uuid.UUID,
    note: Optional[str] = None,
) -> TalentPoolMember:
    _require_member(db, organization_id, actor_id)
    pool = _owned_pool(db, organization_id, pool_id)
    if not person_visible_to_org(db, person_id, organization_id):
        raise NotFoundError("Candidate not found.")
    existing = db.scalar(
        select(TalentPoolMember.id).where(
            TalentPoolMember.pool_id == pool.id,
            TalentPoolMember.person_id == person_id,
        ).limit(1)
    )
    if existing is not None:
        raise ConflictError("Candidate is already in this pool.")
    member = TalentPoolMember(
        pool_id=pool.id, person_id=person_id, added_by=actor_id, note=note
    )
    db.add(member)
    db.commit()
    db.refresh(member)
    return member


def remove_pool_member(
    db: Session,
    organization_id: uuid.UUID,
    pool_id: uuid.UUID,
    person_id: uuid.UUID,
    actor_id: uuid.UUID,
) -> None:
    _require_member(db, organization_id, actor_id)
    pool = _owned_pool(db, organization_id, pool_id)
    member = db.scalar(
        select(TalentPoolMember).where(
            TalentPoolMember.pool_id == pool.id,
            TalentPoolMember.person_id == person_id,
        )
    )
    if member is None:
        raise NotFoundError("Candidate is not in this pool.")
    db.delete(member)
    db.commit()


def delete_pool(
    db: Session, organization_id: uuid.UUID, pool_id: uuid.UUID, actor_id: uuid.UUID
) -> None:
    _require_member(db, organization_id, actor_id)
    pool = _owned_pool(db, organization_id, pool_id)
    db.delete(pool)
    db.commit()


# --- jobseeker-side career intelligence -----------------------------------------


def career_intelligence(db: Session, person_id: uuid.UUID) -> Dict:
    """Data-grounded intelligence over the person's OWN Work ID + the active
    opportunity catalogue. Never invents facts and never promises outcomes."""
    person = _person(db, person_id)
    skills = db.execute(
        select(UserSkill, Skill)
        .join(Skill, Skill.id == UserSkill.skill_id)
        .where(UserSkill.person_id == person.id)
        .order_by(Skill.name)
    ).all()
    experiences = db.scalars(
        select(WorkExperience)
        .where(WorkExperience.person_id == person.id)
        .order_by(WorkExperience.start_date.desc())
    ).all()
    goal = matching_service.load_primary_goal(db, person.id)
    current = experiences[0] if experiences else None

    opps = db.scalars(
        select(Opportunity)
        .where(Opportunity.status == "active", Opportunity.is_approved.is_(True))
        .limit(200)
    ).all()
    matches = matching_service.match_all(db, person.id, opps)
    opp_by_id = {str(o.id): o for o in opps}
    for m in matches:
        opp = opp_by_id.get(m["opportunity_id"])
        m["title"] = opp.title if opp else None
        m["company"] = opp.company_name if opp else None

    within_reach = []
    grow_into = []
    for m in matches:
        if m["percent"] >= 70:
            within_reach.append(m)
        elif m["percent"] >= 45:
            grow_into.append(m)

    # Skills to develop: aggregated gaps across roles the person nearly
    # matches (55-79%) — tied to actual opportunity requirements.
    gap_counts: Dict[str, int] = {}
    for m in matches:
        if 55 <= m["percent"] < 80:
            for s in m.get("missing_skills", []):
                gap_counts[s] = gap_counts.get(s, 0) + 1
    development = sorted(gap_counts.items(), key=lambda kv: -kv[1])[:8]

    # Advisory career-path step (from seeded catalogue) if the goal or the
    # latest role appears on a path.
    path_advice = _path_advice(db, person, goal, current)

    evidence = _evidence_snapshot(db, person.id, own_view=True)
    return {
        "capability": {
            "years_experience": round(_years_experience(db, person.id), 1),
            "roles_held": len(experiences),
            "skills": [
                {
                    "name": skill.name,
                    "level": us.level,
                    "years_experience": us.years_experience,
                    "evidence_count": len(evidence.get(skill.name.lower(), [])),
                }
                for us, skill in skills
            ],
            "verified_skill_count": sum(
                1
                for rows in evidence.values()
                for row in rows
                if row["verification_status"] == "verified"
            ),
        },
        "current_position": {
            "title": current.title if current else None,
            "company": current.company_name if current else None,
            "is_current": current.is_current if current else False,
        },
        "career_goal": {
            "title": goal.title if goal else None,
            "target_role": goal.target_role if goal else None,
        },
        "roles_within_reach": _condensed(within_reach),
        "roles_to_grow_into": _condensed(grow_into),
        "skill_development": [
            {"skill": s, "appears_in_roles": c} for s, c in development
        ],
        "path_advice": path_advice,
        "disclaimer": (
            "This analysis is computed from your Work ID and real, active "
            "opportunities. Career movement is never guaranteed."
        ),
    }


def _condensed(selected) -> List[dict]:
    return [
        {
            "opportunity_id": m["opportunity_id"],
            "title": m.get("title"),
            "company": m.get("company"),
            "percent": m["percent"],
            "strengths": m.get("strengths", [])[:3],
            "missing_skills": m.get("missing_skills", [])[:6],
        }
        for m in selected[:6]
    ]


def _path_advice(db: Session, person, goal, current) -> Optional[Dict]:
    from app.models.talent import CareerPath, CareerPathStep

    paths = db.scalars(select(CareerPath)).all()
    anchor = (goal.target_role if goal and goal.target_role else None) or (
        current.title if current else None
    )
    if not anchor or not paths:
        return None
    anchor_l = anchor.lower()
    for path in paths:
        steps = db.scalars(
            select(CareerPathStep)
            .where(CareerPathStep.path_id == path.id)
            .order_by(CareerPathStep.step_order)
        ).all()
        titles = [s.role_title.lower() for s in steps]
        if anchor_l not in titles:
            continue
        idx = titles.index(anchor_l)
        if idx + 1 >= len(steps):
            return {
                "path": path.title,
                "target_role": path.target_role,
                "note": f"You are at the furthest seeded step of this path ({steps[idx].role_title}).",
                "next_step": None,
            }
        nxt = steps[idx + 1]
        return {
            "path": path.title,
            "target_role": path.target_role,
            "current_step": steps[idx].role_title,
            "next_step": {
                "role_title": nxt.role_title,
                "seniority": nxt.seniority,
                "description": nxt.description,
                "typical_skills": nxt.skills_required,
            },
            "note": (
                "Advisory only — a step on a seeded path, not a promise of "
                "progression."
            ),
        }
    return None
