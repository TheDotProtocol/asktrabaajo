"""Work DNA service — assessment → structured, explainable dimension profile.

Work DNA is NOT one reductive score and it never makes claims about the
person that the assessment cannot support. ``compute_profile`` maps explicit
answers to named dimensions (with per-dimension confidence). The question set
is versioned; future adaptive engines write new versions through the same
service without schema churn (dimensions are an extensible JSON list).
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, InvalidInputError, NotFoundError
from app.core.timeutil import utc_now_naive
from app.models.career import WorkDnaAnswer, WorkDnaProfile

# Versioned question set (Phase 5 foundation). Keys stay stable across
# versions so answer logs remain comparable. Every option maps to dimension
# contributions with an explicit label.
ASSESSMENT_VERSION = "v1"

QUESTIONS: List[dict] = [
    {
        "key": "problem_solving",
        "question": "When facing a hard problem, you most naturally:",
        "options": [
            {"value": "analyze", "label": "Break it into parts and analyze it"},
            {"value": "build", "label": "Try things and build a solution fast"},
            {"value": "people", "label": "Ask others and align on an approach"},
            {"value": "research", "label": "Research how others solved it"},
        ],
    },
    {
        "key": "work_style",
        "question": "You do your best work when:",
        "options": [
            {"value": "solo_deep", "label": "Left alone for deep, uninterrupted focus"},
            {"value": "collaborative", "label": "Working closely with a small team"},
            {"value": "structured", "label": "Following clear process and structure"},
            {"value": "autonomous", "label": "Given ownership and loose direction"},
        ],
    },
    {
        "key": "communication",
        "question": "In meetings, you are most likely to:",
        "options": [
            {"value": "direct", "label": "Be direct and get to the point"},
            {"value": "diplomatic", "label": "Read the room and build consensus"},
            {"value": "written", "label": "Prefer thinking in writing first"},
            {"value": "visual", "label": "Sketch or show rather than explain"},
        ],
    },
    {
        "key": "risk_tolerance",
        "question": "A risky opportunity with high upside feels:",
        "options": [
            {"value": "exciting", "label": "Exciting — I would go for it"},
            {"value": "calculated", "label": "Interesting only with clear downside limits"},
            {"value": "cautious", "label": "Mostly stressful; I prefer certainty"},
            {"value": "strategic", "label": "Worth it if it fits a long-term plan"},
        ],
    },
    {
        "key": "learning_style",
        "question": "You learn a new skill fastest by:",
        "options": [
            {"value": "doing", "label": "Doing it on a real problem"},
            {"value": "course", "label": "Structured courses or certification"},
            {"value": "mentor", "label": "Having someone experienced guide me"},
            {"value": "reading", "label": "Reading documentation and examples"},
        ],
    },
    {
        "key": "career_motivation",
        "question": "The career outcome you value most is:",
        "options": [
            {"value": "mastery", "label": "Becoming excellent at a craft"},
            {"value": "impact", "label": "Seeing real impact from my work"},
            {"value": "growth", "label": "Fast growth and bigger responsibility"},
            {"value": "freedom", "label": "Freedom, flexibility, and ownership"},
            {"value": "security", "label": "Stability and long-term security"},
        ],
    },
    {
        "key": "leadership_tendency",
        "question": "When a group lacks direction, you typically:",
        "options": [
            {"value": "lead", "label": "Step up and organise the group"},
            {"value": "support", "label": "Support whoever leads and fill gaps"},
            {"value": "expert", "label": "Contribute expertise and stay quiet on process"},
            {"value": "facilitate", "label": "Help the group decide together"},
        ],
    },
    {
        "key": "environment",
        "question": "Your ideal working environment is:",
        "options": [
            {"value": "startup", "label": "Fast-moving and ambiguous"},
            {"value": "corporate", "label": "Well-resourced with clear process"},
            {"value": "remote", "label": "Remote-first and asynchronous"},
            {"value": "impact", "label": "Mission-driven, whatever the size"},
        ],
    },
]

# option value -> dimensions it contributes to
_OPTION_DIMENSIONS: Dict[str, List[str]] = {
    "analyze": ["analytical_thinking"],
    "build": ["builder_mindset"],
    "people": ["collaboration"],
    "research": ["analytical_thinking", "learning_agility"],
    "solo_deep": ["deep_focus"],
    "collaborative": ["collaboration"],
    "structured": ["process_orientation"],
    "autonomous": ["ownership"],
    "direct": ["direct_communication"],
    "diplomatic": ["collaboration", "communication"],
    "written": ["written_communication"],
    "visual": ["visual_communication"],
    "exciting": ["risk_tolerance_high"],
    "calculated": ["measured_risk"],
    "cautious": ["risk_averse"],
    "strategic": ["strategic_orientation"],
    "doing": ["learning_by_doing"],
    "course": ["structured_learning"],
    "mentor": ["guided_learning"],
    "reading": ["self_directed_learning"],
    "mastery": ["craft_motivation"],
    "impact": ["impact_motivation"],
    "growth": ["growth_motivation"],
    "freedom": ["autonomy_motivation"],
    "security": ["stability_motivation"],
    "lead": ["leadership"],
    "support": ["teamwork"],
    "expert": ["craft_motivation"],
    "facilitate": ["facilitation", "leadership"],
    "startup": ["startup_environment"],
    "corporate": ["corporate_environment"],
    "remote": ["remote_environment"],
    "impact": ["mission_environment"],
}

# A human label per dimension so profiles are legible, never a black box.
DIMENSION_LABELS: Dict[str, str] = {
    "analytical_thinking": "Analytical thinking",
    "builder_mindset": "Builder mindset",
    "collaboration": "Collaboration",
    "learning_agility": "Learning agility",
    "deep_focus": "Deep focus",
    "process_orientation": "Process orientation",
    "ownership": "Ownership",
    "direct_communication": "Direct communication",
    "written_communication": "Written communication",
    "visual_communication": "Visual communication",
    "communication": "Communication",
    "risk_tolerance_high": "Comfort with risk",
    "measured_risk": "Measured risk-taking",
    "risk_averse": "Risk caution",
    "strategic_orientation": "Strategic orientation",
    "learning_by_doing": "Learning by doing",
    "structured_learning": "Structured learning",
    "guided_learning": "Guided learning",
    "self_directed_learning": "Self-directed learning",
    "craft_motivation": "Craft mastery motivation",
    "impact_motivation": "Impact motivation",
    "growth_motivation": "Growth motivation",
    "autonomy_motivation": "Autonomy motivation",
    "stability_motivation": "Stability motivation",
    "leadership": "Leadership tendency",
    "teamwork": "Teamwork",
    "facilitation": "Facilitation",
    "startup_environment": "Startup environment fit",
    "corporate_environment": "Corporate environment fit",
    "remote_environment": "Remote environment fit",
    "mission_environment": "Mission-driven environment fit",
}

_WORK_PREFERENCES = {
    "solo_deep": "deep, uninterrupted focus",
    "collaborative": "tight-knit team collaboration",
    "structured": "clear structure and process",
    "autonomous": "ownership with loose direction",
}

_ENVIRONMENT_PREFERENCES = {
    "startup": "fast-moving, ambiguous environments",
    "corporate": "well-resourced, process-rich environments",
    "remote": "remote-first, asynchronous work",
    "impact": "mission-driven organisations",
}

_MOTIVATION_LABELS = {
    "mastery": "mastering a craft",
    "impact": "delivering real impact",
    "growth": "growing fast into bigger responsibility",
    "freedom": "freedom and ownership",
    "security": "stability and long-term security",
}


def list_questions() -> List[dict]:
    """Serve the current versioned question set to the assessment UI."""
    return [
        {"key": q["key"], "question": q["question"], "options": q["options"]}
        for q in QUESTIONS
    ]


def _dimension_contributions(answers: Dict[str, str]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for question_key, option_value in answers.items():
        for dimension in _OPTION_DIMENSIONS.get(option_value, []):
            counts[dimension] = counts.get(dimension, 0) + 1
    return counts


def _preference_profile(answers: Dict[str, str]) -> Dict[str, str]:
    profile: Dict[str, str] = {}
    if answers.get("work_style") in _WORK_PREFERENCES:
        profile["work_preference"] = _WORK_PREFERENCES[answers["work_style"]]
    if answers.get("environment") in _ENVIRONMENT_PREFERENCES:
        profile["environment_preference"] = _ENVIRONMENT_PREFERENCES[answers["environment"]]
    if answers.get("career_motivation") in _MOTIVATION_LABELS:
        profile["career_motivation"] = _MOTIVATION_LABELS[answers["career_motivation"]]
    return profile


def compute_dimensions(answers: Dict[str, str]) -> List[dict]:
    """Compute legible dimension records with confidence (0..1)."""
    counts = _dimension_contributions(answers)
    total_answers = max(len(answers), 1)
    dimensions = [
        {
            "key": key,
            "label": DIMENSION_LABELS.get(key, key.replace("_", " ").title()),
            "signal": round(count / total_answers, 3),
            "confidence": round(min(1.0, 0.4 + 0.15 * count), 3),
        }
        for key, count in sorted(counts.items(), key=lambda kv: -kv[1])
    ]
    return dimensions


def get_current_profile(db: Session, person_id: uuid.UUID) -> Optional[WorkDnaProfile]:
    return db.scalar(
        select(WorkDnaProfile)
        .where(WorkDnaProfile.person_id == person_id)
        .order_by(WorkDnaProfile.created_at.desc())
        .limit(1)
    )


def submit_assessment(
    db: Session,
    person_id: uuid.UUID,
    answers: Dict[str, str],
    user_id: uuid.UUID,
) -> WorkDnaProfile:
    """Validate answers, log them, and write a versioned Work DNA profile.

    Writing a new version supersedes nothing destructive — earlier profiles
    remain stored so the person's development over time is auditable.
    """
    question_keys = {q["key"] for q in QUESTIONS}
    valid_values = {
        q["key"]: {o["value"] for o in q["options"]} for q in QUESTIONS
    }
    unknown_keys = set(answers) - question_keys
    if unknown_keys:
        raise InvalidInputError(
            f"Unknown question keys: {sorted(unknown_keys)}. "
            f"Allowed: {sorted(question_keys)}."
        )
    if len(answers) < 3:
        raise InvalidInputError("Answer at least 3 questions to build a profile.")
    for key, value in answers.items():
        if value not in valid_values[key]:
            raise InvalidInputError(
                f"Invalid answer '{value}' for question '{key}'."
            )

    profile = WorkDnaProfile(
        person_id=person_id,
        version=ASSESSMENT_VERSION,
        source="assessment",
        status="completed",
        dimensions=compute_dimensions(answers),
        completed_at=utc_now_naive(),
    )
    db.add(profile)
    db.flush()
    for question_key, answer in answers.items():
        db.add(
            WorkDnaAnswer(
                person_id=person_id,
                profile_id=profile.id,
                question_key=question_key,
                answer={"value": answer},
            )
        )
    db.commit()
    db.refresh(profile)
    return profile
