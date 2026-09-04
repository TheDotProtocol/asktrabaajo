"""Career Advisor — deterministic, evidence-based intelligence (Phase 15).

Everything here is computed from canonical platform state (Work ID,
goals, milestones, applications, the skill taxonomy, career-path
catalogue, and the active opportunity set). Nothing is invented, and no
outcome is ever promised. The Athena layer explains THESE facts in
conversation; it does not reconstruct the person's history from raw
records, and it cannot change the facts.

Public surface (all ``person_id``-scoped, owner-only at the API layer):

- ``profile_digest``      — structured professional digest (whitelist only)
- ``skill_gap_analysis``  — matched / partial / missing vs a target
- ``career_paths``        — catalogue paths anchored to the candidate
- ``opportunity_recommendations`` — explainable ranked opportunities
- ``application_analysis``— deterministic funnel + outcome read
- ``action_plan``         — goal -> gaps -> actions -> milestones

Data-minimization contract: the digest never includes contact details,
date of birth, government/tax/passport identifiers, KYC, document
contents, or authentication material — the same deny-list the Athena
context builder enforces (see ``athena_context.SENSITIVE_FIELD_NAMES``).
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.timeutil import utc_now_naive
from app.models.career import (
    CareerGoal,
    CareerMilestone,
    JobApplication,
    Opportunity,
)
from app.models.enums import (
    APPLICATION_STATUS_ACCEPTED,
    APPLICATION_STATUS_APPLIED,
    APPLICATION_STATUS_APPLICATION_RECEIVED,
    APPLICATION_STATUS_ASSESSMENT,
    APPLICATION_STATUS_INTERVIEW,
    APPLICATION_STATUS_OFFER,
    APPLICATION_STATUS_ON_HOLD,
    APPLICATION_STATUS_REJECTED,
    APPLICATION_STATUS_SCREENING,
    APPLICATION_STATUS_WITHDRAWN,
    CREDENTIAL_STATUS_VERIFIED,
)
from app.models.talent import CareerPath, CareerPathStep, SkillRelationship
from app.models.work import Credential, Education, Skill, UserSkill, WorkExperience
from app.services import development
from app.services import matching
from app.services import skills_registry

# Stuck-application threshold (no employer movement after N days).
_STUCK_DAYS = 21

_APPLIED_TO_ADVANCE = {
    APPLICATION_STATUS_APPLICATION_RECEIVED,
    APPLICATION_STATUS_SCREENING,
    APPLICATION_STATUS_ASSESSMENT,
    APPLICATION_STATUS_INTERVIEW,
    APPLICATION_STATUS_OFFER,
    APPLICATION_STATUS_ACCEPTED,
}
# Any row that means the person actually applied (employer may have since
# rejected/withdrawn it, but the application happened).
_APPLIED_OR_LATER = _APPLIED_TO_ADVANCE | {
    APPLICATION_STATUS_APPLIED,
    APPLICATION_STATUS_REJECTED,
    APPLICATION_STATUS_WITHDRAWN,
    APPLICATION_STATUS_ON_HOLD,
}
_ADVANCED_OUTCOMES = {
    APPLICATION_STATUS_INTERVIEW,
    APPLICATION_STATUS_OFFER,
    APPLICATION_STATUS_ACCEPTED,
}
_CLOSED_OUTCOMES = {
    APPLICATION_STATUS_REJECTED,
    APPLICATION_STATUS_WITHDRAWN,
    APPLICATION_STATUS_ACCEPTED,
}

_PROGRESS_ORDER = [
    APPLICATION_STATUS_APPLIED,
    APPLICATION_STATUS_APPLICATION_RECEIVED,
    APPLICATION_STATUS_SCREENING,
    APPLICATION_STATUS_ASSESSMENT,
    APPLICATION_STATUS_INTERVIEW,
    APPLICATION_STATUS_OFFER,
    APPLICATION_STATUS_ACCEPTED,
]


def _person(db: Session, person_id: uuid.UUID):
    from app.models.identity import PersonProfile

    person = db.get(PersonProfile, person_id)
    if person is None:
        from app.core.errors import NotFoundError

        raise NotFoundError("Jobseeker profile not found.")
    return person


def person_for_user(db: Session, user_id: uuid.UUID):
    """The PersonProfile owned by ``user_id`` (or a NotFoundError)."""
    from app.models.identity import PersonProfile

    person = db.scalar(
        select(PersonProfile).where(PersonProfile.user_id == user_id)
    )
    if person is None:
        from app.core.errors import PermissionDeniedError

        raise PermissionDeniedError("No jobseeker profile exists for this account.")
    return person


def _collect_skills(db: Session, person_id: uuid.UUID) -> Dict[str, str]:
    """Canonical-name -> level map of the person's skills."""
    return development.collect_skills(db, person_id)


