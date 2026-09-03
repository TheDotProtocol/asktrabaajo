"""Opportunity matching engine — explainable, never a bare percentage.

The match is a transparent combination of named components, each with a
reason. ``score`` alone is never presented: callers receive per-component
scores plus human-readable strengths and gaps so the UI can say WHY a job
matches and WHAT would strengthen it. No ML claims are made anywhere — this
is deterministic, rule-based matching that future AI can build on, traceably.
"""
from __future__ import annotations

import uuid
from typing import Dict, List, Optional

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.career import CareerGoal, Opportunity
from app.models.work import Education, Skill, UserSkill, WorkExperience
from app.services import skills_registry

# --- component weights (configurable; sum to 1.0) -----------------------------
MATCH_WEIGHTS = {
    "skills": 0.45,
    "experience": 0.20,
    "goal_alignment": 0.15,
    "education": 0.10,
    "seniority": 0.10,
}

_SKILL_LEVEL_WEIGHT = {
    "beginner": 0.6,
    "intermediate": 1.0,
    "advanced": 1.2,
    "expert": 1.3,
}

_EXPERIENCE_YEARS = {
    "internship": (0, 1),
    "entry": (0, 2),
    "junior": (1, 3),
    "1+ years": (1, 10),
    "2+ years": (2, 10),
    "3+ years": (3, 10),
    "4+ years": (4, 10),
    "5+ years": (5, 10),
    "mid": (2, 6),
    "senior": (4, 10),
    "lead": (6, 10),
}


class CandidateProfile:
    """The subset of a person's Work ID the matcher is allowed to read.

    Deliberately a service-side value object (not ORM rows leaking out) so
    the matcher can never accidentally expose raw personal data.
    """

    def __init__(
        self,
        *,
        skills: Dict[str, str],
        years_experience: float,
        total_roles: int,
        education_levels: List[str],
        industries: List[str],
        seniority_hint: Optional[str] = None,
    ) -> None:
        self.skills = skills
        self.years_experience = years_experience
        self.total_roles = total_roles
        self.education_levels = education_levels
        self.industries = industries
        self.seniority_hint = seniority_hint

    @property
    def normalized_skills(self) -> set:
        return {name.lower() for name in self.skills}


def load_candidate_profile(db: Session, person_id: uuid.UUID) -> CandidateProfile:
    skill_rows = db.execute(
        select(UserSkill, Skill)
        .join(Skill, Skill.id == UserSkill.skill_id)
        .where(UserSkill.person_id == person_id)
    ).all()
    skills: Dict[str, str] = {}
    # Canonicalize self-declared skill names against the taxonomy so a
    # candidate who typed "reactjs" matches an opportunity requiring "React".
    name_map = skills_registry.canonical_name_map(
        db, [skill.name for _, skill in skill_rows]
    )
    for us, skill in skill_rows:
        canonical = name_map.get(skill.name, skill.name)
        skills[canonical.lower()] = us.level or "intermediate"

    experiences = db.scalars(
        select(WorkExperience).where(WorkExperience.person_id == person_id)
    ).all()
    educations = db.scalars(
        select(Education).where(Education.person_id == person_id)
    ).all()
    industries: List[str] = []

    years = 0.0
    for exp in experiences:
        years = max(years, _years_between(exp.start_date, exp.end_date))

    return CandidateProfile(
        skills=skills,
        years_experience=years,
        total_roles=len(experiences),
        education_levels=[e.level for e in educations if e.level],
        industries=industries,
    )


def _years_between(start, end) -> float:
    try:
        end_date = end if end is not None else date.today()
        return max(0.0, (end_date - start).days / 365.25)
    except Exception:
        return 0.0


def load_primary_goal(db: Session, person_id: uuid.UUID) -> Optional[CareerGoal]:
    return db.scalar(
        select(CareerGoal)
        .where(CareerGoal.person_id == person_id, CareerGoal.is_primary.is_(True))
        .order_by(CareerGoal.created_at.desc())
        .limit(1)
    )


# --- components ---------------------------------------------------------------


