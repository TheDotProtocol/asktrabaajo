"""Career development + Career Advisor foundation.

The Advisor here is deliberately NOT a chatbot and makes NO claims it cannot
support. ``advisor_snapshot`` reasons over the person's real Work ID: where
they are, what their strongest skills are, which direction their goal points,
and what demonstrably stands between them and that direction. Every
recommendation is traceable to a Work ID fact — the eventual Athena layer
consumes the same service boundaries and adds conversation on top, never
invention.

Recommendations are ranked by impact and are intentionally few (no course
catalog spam). No 'career guarantees' are ever produced.
"""
from __future__ import annotations

import uuid
from typing import Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.career import CareerGoal, Opportunity
from app.models.enums import EDUCATION_LEVELS
from app.models.work import Credential, Education, Skill, UserSkill, WorkExperience

# Learning/certification suggestions keyed by skill gaps — static catalogue
# entries with a category, so recommendations are concrete but never vendor ads.
_LEARNING_MAP = {
    "python": ("Structured Python track (data or backend)", "course"),
    "typescript": ("TypeScript depth: typing, patterns, tooling", "course"),
    "react": ("React advanced: rendering, state, performance", "course"),
    "node": ("Node.js backend patterns and APIs", "course"),
    "sql": ("SQL analytics and query design", "course"),
    "postgresql": ("PostgreSQL: schema design, indexing, transactions", "course"),
    "aws": ("AWS solutions certification path", "certification"),
    "kubernetes": ("Kubernetes operations certification", "certification"),
    "terraform": ("Infrastructure-as-code with Terraform", "course"),
    "machine learning": ("Practical machine learning specialization", "certification"),
    "pytorch": ("PyTorch deep learning in production", "course"),
    "nlp": ("NLP with transformers in practice", "course"),
    "blockchain": ("Blockchain protocol engineering foundations", "course"),
    "solidity": ("Solidity smart contract development", "course"),
    "rust": ("Systems programming with Rust", "course"),
    "security": ("Applied security engineering path", "certification"),
    "product management": ("Product management essentials", "course"),
    "figma": ("Design systems in Figma", "course"),
    "leadership": ("Engineering leadership and management", "course"),
    "data analysis": ("Data analysis with Python and SQL", "course"),
}

# Typical skill clusters for common seniority targets, used ONLY to produce
# development suggestions when a goal exists — never to fake a match score.
_GOAL_CLUSTERS = {
    "engineer": [
        "python", "typescript", "react", "node", "postgresql", "aws",
        "docker", "kubernetes", "ci/cd", "testing",
    ],
    "engineering manager": [
        "leadership", "people management", "hiring", "technical strategy", "mentoring",
    ],
    "machine learning": [
        "python", "machine learning", "pytorch", "nlp", "statistics", "data analysis",
    ],
    "product manager": [
        "product management", "analytics", "sql", "user research", "a/b testing",
    ],
    "designer": ["figma", "design", "typography", "prototyping", "user research"],
    "analyst": ["data analysis", "sql", "excel", "python", "statistics", "financial modeling"],
    "security": ["security", "penetration testing", "aws", "python", "compliance"],
    "blockchain": ["blockchain", "solidity", "rust", "cryptography", "web3"],
    "cloud": ["aws", "kubernetes", "terraform", "linux", "observability", "python"],
    "data": ["sql", "python", "statistics", "machine learning", "data engineering"],
    "hr": ["hr operations", "recruiting", "compensation", "onboarding", "employee relations"],
}

_EDUCATION_LEVEL_ORDER = {level: i for i, level in enumerate(EDUCATION_LEVELS)}


def collect_skills(db: Session, person_id: uuid.UUID) -> Dict[str, str]:
    rows = db.execute(
        select(UserSkill, Skill)
        .join(Skill, Skill.id == UserSkill.skill_id)
        .where(UserSkill.person_id == person_id)
    ).all()
    return {skill.name.lower(): (us.level or "intermediate") for us, skill in rows}


def _infer_cluster(person_skills: Dict[str, str], goal: CareerGoal) -> Optional[str]:
    if goal.target_role:
        target = goal.target_role.lower()
        for key, _cluster in _GOAL_CLUSTERS.items():
            if key in target:
                return key
    # Infer from strongest current skills.
    for cluster, skills in _GOAL_CLUSTERS.items():
        matched = sum(1 for s in skills if s in person_skills)
        if matched >= 2:
            return cluster
    return None