def _ordered_experiences(db: Session, person_id: uuid.UUID) -> list:
    return db.scalars(
        select(WorkExperience)
        .where(WorkExperience.person_id == person_id)
        .order_by(WorkExperience.start_date.desc())
    ).all()


def _primary_goal(db: Session, person_id: uuid.UUID) -> Optional[CareerGoal]:
    return matching.load_primary_goal(db, person_id)


def _active_opportunities(db: Session) -> list:
    return db.scalars(
        select(Opportunity)
        .where(Opportunity.status == "active", Opportunity.is_approved.is_(True))
        .order_by(Opportunity.created_at.desc())
        .limit(300)
    ).all()


def _skill_level_rank(level: Optional[str]) -> int:
    return {"beginner": 0, "intermediate": 1, "advanced": 2, "expert": 3}.get(
        level or "", 1
    )


def _coerce_date(value) -> Optional[date]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    return value


# --- Career profile digest -----------------------------------------------------


def profile_digest(db: Session, person_id: uuid.UUID) -> Dict:
    """Structured Career Profile Digest — whitelisted professional facts.

    Athena receives this digest; it never reconstructs the person's
    history from database rows. Sensitive fields are excluded by
    construction (see module docstring).
    """
    person = _person(db, person_id)
    skills_map = _collect_skills(db, person_id)
    experiences = _ordered_experiences(db, person_id)
    educations = db.scalars(
        select(Education).where(Education.person_id == person_id)
    ).all()
    credentials = db.scalars(
        select(Credential).where(Credential.person_id == person_id)
    ).all()
    goal = _primary_goal(db, person_id)
    milestones = db.scalars(
        select(CareerMilestone)
        .where(CareerMilestone.person_id == person_id)
        .order_by(CareerMilestone.occurred_on.desc())
        .limit(8)
    ).all()
    applications = db.scalars(
        select(JobApplication).where(JobApplication.person_id == person_id)
    ).all()

    current = experiences[0] if experiences else None
    strongest = sorted(
        skills_map,
        key=lambda s: _skill_level_rank(skills_map[s]),
        reverse=True,
    )[:6]
    verified = [
        {"name": c.name, "issuer": c.issuer}
        for c in credentials
        if c.status == CREDENTIAL_STATUS_VERIFIED
    ]
    unverified = [
        {"name": c.name, "issuer": c.issuer, "status": c.status}
        for c in credentials
        if c.status != CREDENTIAL_STATUS_VERIFIED
    ]

    app_status_counts: Dict[str, int] = {}
    for a in applications:
        app_status_counts[a.status] = app_status_counts.get(a.status, 0) + 1

    total_years = 0.0
    for exp in experiences:
        end = exp.end_date or date.today()
        try:
            total_years = max(total_years, (end - exp.start_date).days / 365.25)
        except Exception:
            pass

    return {
        "person_id": str(person.id),
        "professional_summary": (
            f"{person.headline or 'Professional profile'}"
        ),
        "current_position": {
            "title": current.title if current else None,
            "company": current.company_name if current else None,
        },
        "experience_summary": {
            "roles_held": len(experiences),
            "years_experience": round(total_years, 1),
            "recent_roles": [
                {
                    "title": e.title,
                    "company": e.company_name,
                    "start_date": e.start_date.isoformat() if e.start_date else None,
                    "end_date": e.end_date.isoformat() if e.end_date else None,
                    "current": e.is_current,
                }
                for e in experiences[:4]
            ],
        },
        "education_summary": [
            {
                "level": e.level,
                "degree": e.degree,
                "institution": e.institution,
                "field": e.field_of_study,
            }
            for e in educations
        ],
        "credentials": {
            "verified": verified,
            "unverified": unverified,
            # Explicit honesty: unverified claims are never presented as fact.
            "note": (
                "Credentials are shown with their verification state; "
                "unverified entries are the candidate's claim, not a verified fact."
            ),
        },
        "skills": {
            "all": [
                {"name": name, "level": level}
                for name, level in sorted(skills_map.items())
            ],
            "strongest": [
                {"name": name, "level": skills_map[name]} for name in strongest
            ],
        },
        "career_goal": {
            "title": goal.title if goal else None,
            "target_role": goal.target_role if goal else None,
            "target_industries": (goal.target_industries or []) if goal else [],
            "target_locations": (goal.target_locations or []) if goal else [],
            "preferred_work_modes": (goal.preferred_work_modes or []) if goal else [],
            "availability": goal.availability if goal else None,
        },
        "career_milestones": [
            {
                "title": m.title,
                "kind": m.kind,
                "occurred_on": m.occurred_on.isoformat() if m.occurred_on else None,
            }
            for m in milestones
        ],
        "application_status_counts": app_status_counts,
        "disclaimer": (
            "This digest is computed from your Work ID and canonical platform "
            "records. Career movement is never guaranteed."
        ),
    }


