"""Interview preparation — deterministic PREPARATION layer (Phase 15).

Scope (per the phase boundary): preparation and practice ONLY. No live
autonomous interviewer, no video/audio, no facial or emotion analysis,
no lie detection, no psychological profiling, no hireability score.

Two deterministic engines, fully code-enforced and test-stable:

- ``generate_questions`` — structured question generation derived from
  the target opportunity's requirements and the candidate's own Work ID.
  Categories are controlled (behavioral, technical, role_specific,
  competency, situational, career_history). AI never invents the employer's
  real questions.
- ``evaluate_answer`` — explainable dimension feedback (relevance,
  structure, evidence, role_knowledge, communication, completeness) with
  per-dimension explanation. It is framed as preparation feedback, never
  as a hiring prediction.

Sessions (``interview_prep_sessions``) are candidate-owned METADATA
containers with lazy expiry and explicit owner deletion. Mock answers are
NEVER persisted by these endpoints: feedback is returned at request time.
When the mock flow runs inside an Athena chat, its turns live in
``athena_messages`` under the existing sanitized retention policy.
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import InvalidInputError, NotFoundError, PermissionDeniedError
from app.core.timeutil import utc_now_naive
from app.models.career import Interview, JobApplication, Opportunity
from app.models.enums import (
    PREP_CATEGORY_BEHAVIORAL,
    PREP_CATEGORIES,
    PREP_CATEGORY_CAREER_HISTORY,
    PREP_CATEGORY_COMPETENCY,
    PREP_CATEGORY_ROLE_SPECIFIC,
    PREP_CATEGORY_SITUATIONAL,
    PREP_CATEGORY_TECHNICAL,
    PREP_DIMENSIONS,
    PREP_SESSION_STATUS_ACTIVE,
    PREP_SESSION_STATUS_COMPLETED,
    PREP_SESSION_STATUS_EXPIRED,
)
from app.models.interview_prep import InterviewPrepSession
from app.services import audit as audit_service
from app.services.career_advisor import person_for_user

# --- Session lifecycle ---------------------------------------------------------

_PREP_INACTIVITY_DAYS = 30  # lazy expiry window; no scheduler dependency


def _now() -> datetime:
    return utc_now_naive()


def _coerce(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is not None:
        dt = dt.astimezone().replace(tzinfo=None)
    return dt


def _owned_session(db: Session, person_id: uuid.UUID, session_id: uuid.UUID) -> InterviewPrepSession:
    session = db.get(InterviewPrepSession, session_id)
    if session is None or session.person_id != person_id:
        raise NotFoundError("Interview preparation session not found.")
    _expire_if_stale(db, session)
    return session


def _expire_if_stale(db: Session, session: InterviewPrepSession) -> None:
    if session.status != PREP_SESSION_STATUS_ACTIVE:
        return
    if session.expires_at and _coerce(session.expires_at) <= _now():
        session.status = PREP_SESSION_STATUS_EXPIRED
        db.commit()


def create_session(
    db: Session,
    user_id: uuid.UUID,
    *,
    opportunity_id: Optional[uuid.UUID] = None,
    application_id: Optional[uuid.UUID] = None,
    interview_id: Optional[uuid.UUID] = None,
    focus_areas: Optional[List[str]] = None,
) -> InterviewPrepSession:
    """A candidate-owned prep session, lazily expiring after inactivity."""
    person = person_for_user(db, user_id)
    if opportunity_id is not None and db.get(Opportunity, opportunity_id) is None:
        raise NotFoundError("Opportunity not found.")
    if application_id is not None:
        app = db.get(JobApplication, application_id)
        if app is None or app.person_id != person.id:
            raise NotFoundError("Application not found.")
    if interview_id is not None:
        interview = db.get(Interview, interview_id)
        if interview is None:
            raise NotFoundError("Interview not found.")
        app = db.get(JobApplication, interview.application_id)
        if app is None or app.person_id != person.id:
            raise PermissionDeniedError("Interview not accessible to this account.")
    if focus_areas is not None:
        cleaned = [str(f).strip()[:60] for f in focus_areas if str(f).strip()]
        focus_areas = cleaned[:6] or None

    now = _now()
    session = InterviewPrepSession(
        person_id=person.id,
        opportunity_id=opportunity_id,
        application_id=application_id,
        interview_id=interview_id,
        status=PREP_SESSION_STATUS_ACTIVE,
        focus_areas=focus_areas,
        last_activity_at=now,
        expires_at=now + timedelta(days=_PREP_INACTIVITY_DAYS),
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    audit_service.record(
        db,
        actor_id=user_id,
        action="interview_prep.session.created",
        resource_type="interview_prep_session",
        resource_id=session.id,
        metadata={
            "opportunity_id": str(opportunity_id) if opportunity_id else None,
            "interview_id": str(interview_id) if interview_id else None,
        },
    )
    db.commit()
    return session


def touch_session(db: Session, session: InterviewPrepSession) -> None:
    """Refresh the lazy-expiry clock on activity."""
    session.last_activity_at = _now()
    session.expires_at = _now() + timedelta(days=_PREP_INACTIVITY_DAYS)


def get_session_for_user(
    db: Session, user_id: uuid.UUID, session_id: uuid.UUID
) -> InterviewPrepSession:
    """One owned session (owner-only; lazily expired before returning)."""
    person = person_for_user(db, user_id)
    return _owned_session(db, person.id, session_id)


def list_owned_sessions(
    db: Session, user_id: uuid.UUID, *, include_completed: bool = True, limit: int = 20
) -> List[InterviewPrepSession]:
    person = person_for_user(db, user_id)
    query = select(InterviewPrepSession).where(InterviewPrepSession.person_id == person.id)
    if not include_completed:
        query = query.where(InterviewPrepSession.status == PREP_SESSION_STATUS_ACTIVE)
    rows = db.scalars(
        query.order_by(InterviewPrepSession.last_activity_at.desc()).limit(
            max(1, min(limit, 100))
        )
    ).all()
    for row in rows:
        _expire_if_stale(db, row)
    return rows


def complete_session(db: Session, user_id: uuid.UUID, session_id: uuid.UUID) -> InterviewPrepSession:
    person = person_for_user(db, user_id)
    session = _owned_session(db, person.id, session_id)
    if session.status == PREP_SESSION_STATUS_ACTIVE:
        session.status = PREP_SESSION_STATUS_COMPLETED
        session.completed_at = _now()
        db.commit()
        db.refresh(session)
        audit_service.record(
            db,
            actor_id=user_id,
            action="interview_prep.session.completed",
            resource_type="interview_prep_session",
            resource_id=session.id,
            metadata={"questions": session.questions_generated},
        )
        db.commit()
    return session


def delete_session(db: Session, user_id: uuid.UUID, session_id: uuid.UUID) -> None:
    """Owner-only deletion (also satisfies the retention/deletion contract)."""
    person = person_for_user(db, user_id)
    session = db.get(InterviewPrepSession, session_id)
    if session is None or session.person_id != person.id:
        raise NotFoundError("Interview preparation session not found.")
    audit_service.record(
        db,
        actor_id=user_id,
        action="interview_prep.session.deleted",
        resource_type="interview_prep_session",
        resource_id=session.id,
        metadata={},
    )
    db.delete(session)
    db.commit()


def session_out(session: InterviewPrepSession) -> Dict:
    return {
        "id": str(session.id),
        "status": session.status,
        "opportunity_id": str(session.opportunity_id) if session.opportunity_id else None,
        "application_id": str(session.application_id) if session.application_id else None,
        "interview_id": str(session.interview_id) if session.interview_id else None,
        "focus_areas": session.focus_areas or [],
        "questions_generated": session.questions_generated,
        "answers_evaluated": session.answers_evaluated,
        "created_at": session.created_at.isoformat() if session.created_at else None,
        "expires_at": session.expires_at.isoformat() if session.expires_at else None,
        "completed_at": session.completed_at.isoformat() if session.completed_at else None,
    }


# --- Question generation -------------------------------------------------------

_BEHAVIORAL_PROMPTS = [
    ("Tell me about a time you handled a difficult situation at work. What did you do, and what was the outcome?", "resilience"),
    ("Describe a time you had to persuade someone to support your idea.", "influence"),
    ("Give an example of a goal you reached through careful planning.", "planning"),
    ("Tell me about a time you received tough feedback. How did you respond?", "coachability"),
    ("Describe a situation where you had to adapt to a significant change.", "adaptability"),
    ("Tell me about a time you worked under pressure to meet a deadline.", "execution"),
    ("Describe a time you made a mistake. What did you learn?", "ownership"),
    ("Give an example of when you went beyond your job description.", "initiative"),
    ("Tell me about a time you resolved a conflict with a colleague.", "collaboration"),
    ("Describe a time you had to make a decision with incomplete information.", "judgment"),
]

_SITUATIONAL_PROMPTS = [
    ("Your team is falling behind on a critical deadline. What is your approach?", "execution"),
    ("A stakeholder changes a requirement after work has started. How do you respond?", "adaptability"),
    ("You notice a quality problem in something about to ship. What do you do?", "judgment"),
    ("Two priorities demand your time and both are urgent. How do you decide?", "prioritization"),
    ("A teammate is underperforming and it affects you. How do you handle it?", "collaboration"),
]

# Competency prompts are filled from the candidate's own skills.
_COMPETENCY_TEMPLATE = (
    "Give a concrete example that demonstrates your skill in {skill}. What did you do, "
    "and what measurable outcome did it produce?"
)

_CAREER_HISTORY_PROMPTS = [
    ("Walk me through your career so far. What choices did you make and why?",
     "career_narrative"),
    ("What are you most proud of in your current or most recent role?", "achievement"),
    ("Why are you interested in this role, and how does it fit your longer-term direction?",
     "motivation"),
]

_STRUCTURE_MARKERS = {
    "situation": ("situation", "context", "background", "at the time", "i was working"),
    "task": ("task", "goal", "objective", "i needed to", "my responsibility"),
    "action": ("action", "i did", "i decided", "i implemented", "i built", "i led",
               "i created", "i introduced", "i took", "i drove"),
    "result": ("result", "outcome", "impact", "improved", "increased", "reduced",
               "saved", "delivered", "launched", "achieved"),
}
_EVIDENCE_PATTERN = re.compile(r"\b\d[\d,.]*\s*(%|percent|k|m|million|x|users|people|revenue|cost|time)?\b", re.I)
_OUTCOME_VERBS = ("improved", "increased", "reduced", "saved", "delivered", "launched",
                  "grew", "cut", "doubled", "shipped", "won", "built", "led", "created")


def _target_context(db: Session, session: InterviewPrepSession) -> Dict:
    """Factual prep context from the anchored opportunity (no invention)."""
    out: Dict = {}
    opp_id = session.opportunity_id
    if opp_id is None and session.application_id is not None:
        app = db.get(JobApplication, session.application_id)
        opp_id = app.opportunity_id if app else None
    if opp_id is not None:
        opp = db.get(Opportunity, opp_id)
        if opp is not None:
            out["opportunity"] = {
                "id": str(opp.id),
                "title": opp.title,
                "company": opp.company_name,
                "summary": (opp.summary or "")[:600],
                "description": (opp.description or "")[:1200],
                "skills_required": opp.skills_required or [],
                "seniority": opp.seniority,
                "industry": opp.industry,
            }
    return out


def generate_questions(
    db: Session,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    *,
    count: int = 5,
    categories: Optional[List[str]] = None,
) -> Dict:
    """Structured, deterministic question generation for one prep session.

    Returns the session (freshly expired/activity-touched) plus a list of
    questions: ``question``, ``category``, ``competency``, ``difficulty``,
    ``reason``, ``target_skill``, ``suggested_answer_dimensions``.
    """
    person = person_for_user(db, user_id)
    session = _owned_session(db, person.id, session_id)
    if session.status != PREP_SESSION_STATUS_ACTIVE:
        raise InvalidInputError(
            f"This preparation session is {session.status} — start a new one."
        )
    count = max(1, min(count or 5, 10))
    if categories is not None:
        bad = set(categories) - PREP_CATEGORIES
        if bad:
            raise InvalidInputError(f"Unknown question categories: {sorted(bad)}")
        requested = [c for c in categories if c in PREP_CATEGORIES]
    else:
        requested = [
            PREP_CATEGORY_BEHAVIORAL,
            PREP_CATEGORY_TECHNICAL,
            PREP_CATEGORY_ROLE_SPECIFIC,
            PREP_CATEGORY_COMPETENCY,
            PREP_CATEGORY_SITUATIONAL,
            PREP_CATEGORY_CAREER_HISTORY,
        ]

    context = _target_context(db, session)
    opp = context.get("opportunity")
    skills_required = [str(s) for s in (opp or {}).get("skills_required", [])]
    skills_map = _own_skills(db, person.id)
    own_skill_names = list(skills_map.keys())

    questions: List[Dict] = []
    seen: set = set()

    def _push(category, question, competency, target_skill=None, difficulty="medium",
              reason=""):
        key = question.lower().strip()
        if key in seen or len(questions) >= count:
            return
        seen.add(key)
        questions.append(
            {
                "question": question,
                "category": category,
                "competency": competency,
                "difficulty": difficulty,
                "reason": reason,
                "target_skill": target_skill,
                "suggested_answer_dimensions": _dimension_hint(category),
            }
        )

    # 1. Technical — only when the role actually lists skills.
    if PREP_CATEGORY_TECHNICAL in requested and skills_required:
        for skill in skills_required[:3]:
            if len(questions) >= count:
                break
            _push(
                PREP_CATEGORY_TECHNICAL,
                f"The role lists {skill} as a requirement. Walk me through a real "
                f"project where you used {skill}: what you built, the decisions you "
                "made, and the outcome.",
                "technical_depth",
                target_skill=skill,
                difficulty="hard",
                reason=f"Directly exercises the {skill} requirement stated in the job.",
            )

    # 2. Role-specific — from the job title/summary (facts only).
    if PREP_CATEGORY_ROLE_SPECIFIC in requested and opp:
        title = (opp.get("title") or "this role")
        _push(
            PREP_CATEGORY_ROLE_SPECIFIC,
            f"Looking at the {title} role at {opp.get('company')}: which part of your "
            "experience best prepares you for it, and where would you need to ramp up?",
            "role_fit",
            difficulty="medium",
            reason="Grounded in the actual posted role, not invented company process.",
        )
        _push(
            PREP_CATEGORY_ROLE_SPECIFIC,
            f"How would you prioritise your first 30 days in this {title} role?",
            "ramp_planning",
            difficulty="hard",
            reason="Tests how you translate the posted responsibilities into action.",
        )

    # 3. Competency — from the candidate's OWN skills.
    if PREP_CATEGORY_COMPETENCY in requested and own_skill_names:
        for skill in own_skill_names[:3]:
            if len(questions) >= count:
                break
            _push(
                PREP_CATEGORY_COMPETENCY,
                _COMPETENCY_TEMPLATE.format(skill=skill),
                "skill_evidence",
                target_skill=skill,
                difficulty="medium",
                reason=f"Asks you to evidence a skill you claim on your Work ID ({skill}).",
            )

    # 4. Behavioral / situational / career-history pools.
    behavioral = [
        b for b in _BEHAVIORAL_PROMPTS if b not in seen
    ]
    for prompt, competency in behavioral:
        if len(questions) >= count:
            break
        _push(
            PREP_CATEGORY_BEHAVIORAL, prompt, competency,
            difficulty="medium",
            reason="Standard behavioral probe — answer with a real, structured example.",
        )

    situational = [s for s in _SITUATIONAL_PROMPTS if s not in seen]
    for prompt, competency in situational:
        if len(questions) >= count:
            break
        _push(
            PREP_CATEGORY_SITUATIONAL, prompt, competency,
            difficulty="hard",
            reason="Hypothetical scenario testing judgment without a 'right' answer.",
        )

    for prompt, competency in _CAREER_HISTORY_PROMPTS:
        if len(questions) >= count:
            break
        _push(
            PREP_CATEGORY_CAREER_HISTORY, prompt, competency,
            difficulty="easy",
            reason="Opens your narrative — grounded in your real history, not an interview script.",
        )

    session.questions_generated = (session.questions_generated or 0) + len(questions)
    touch_session(db, session)
    db.commit()
    db.refresh(session)

    return {
        "session_id": str(session.id),
        "count": len(questions),
        "questions": questions,
        "note": (
            "Questions are generated from the posted role requirements and your "
            "Work ID. They are preparation practice — the employer may ask "
            "different questions."
        ),
    }


def _dimension_hint(category: str) -> List[str]:
    base = ["relevance", "structure", "evidence", "completeness"]
    if category == PREP_CATEGORY_TECHNICAL:
        return ["role_knowledge", "relevance", "structure", "evidence"]
    if category == PREP_CATEGORY_BEHAVIORAL:
        return ["structure", "evidence", "relevance", "completeness"]
    return base


def _own_skills(db: Session, person_id: uuid.UUID) -> Dict[str, str]:
    from app.models.work import Skill, UserSkill

    rows = db.execute(
        select(UserSkill, Skill).join(Skill, Skill.id == UserSkill.skill_id).where(
            UserSkill.person_id == person_id
        )
    ).all()
    return {skill.name.lower(): (us.level or "intermediate") for us, skill in rows}


# --- Answer evaluation ---------------------------------------------------------


def evaluate_answer(
    db: Session,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    *,
    question: str,
    answer: str,
) -> Dict:
    """Deterministic, explainable feedback on one mock answer.

    Six dimensions scored 0..1 with plain-language explanations, plus
    strengths, improvement areas, and a stronger-response pointer.
    Never a hireability probability — explicitly framed as preparation
    feedback.
    """
    person = person_for_user(db, user_id)
    session = _owned_session(db, person.id, session_id)
    if session.status != PREP_SESSION_STATUS_ACTIVE:
        raise InvalidInputError(
            f"This preparation session is {session.status} — start a new one."
        )
    answer = (answer or "").strip()
    if not answer:
        raise InvalidInputError("An answer is required for evaluation.")
    if len(answer) > 6000:
        raise InvalidInputError("Answer is too long (max 6000 characters).")

    context = _target_context(db, session)
    opp = context.get("opportunity")
    required_skills = [str(s).lower() for s in (opp or {}).get("skills_required", [])]

    # --- dimension scores (deterministic heuristics, all explainable) ---------
    dims = {}

    # relevance: does the answer engage the question's subject?
    question_terms = _significant_terms(question, min_len=4)
    hit_terms = [t for t in question_terms if t in answer.lower()]
    dims["relevance"] = min(1.0, 0.35 + 0.65 * (len(hit_terms) / max(1, len(question_terms))))

    # structure: presence of situation/task/action/result markers.
    lower = answer.lower()
    found_markers = [
        section for section, keys in _STRUCTURE_MARKERS.items()
        if any(k in lower for k in keys)
    ]
    dims["structure"] = min(1.0, len(found_markers) / 4.0 + (0.2 if len(found_markers) == 4 else 0.0))

    # evidence: quantified outcomes and outcome verbs.
    has_numbers = bool(_EVIDENCE_PATTERN.search(answer))
    has_outcome_verbs = any(v in lower for v in _OUTCOME_VERBS)
    dims["evidence"] = min(1.0, (0.5 if has_numbers else 0.0) + (0.5 if has_outcome_verbs else 0.0))

    # role_knowledge: mentions of skills required by the posted role.
    mentioned = [s for s in required_skills if s in lower]
    dims["role_knowledge"] = (
        min(1.0, len(mentioned) / max(1, len(required_skills)))
        if required_skills
        else 0.6  # no stated skill requirements -> neutral, explained
    )

    # communication: word count band + sentence rhythm (deterministic proxy).
    words = len(answer.split())
    sentences = max(1, len(re.findall(r"[.!?]+", answer)))
    if 60 <= words <= 400:
        comm = 0.9
        comm_reason = f"Clear length for a spoken answer (~{words} words)."
    elif words < 30:
        comm = 0.3
        comm_reason = "Very short — the interviewer would not have enough to assess."
    elif words > 600:
        comm = 0.5
        comm_reason = "Long for a spoken answer — tighten to keep the interviewer engaged."
    else:
        comm = 0.7
        comm_reason = "Reasonable length; watch pacing."
    dims["communication"] = comm

    # completeness: does it answer the full question (question length proxy +
    # covers action + result)?
    completeness = 0.4
    reasons = []
    if "action" in found_markers:
        completeness += 0.3
    else:
        reasons.append("no explicit action")
    if "result" in found_markers:
        completeness += 0.3
    else:
        reasons.append("no stated result")
    dims["completeness"] = min(1.0, completeness)

    # --- assemble -------------------------------------------------------------
    dim_payload = {}
    for name in sorted(PREP_DIMENSIONS):
        score = dims.get(name, 0.5)
        dim_payload[name] = {
            "score": round(score, 2),
            "explanation": _dimension_explanation(name, score, lower, required_skills),
        }

    strengths = [
        name for name, d in dim_payload.items() if d["score"] >= 0.7
    ]
    improvements = [
        name for name, d in dim_payload.items() if d["score"] < 0.5
    ]

    session.answers_evaluated = (session.answers_evaluated or 0) + 1
    touch_session(db, session)
    db.commit()
    db.refresh(session)

    return {
        "session_id": str(session.id),
        "dimensions": dim_payload,
        "what_you_did_well": [dim_payload[n]["explanation"] for n in strengths[:3]] or [
            "Keep practicing — a full structured example will bring the scores up."
        ],
        "what_was_missing": [
            dim_payload[n]["explanation"] for n in improvements[:3]
        ],
        "how_to_improve": _improvement_guidance(improvements, found_markers),
        "stronger_response_pointer": _stronger_pointer(answer),
        "disclaimer": (
            "This is preparation feedback on structure and evidence — not a "
            "prediction of interview success or hiring."
        ),
    }


def _significant_terms(text: str, min_len: int = 4) -> List[str]:
    stop = {
        "about", "there", "their", "which", "would", "should", "could", "what", "when",
        "where", "how", "your", "with", "from", "that", "this", "have", "been", "were",
        "tell", "time", "worked", "handle", "doing", "give", "example", "describe",
        "situation", "something", "meet", "making", "asked", "look", "started", "under",
    }
    return sorted(
        {
            t
            for t in re.findall(r"[a-z]{3,}", text.lower())
            if t not in stop and len(t) >= min_len
        }
    )


def _dimension_explanation(name, score: float, lower: str, required_skills) -> str:
    if name == "relevance":
        if score >= 0.7:
            return "Your answer engages the core of the question."
        return "Your answer only partially touches what the question asks."
    if name == "structure":
        if score >= 0.7:
            return "Strong structure — you moved through a clear sequence."
        return "Structure was thin; a Situation→Task→Action→Result shape helps."
    if name == "evidence":
        if score >= 0.7:
            return "Good use of concrete outcomes or measurable results."
        return "Add numbers or a measurable outcome to make the example land."
    if name == "role_knowledge":
        if not required_skills:
            return "No stated skill requirements for the target role — neutral signal."
        if score >= 0.7:
            return "You referenced skills the role actually asks for."
        return f"Mention the role's stated skills where true ({', '.join(required_skills[:3])})."
    if name == "communication":
        return "Clear, well-paced delivery." if score >= 0.7 else (
            "Tighten the answer for spoken delivery."
        )
    if name == "completeness":
        if score >= 0.7:
            return "The answer covers what happened AND what resulted."
        return "Complete the loop: state your action and its result."
    return "Neutral."


def _improvement_guidance(improvements: List[str], found_markers) -> List[str]:
    guidance: List[str] = []
    if "structure" in improvements or "completeness" in improvements:
        guidance.append(
            "Use the STAR shape: brief Situation, your Task, the Actions you took, "
            "and a concrete Result."
        )
    if "evidence" in improvements:
        guidance.append("Quantify: percentages, counts, time saved, revenue moved.")
    if "relevance" in improvements:
        guidance.append("Answer the actual question first, then add context.")
    if "role_knowledge" in improvements:
        guidance.append("Connect your example to the skills the role requires.")
    if not guidance:
        guidance.append("Solid answer — practise delivering it concisely out loud.")
    return guidance[:3]


def _stronger_pointer(answer: str) -> str:
    if len(answer.split()) < 60:
        return "A stronger version gives one complete example with a beginning, middle, and measurable end — roughly a minute of speaking."
    return "A stronger version ends by naming the outcome you produced and what you learned from it."