def skill_component(
    candidate: CandidateProfile,
    opportunity: Opportunity,
    name_map: Optional[Dict[str, str]] = None,
) -> Dict:
    raw_required = [str(s).strip() for s in (opportunity.skills_required or [])]
    if name_map:
        required = [name_map.get(r, r).lower() for r in raw_required]
    else:
        required = [r.lower() for r in raw_required]
    required = [r for r in required if r]
    if not required:
        return {
            "score": 1.0,
            "weight": MATCH_WEIGHTS["skills"],
            "matched": [],
            "missing": [],
            "reason": "No specific skills required.",
        }
    matched, missing = [], []
    for skill in required:
        if skill in candidate.normalized_skills:
            matched.append(skill)
        else:
            missing.append(skill)
    coverage = len(matched) / len(required)
    # Weight matched skills by claimed proficiency.
    boosts = [
        _SKILL_LEVEL_WEIGHT.get(candidate.skills[s], 1.0) for s in matched
    ]
    avg_boost = sum(boosts) / len(boosts) if boosts else 1.0
    score = min(1.0, coverage * min(avg_boost, 1.3))
    if matched and missing:
        reason = (
            f"Matches {len(matched)} of {len(required)} required skills"
            f" ({', '.join(matched[:4])}); missing {', '.join(missing[:3])}."
        )
    elif missing:
        reason = f"Missing required skills: {', '.join(missing[:4])}."
    else:
        reason = f"Covers every required skill ({', '.join(matched[:5])})."
    return {
        "score": round(score, 3),
        "weight": MATCH_WEIGHTS["skills"],
        "matched": matched,
        "missing": missing,
        "reason": reason,
    }


def experience_component(candidate: CandidateProfile, opportunity: Opportunity) -> Dict:
    needed_min, needed_max = _EXPERIENCE_YEARS.get(
        (opportunity.experience_level or "").lower(), (0, 15)
    )
    years = candidate.years_experience
    if years >= needed_min:
        score = min(1.0, 0.6 + 0.1 * min(years - needed_min, 4))
        reason = f"Your {years:.0f}+ years of experience clears the {needed_min}+ requested."
    elif candidate.total_roles >= 1:
        score = 0.5
        reason = (
            f"The role asks for {needed_min}+ years; you have ~{years:.0f} "
            "but relevant role history."
        )
    else:
        score = 0.1
        reason = f"The role asks for {needed_min}+ years of experience."
    return {
        "score": round(score, 3),
        "weight": MATCH_WEIGHTS["experience"],
        "reason": reason,
    }


def education_component(candidate: CandidateProfile, opportunity: Opportunity) -> Dict:
    # Opportunity rarely states hard education requirements in this corpus;
    # education contributes a neutral signal unless a degree is demanded.
    if candidate.education_levels:
        score = 1.0
        reason = "Your education history supports this role."
    elif candidate.years_experience >= 3:
        score = 0.9
        reason = "No degree listed, but your experience carries the requirement."
    else:
        score = 0.6
        reason = "No formal education recorded — consider adding it to your Work ID."
    return {
        "score": round(score, 3),
        "weight": MATCH_WEIGHTS["education"],
        "reason": reason,
    }


def seniority_component(candidate: CandidateProfile, opportunity: Opportunity) -> Dict:
    opp_seniority = (opportunity.seniority or "").lower()
    hints = {"junior": (0, 2), "mid": (2, 6), "senior": (4, 10), "lead": (6, 10)}
    needed_min = hints.get(opp_seniority, (0, 10))[0]
    if candidate.years_experience >= needed_min:
        score = 1.0
        reason = f"Your experience level fits a {opp_seniority or 'mid'} role."
    elif opp_seniority == "senior" and candidate.years_experience >= 2:
        score = 0.7
        reason = "Senior-level role; you have a strong base to grow into it."
    else:
        score = 0.4
        reason = (
            f"This is a {opp_seniority or 'mid'} role — it may stretch your "
            "current level."
        )
    return {
        "score": round(score, 3),
        "weight": MATCH_WEIGHTS["seniority"],
        "reason": reason,
    }