# --- Skill-gap analysis --------------------------------------------------------


def _adjacent_skills(db: Session, skill_name: str) -> List[str]:
    """Canonical names related to ``skill_name`` via the taxonomy graph.

    Uses explicit ``SkillRelationship`` edges only — never invented
    adjacency. Exact-name lookup first; alias-canonicalized fallback.
    """
    name_map = skills_registry.canonical_name_map(db, [skill_name])
    canonical = name_map.get(skill_name, skill_name)
    skill = db.scalar(select(Skill).where(Skill.name == canonical))
    if skill is None:
        return []
    rows = db.scalars(
        select(SkillRelationship).where(
            SkillRelationship.skill_id == skill.id,
            SkillRelationship.kind.in_(["related", "complementary", "parent"]),
        )
    ).all()
    related_ids = [r.related_skill_id for r in rows]
    if not related_ids:
        return []
    related = db.scalars(select(Skill).where(Skill.id.in_(related_ids))).all()
    return [s.name for s in related]


def skill_gap_analysis(
    db: Session,
    person_id: uuid.UUID,
    opportunity_id: Optional[uuid.UUID] = None,
) -> Dict:
    """Matched / partial / missing skills against a concrete target.

    Target: the given opportunity when supplied; otherwise the primary
    goal's target role (skill clusters) when set; otherwise an explicit
    ``no target`` result — the service never fabricates a requirement set.
    """
    skills_map = _collect_skills(db, person_id)
    experiences = _ordered_experiences(db, person_id)
    goal = _primary_goal(db, person_id)
    credentials = db.scalars(
        select(Credential).where(Credential.person_id == person_id)
    ).all()

    required: List[str] = []
    target_kind = "opportunity"
    target: Optional[Dict] = None

    if opportunity_id is not None:
        opp = db.get(Opportunity, opportunity_id)
        if opp is None:
            from app.core.errors import NotFoundError

            raise NotFoundError("Opportunity not found.")
        required = [str(s).strip() for s in (opp.skills_required or []) if str(s).strip()]
        target = {
            "kind": "opportunity",
            "id": str(opp.id),
            "title": opp.title,
            "company": opp.company_name,
            "experience_level": opp.experience_level,
        }
    else:
        target_kind = "goal"
        target_role = (goal.target_role if goal else None) or None
        target = {"kind": "goal", "title": goal.title if goal else None,
                  "target_role": target_role}
        if target_role:
            # Infer canonical requirement set from the goal cluster ONLY
            # (static catalogue in development.py) — never fabricated.
            required = _goal_cluster_skills(target_role, skills_map)

    name_map = skills_registry.canonical_name_map(db, required)
    required_lower = {}
    for r in required:
        canonical = name_map.get(r, r)
        required_lower[canonical.lower()] = canonical

    matched, partial, missing = [], [], []
    for req_lower in sorted(required_lower):
        canonical = required_lower[req_lower]
        if req_lower in skills_map:
            matched.append(
                {
                    "skill": canonical,
                    "level": skills_map[req_lower],
                    "status": "matched",
                }
            )
            continue
        adjacent = [
            a for a in _adjacent_skills(db, canonical) if a.lower() in skills_map
        ]
        if adjacent:
            partial.append(
                {
                    "skill": canonical,
                    "related_skills": adjacent,
                    "status": "partial",
                    "note": "You have related skills, not this exact one.",
                }
            )
        else:
            missing.append(
                {
                    "skill": canonical,
                    "status": "missing",
                    "note": "Not present in your Work ID skills.",
                }
            )

    years = 0.0
    for exp in experiences:
        end = exp.end_date or date.today()
        try:
            years = max(years, (end - exp.start_date).days / 365.25)
        except Exception:
            pass

    experience_gap = None
    if target and target.get("experience_level"):
        needed = int("".join(ch for ch in str(target["experience_level"]) if ch.isdigit()) or 0)
        if years < needed:
            experience_gap = {
                "required_years": needed,
                "years_experience": round(years, 1),
                "note": f"The role asks for ~{needed}+ years; your Work ID shows {years:.1f}.",
            }

    credential_gap = None
    verified_names = {c.name.lower() for c in credentials if c.status == CREDENTIAL_STATUS_VERIFIED}
    if not verified_names:
        credential_gap = {
            "note": (
                "No verified credentials are recorded on your Work ID yet. "
                "Add certifications you hold; verification can come later."
            )
        }

    coverage = len(matched) / len(required) if required else None
    return {
        "target": target,
        "target_kind": target_kind,
        "required_skill_count": len(required),
        "matched_skills": matched,
        "partial_skills": partial,
        "missing_skills": missing,
        "skill_coverage": round(coverage, 3) if coverage is not None else None,
        "experience_gap": experience_gap,
        "credential_gap": credential_gap,
        "summary": _gap_summary(matched, partial, missing, target, years),
        "disclaimer": (
            "Requirements come from the opportunity or the canonical goal "
            "cluster — never invented. Meeting them is no guarantee of an offer."
        ),
    }