def advisor_snapshot(db: Session, person_id: uuid.UUID) -> Dict:
    """The Jobseeker Career OS advisor card — evidence-based, no invention."""
    person_skills = collect_skills(db, person_id)
    experiences = db.scalars(
        select(WorkExperience)
        .where(WorkExperience.person_id == person_id)
        .order_by(WorkExperience.start_date.desc())
    ).all()
    educations = db.scalars(
        select(Education).where(Education.person_id == person_id)
    ).all()
    credentials = db.scalars(
        select(Credential).where(Credential.person_id == person_id)
    ).all()
    goal = db.scalar(
        select(CareerGoal)
        .where(CareerGoal.person_id == person_id, CareerGoal.is_primary.is_(True))
        .order_by(CareerGoal.created_at.desc())
        .limit(1)
    )
    opportunities = db.scalars(
        select(Opportunity).where(Opportunity.status == "active").limit(200)
    ).all()

    strongest = sorted(
        person_skills,
        key=lambda s: {"beginner": 0, "intermediate": 1, "advanced": 2, "expert": 3}.get(
            person_skills[s], 1
        ),
        reverse=True,
    )[:5]
    roles_held = [e.title for e in experiences if e.title][:4]
    current = experiences[0] if experiences else None

    # Gap analysis when a goal exists.
    gaps: List[Dict] = []
    if goal:
        cluster = _infer_cluster(person_skills, goal)
        target_skills = _GOAL_CLUSTERS.get(cluster, []) if cluster else []
        if cluster is None and goal.target_role:
            gaps.append(
                {
                    "kind": "role",
                    "title": "Add skills the market expects",
                    "detail": (
                        f"'{goal.target_role}' is your target — add concrete "
                        "skills to your Work ID so matching has evidence to work with."
                    ),
                }
            )
        for skill in target_skills:
            if skill not in person_skills:
                learning = _LEARNING_MAP.get(skill)
                gaps.append(
                    {
                        "kind": "skill",
                        "skill": skill,
                        "title": f"Develop: {skill}",
                        "detail": (
                            learning[0] if learning else "Relevant practical experience."
                        ),
                        "action_type": learning[1] if learning else "experience",
                    }
                )
            if len(gaps) >= 4:
                break
        if goal.target_role and experiences:
            matching_titles = [
                e.title for e in experiences
                if any(tok in (e.title or "").lower() for tok in goal.target_role.lower().split() if len(tok) > 3)
            ]
            if not matching_titles:
                gaps.insert(
                    0,
                    {
                        "kind": "experience",
                        "title": "Bridge toward your target role",
                        "detail": (
                            f"Your history is in {roles_held[0] if roles_held else 'other roles'}; "
                            "look for stretch assignments or projects that produce the "
                            f"'{goal.target_role}' outcomes you can show."
                        ),
                        "action_type": "experience",
                    },
                )

    # Learning recommendations grounded in gaps only (no catalog spam).
    learning: List[Dict] = []
    for gap in gaps:
        if gap.get("kind") == "skill" and gap.get("action_type") in ("course", "certification"):
            learning.append(
                {
                    "skill": gap["skill"],
                    "recommendation": gap["title"],
                    "kind": gap["action_type"],
                }
            )
    learning = learning[:3]

    next_actions: List[str] = []
    if not person_skills:
        next_actions.append("Add at least three skills to your Work ID.")
    if not educations:
        next_actions.append("Record your education so your profile is complete.")
    if not credentials:
        next_actions.append("Add certifications you hold — verification can come later.")
    if goal is None:
        next_actions.append("Set a career goal so the Career Advisor can prioritise for you.")
    if not opportunities:
        next_actions.append("No opportunities are open yet — check back soon.")
    if not next_actions:
        next_actions.append("Your foundation is solid — review recommended opportunities and apply.")

    return {
        "summary": _summary_text(current, roles_held, strongest, goal),
        "current_position": {
            "title": current.title if current else None,
            "company": current.company_name if current else None,
        },
        "roles_held": roles_held,
        "strongest_skills": strongest,
        "career_goal": {
            "id": str(goal.id) if goal else None,
            "title": goal.title if goal else None,
            "target_role": goal.target_role if goal else None,
        },
        "gaps": gaps,
        "learning_recommendations": learning,
        "next_actions": next_actions[:4],
        "disclaimer": (
            "Recommendations are derived from your Work ID and market data. "
            "No career outcome is guaranteed."
        ),
    }


def _summary_text(
    current, roles_held: List[str], strongest: List[str], goal
) -> str:
    if not roles_held and not strongest:
        return "Build out your Work ID — once we know your skills and history, your Career Advisor can guide you."
    bits = []
    if roles_held:
        bits.append(f"your history spans {', '.join(roles_held[:2])}")
    if strongest:
        bits.append(f"your strongest skills are {', '.join(strongest[:3])}")
    if goal and goal.target_role:
        bits.append(f"your stated target is {goal.target_role}")
    return "Based on your Work ID, " + "; ".join(bits) + "."