def goal_component(
    candidate: CandidateProfile,
    opportunity: Opportunity,
    goal: Optional[CareerGoal],
) -> Dict:
    if goal is None:
        return {
            "score": 0.6,
            "weight": MATCH_WEIGHTS["goal_alignment"],
            "reason": "Add a career goal to sharpen matching.",
        }
    checks, notes = [], []
    if goal.target_role:
        tokens = goal.target_role.lower().split()
        title = opportunity.title.lower()
        if any(tok in title for tok in tokens if len(tok) > 3):
            checks.append(True)
            notes.append("matches your target role")
        else:
            checks.append(False)
            notes.append(f"targets '{goal.target_role}'")
    if goal.target_industries and opportunity.industry:
        match = any(
            opportunity.industry.lower() in str(ind).lower()
            for ind in goal.target_industries
        )
        checks.append(match)
        notes.append("aligned with your target industries" if match else "outside your listed industries")
    if goal.preferred_work_modes and opportunity.work_mode:
        match = opportunity.work_mode in goal.preferred_work_modes or (
            opportunity.remote_eligible and "remote" in goal.preferred_work_modes
        )
        checks.append(match)
        notes.append("work mode fits your preference" if match else "work mode differs from your preference")
    if goal.open_to_relocation is False and goal.target_locations and opportunity.city:
        match = any(
            opportunity.city.lower() in str(loc).lower() or opportunity.country.lower() in str(loc).lower()
            for loc in goal.target_locations
        )
        checks.append(match)
        notes.append("in a preferred location" if match else "outside your preferred locations")
    if not checks:
        return {
            "score": 0.7,
            "weight": MATCH_WEIGHTS["goal_alignment"],
            "reason": "Goal set — refine it with target roles and locations for sharper matches.",
        }
    score = sum(checks) / len(checks)
    return {
        "score": round(score, 3),
        "weight": MATCH_WEIGHTS["goal_alignment"],
        "reason": "Career goal: " + "; ".join(notes),
    }


def match_opportunity(
    candidate: CandidateProfile,
    opportunity: Opportunity,
    goal: Optional[CareerGoal] = None,
    name_map: Optional[Dict[str, str]] = None,
) -> Dict:
    """One opportunity -> explainable match result."""
    components = {
        "skills": skill_component(candidate, opportunity, name_map=name_map),
        "experience": experience_component(candidate, opportunity),
        "education": education_component(candidate, opportunity),
        "seniority": seniority_component(candidate, opportunity),
        "goal_alignment": goal_component(candidate, opportunity, goal),
    }
    total = round(
        sum(c["score"] * c["weight"] for c in components.values()), 3
    )
    percent = int(round(total * 100))
    gaps = [
        c["reason"]
        for c in components.values()
        if c["score"] < 0.6
    ]
    strengths = [
        c["reason"]
        for c in components.values()
        if c["score"] >= 0.8
    ]
    component_payload = {}
    for key, c in components.items():
        payload = {"score": c["score"], "reason": c["reason"]}
        if key == "skills":
            payload["matched"] = c.get("matched", [])
            payload["missing"] = c.get("missing", [])
        component_payload[key] = payload
    return {
        "opportunity_id": str(opportunity.id),
        "percent": percent,
        "score": total,
        "components": component_payload,
        "strengths": strengths[:4],
        "gaps": gaps[:4],
        "missing_skills": components["skills"].get("missing", []),
    }


def match_all(
    db: Session,
    person_id: uuid.UUID,
    opportunities: List[Opportunity],
) -> List[Dict]:
    candidate = load_candidate_profile(db, person_id)
    goal = load_primary_goal(db, person_id)
    raw_required = {
        str(s).strip()
        for opp in opportunities
        for s in (opp.skills_required or [])
        if str(s).strip()
    }
    name_map = (
        skills_registry.canonical_name_map(db, raw_required) if raw_required else {}
    )
    results = [
        match_opportunity(candidate, opp, goal, name_map=name_map)
        for opp in opportunities
    ]
    results.sort(key=lambda r: -r["score"])
    return results