def _goal_cluster_skills(target_role: str, skills_map: Dict[str, str]) -> List[str]:
    """Skill list for a target role, from the static goal-cluster catalogue."""
    clusters = {
        "engineer": ["python", "typescript", "react", "node", "postgresql", "aws"],
        "engineering manager": ["leadership", "people management", "hiring", "mentoring"],
        "machine learning": ["python", "machine learning", "pytorch", "statistics"],
        "product manager": ["product management", "analytics", "sql", "user research"],
        "designer": ["figma", "user research", "prototyping"],
        "analyst": ["sql", "excel", "python", "statistics", "data analysis"],
        "security": ["security", "aws", "python", "compliance"],
        "cloud": ["aws", "kubernetes", "terraform", "python"],
        "data": ["sql", "python", "statistics", "machine learning"],
        "hr": ["recruiting", "onboarding", "employee relations"],
        "marketing": ["marketing", "analytics", "content", "seo"],
        "finance": ["financial modeling", "excel", "accounting", "analysis"],
        "sales": ["sales", "negotiation", "crm", "account management"],
    }
    lower = target_role.lower()
    for key, cluster in clusters.items():
        if key in lower:
            return cluster
    # Fall back to skills already present (nothing invented) so the analysis
    # can still return a structured (possibly empty) result.
    if skills_map:
        return sorted(skills_map)[:6]
    return []


def _gap_summary(matched, partial, missing, target, years) -> str:
    if target is None or (target.get("target_role") is None and target.get("title") is None):
        return "Set a career goal (or pick an opportunity) to see your skill gaps."
    if not (matched or partial or missing):
        return "No canonical requirement set is defined for this target yet."
    bits = []
    if matched:
        bits.append(f"you already cover {len(matched)} required skills")
    if partial:
        bits.append(f"{len(partial)} are close (related skills only)")
    if missing:
        bits.append(f"{len(missing)} are missing")
    return "Against this target, " + "; ".join(bits) + "."


# --- Career paths --------------------------------------------------------------


def career_paths(db: Session, person_id: uuid.UUID) -> Dict:
    """Paths from the advisory catalogue anchored to this candidate.

    Classification is factual, not speculative: DIRECT when the anchor
    role literally sits on the path; ADJACENT when the target step's
    skills overlap the candidate's; TRANSITION when the path target is
    the person's stated goal but no history matches; EXPLORATORY when the
    path merely shares skills with the candidate. Paths are advisory —
    never guaranteed progression.
    """
    experiences = _ordered_experiences(db, person_id)
    goal = _primary_goal(db, person_id)
    skills_map = _collect_skills(db, person_id)
    roles_held = [e.title for e in experiences if e.title]
    anchor = (
        (goal.target_role if goal and goal.target_role else None)
        or (roles_held[0] if roles_held else None)
    )
    paths = db.scalars(
        select(CareerPath).where(CareerPath.status == "active").order_by(CareerPath.title)
    ).all()

    goal_role = (goal.target_role if goal else None) or None
    results = []
    for path in paths:
        steps = db.scalars(
            select(CareerPathStep)
            .where(CareerPathStep.path_id == path.id)
            .order_by(CareerPathStep.step_order)
        ).all()
        step_titles = [s.role_title for s in steps]

        # DIRECT only when a role the person actually HELD sits on the path.
        held_pos = None
        for i, t in enumerate(step_titles):
            if t.lower() in {r.lower() for r in roles_held}:
                held_pos = i
                break
        if held_pos is not None:
            view = _path_view(path, steps, held_pos, "direct", goal, roles_held)
            view["anchored_from"] = "history"
            results.append(view)
            continue

        # TRANSITION: the stated GOAL is on (or is the target of) this path
        # but the person has never held a step role. Never presented as a
        # current position.
        goal_pos = None
        if goal_role:
            for i, t in enumerate(step_titles):
                if t.lower() == goal_role.lower():
                    goal_pos = i
                    break
        if goal_pos is not None or (
            goal_role and path.target_role.lower() == goal_role.lower()
        ):
            results.append(
                _transition_view(path, steps, goal_pos, goal_role, roles_held)
            )
            continue

        # EXPLORATORY: shares real skills with the candidate, nothing more.
        overlap = sum(
            1
            for s in steps
            for skill in (s.skills_required or [])
            if str(skill).lower() in skills_map
        )
        if overlap >= 1:
            view = _path_view(path, steps, None, "exploratory", goal, roles_held)
            view["anchored_from"] = "skills"
            results.append(view)

    return {
        "anchor": anchor,
        "anchored_from": (
            "goal"
            if (goal and goal.target_role and anchor == goal.target_role)
            else ("history" if anchor else None)
        ),
        "paths": results[:8],
        "disclaimer": (
            "Paths are advisory steps from the platform catalogue. Reaching a "
            "role depends on real hiring decisions, never on this list."
        ),
    }


def _transition_view(path, steps, goal_pos, goal_role, roles_held) -> Dict:
    """Goal-anchored transition view: never claims a held position."""
    step_titles = [s.role_title for s in steps]
    if goal_pos is None:
        goal_pos = len(steps) - 1  # goal is the path target itself
    return {
        "path": path.title,
        "target_role": path.target_role,
        "classification": "transition",
        "current_step": None,
        "current_held": False,
        "goal_step": step_titles[goal_pos] if goal_pos < len(steps) else None,
        "steps": step_titles,
        "next_step": {
            "role_title": steps[0].role_title,
            "seniority": steps[0].seniority,
            "description": steps[0].description,
            "typical_skills_to_develop": (steps[0].skills_required or [])[:6],
        }
        if steps
        else None,
        "note": (
            "Your history does not yet include this path's roles — this is a "
            "deliberate transition toward your stated goal. The first step is "
            "listed above; nothing here is guaranteed."
        ),
    }


def _path_view(path, steps, position, classification, goal, roles_held) -> Dict:
    if position is not None:
        remaining = steps[position + 1:]
        current_step = steps[position]
        next_step = steps[position + 1] if remaining else None
        gap = None
        if next_step is not None:
            missing = [
                {"skill": s, "status": "missing"}
                for s in (next_step.skills_required or [])
            ]
            gap = {
                "from_role": current_step.role_title,
                "to_role": next_step.role_title,
                "typical_skills_to_develop": (next_step.skills_required or [])[:6],
            }
        return {
            "path": path.title,
            "target_role": path.target_role,
            "classification": classification,
            "current_step": current_step.role_title,
            "steps": [s.role_title for s in steps],
            "next_step": {
                "role_title": next_step.role_title,
                "seniority": next_step.seniority,
                "description": next_step.description,
            }
            if next_step
            else None,
            "gap_to_next_step": gap,
            "note": (
                "You are on this path. Advisory only — not a promise of progression."
            ),
        }
    return {
        "path": path.title,
        "target_role": path.target_role,
        "classification": classification,
        "steps": [s.role_title for s in steps],
        "note": {
            "direct": "Your current/target role anchors this path.",
            "transition": "This path targets your stated career goal — a deliberate transition.",
            "exploratory": "This path shares skills with your profile — explore deliberately.",
        }.get(classification, ""),
    }


# --- Opportunity recommendations ----------------------------------------------


def opportunity_recommendations(
    db: Session,
    person_id: uuid.UUID,
    mode: str = "strong",
    limit: int = 10,
) -> Dict:
    """Explainable opportunity recommendations over active catalogue.

    Modes: strong (80%+), potential (60-79%), transition (moves the
    person toward their goal's path from a lower match), explore (the
    rest of the active catalogue, capped). Every item carries component
    reasons and explicit missing skills — no bare percentage is offered.
    """
    valid_modes = {"strong", "potential", "transition", "explore"}
    if mode not in valid_modes:
        from app.core.errors import InvalidInputError

        raise InvalidInputError(f"mode must be one of {sorted(valid_modes)}")
    person = _person(db, person_id)
    opps = _active_opportunities(db)
    matches = matching.match_all(db, person.id, opps)
    goal = _primary_goal(db, person.id)
    goal_role = (goal.target_role if goal else None) or ""
    experiences = _ordered_experiences(db, person.id)
    current = experiences[0] if experiences else None

    items = []
    for m in matches:
        opp = db.get(Opportunity, uuid.UUID(m["opportunity_id"]))
        if opp is None:
            continue
        item = {
            "opportunity_id": m["opportunity_id"],
            "title": opp.title,
            "company": opp.company_name,
            "location": opp.city or opp.location,
            "country": opp.country,
            "work_mode": opp.work_mode,
            "seniority": opp.seniority,
            "percent": m["percent"],
            "strengths": m.get("strengths", [])[:4],
            "missing_skills": m.get("missing_skills", [])[:6],
            "career_signal": _career_signal(opp, goal_role, current),
        }
        pct = m["percent"]
        if mode == "strong" and pct >= 80:
            items.append(item)
        elif mode == "potential" and 60 <= pct < 80:
            items.append(item)
        elif mode == "transition" and pct < 80 and item["career_signal"]:
            items.append(item)
        elif mode == "explore":
            items.append(item)

    items = items[: max(1, min(limit, 25))]
    return {
        "mode": mode,
        "count": len(items),
        "items": items,
        "note": {
            "strong": "Strong matches: you already cover most stated requirements.",
            "potential": "Potential matches: a meaningful fit with defined gaps to close.",
            "transition": "Career-transition signals: these roles step toward your stated goal.",
            "explore": "Explore: the rest of the active catalogue, for deliberate browsing.",
        }[mode],
        "disclaimer": (
            "Percentages are explainable matching signals computed from the "
            "job requirements and your Work ID — never a hiring guarantee."
        ),
    }


def _career_signal(opp, goal_role: str, current) -> Optional[Dict]:
    """A factual 'why this role moves you' signal — not a guarantee."""
    title_l = (opp.title or "").lower()
    signals = []
    if goal_role and any(
        len(tok) > 3 and tok in title_l for tok in goal_role.lower().split()
    ):
        signals.append("matches your stated target role")
    if current:
        current_l = (current.title or "").lower()
        if current_l and any(len(tok) > 3 and tok in current_l for tok in title_l.split()):
            signals.append("extends your current role family")
        else:
            signals.append("differs from your current role family — a deliberate move")
    opp_level = (opp.seniority or "").lower()
    if opp_level in {"senior", "lead"} and current and current.is_current:
        signals.append("a more senior step than your current position")
    return {"signals": signals[:3]} if signals else None


# --- Application analysis ------------------------------------------------------


def application_analysis(db: Session, person_id: uuid.UUID) -> Dict:
    """Deterministic read of the candidate's own application history.

    Funnel counts, movement rates, stuck applications, and honest
    advice derived from their own data. Never exposes employer notes.
    """
    person = _person(db, person_id)
    apps = db.scalars(
        select(JobApplication).where(JobApplication.person_id == person.id)
    ).all()

    counts: Dict[str, int] = {}
    applied_total = 0
    advanced = 0
    outcomes: Dict[str, int] = {}
    stuck = []
    by_company: Dict[str, int] = {}

    now = utc_now_naive()
    for a in apps:
        counts[a.status] = counts.get(a.status, 0) + 1
        opp = db.get(Opportunity, a.opportunity_id) if a.opportunity_id else None
        company = opp.company_name if opp else "unknown"
        by_company[company] = by_company.get(company, 0) + 1
        if a.status in _APPLIED_OR_LATER:
            applied_total += 1
        if a.status in _ADVANCED_OUTCOMES:
            advanced += 1
        if a.status in _CLOSED_OUTCOMES:
            outcomes[a.status] = outcomes.get(a.status, 0) + 1
        if (
            a.status in {APPLICATION_STATUS_APPLIED, APPLICATION_STATUS_APPLICATION_RECEIVED}
            and a.applied_at
        ):
            age_days = (now - a.applied_at).days
            if age_days >= _STUCK_DAYS:
                stuck.append(
                    {
                        "application_id": str(a.id),
                        "company": company,
                        "title": opp.title if opp else None,
                        "days": age_days,
                    }
                )

    movement_rate = (
        round(advanced / applied_total, 3) if applied_total else None
    )
    company_leaders = sorted(by_company.items(), key=lambda kv: -kv[1])[:5]

    advice: List[str] = []
    if applied_total == 0:
        advice.append("You have not applied to any opportunity yet — start with strong matches.")
    elif movement_rate is not None and movement_rate == 0:
        advice.append(
            "None of your applications have advanced to interview yet. Compare your "
            "missing skills on the roles you applied to and target stronger matches."
        )
    elif movement_rate is not None and movement_rate < 0.3:
        advice.append(
            "Your application-to-interview rate is low. Review the skill gaps on the "
            "roles you applied to; prioritizing roles where you cover the core "
            "requirements usually improves movement."
        )
    if stuck:
        advice.append(
            f"{len(stuck)} application(s) have not moved in {_STUCK_DAYS}+ days. "
            "Consider a follow-up through the platform's communication flow or "
            "refocus effort on roles with stronger fit."
        )
    if not advice:
        advice.append(
            "Keep applying to roles where your skill coverage is strong; consistency "
            "is the main lever visible in your data."
        )

    return {
        "application_count": len(apps),
        "applied_count": applied_total,
        "advanced_count": advanced,
        "status_counts": counts,
        "outcome_counts": outcomes,
        "movement_rate": movement_rate,
        "movement_note": (
            "Share of your applications that reached interview, offer, or acceptance. "
            "This is your data, not an employer judgment."
        ),
        "stuck_applications": stuck[:10],
        "top_companies": [
            {"company": company, "applications": count}
            for company, count in company_leaders
        ],
        "advice": advice[:4],
    }


# --- Action plan ---------------------------------------------------------------


def action_plan(
    db: Session,
    person_id: uuid.UUID,
    weeks: int = 8,
) -> Dict:
    """A structured, suggestion-only career action plan.

    Derived deterministically from the digest + gap analysis: goal,
    current state, gaps, prioritized actions with milestone-shaped next
    steps. Target dates are suggestions for the candidate's own planner —
    nothing executes and nothing is guaranteed.
    """
    digest = profile_digest(db, person_id)
    gaps = skill_gap_analysis(db, person_id)
    goal = _primary_goal(db, person_id)

    actions: List[Dict] = []
    target_role = (goal.target_role if goal else None) or "your target role"

    missing = gaps.get("missing_skills", [])[:3]
    for idx, gap in enumerate(missing):
        actions.append(
            {
                "type": "develop_skill",
                "title": f"Develop: {gap['skill']}",
                "detail": gap.get("note"),
                "target_week": min(idx + 1, weeks),
            }
        )
    partial = gaps.get("partial_skills", [])[:2]
    for idx, gap in enumerate(partial):
        actions.append(
            {
                "type": "deepen_skill",
                "title": f"Deepen toward: {gap['skill']} (related skills only)",
                "detail": gap.get("note"),
                "target_week": min(len(missing) + idx + 1, weeks),
            }
        )

    experiences = _ordered_experiences(db, person_id)
    if not experiences and target_role:
        actions.append(
            {
                "type": "gain_experience",
                "title": "Build experience evidence",
                "detail": (
                    f"Add internships, projects, or volunteer roles that produce "
                    f"'{target_role}'-relevant outcomes you can show."
                ),
                "target_week": 1,
            }
        )

    if not actions:
        actions.append(
            {
                "type": "apply",
                "title": "Focus on strong matches",
                "detail": (
                    "Your skill coverage is solid — apply to strong matches and "
                    "prepare for interviews."
                ),
                "target_week": 1,
            }
        )

    milestone_suggestions = [
        {
            "kind": "skill",
            "title": f"Complete a first pass at '{missing[0]['skill']}'" if missing else "Complete a first application",
            "occurred_on": (date.today() + timedelta(days=14)).isoformat(),
            "suggested": True,
        },
        {
            "kind": "application",
            "title": f"Apply to {min(5, max(1, weeks))} relevant opportunities",
            "occurred_on": (date.today() + timedelta(days=weeks * 7)).isoformat(),
            "suggested": True,
        },
    ]

    return {
        "goal": digest["career_goal"],
        "current_state": {
            "current_position": digest["current_position"],
            "skills_count": len(digest["skills"]["all"]),
        },
        "gap_summary": gaps.get("summary"),
        "actions": actions,
        "milestone_suggestions": milestone_suggestions,
        "note": (
            "This plan is a suggestion generated from your Work ID and goals. "
            "You stay in control: nothing here applies, sends, or changes your "
            "profile without your explicit action."
        ),
    }


# --- Own-data mutations (via tools/REST, person-authorized) --------------------


def create_own_milestone(
    db: Session,
    person_id: uuid.UUID,
    *,
    title: str,
    kind: str,
    occurred_on: Optional[date] = None,
) -> CareerMilestone:
    """Insert a milestone on the caller's OWN career timeline.

    Reuses the same canonical row + ownership the REST jobseeker
    endpoint uses. ``kind`` is a controlled-ish short tag; title is
    the candidate's own words (bounded).
    """
    person = _person(db, person_id)
    title = (title or "").strip()
    if not title or len(title) > 200:
        from app.core.errors import InvalidInputError

        raise InvalidInputError("A milestone title between 1 and 200 characters is required.")
    if len(kind or "") > 32:
        from app.core.errors import InvalidInputError

        raise InvalidInputError("Milestone kind is too long.")
    milestone = CareerMilestone(
        person_id=person.id,
        kind=(kind or "achievement").strip() or "achievement",
        title=title[:200],
        occurred_on=occurred_on or date.today(),
    )
    db.add(milestone)
    db.commit()
    db.refresh(milestone)
    return milestone
