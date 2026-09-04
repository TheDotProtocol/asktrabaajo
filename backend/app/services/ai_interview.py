"""AI Interview Engine — controlled Athena-conducted interviews (Phase 16).

The engine orchestrates an employer-configured, candidate-owned AI
interview from configuration through consent, a deterministic question
plan, adaptive follow-ups, structured evaluation, completion report and
an employer human decision. It NEVER makes the final employment decision.

Architecture boundaries (non-negotiable, code-enforced):

- The candidate entry path requires the SHA-256 entry-token match on
  every call; a session URL cannot be guessed and replay needs the token.
- State transitions are explicit (``AI_INTERVIEW_TRANSITIONS``); the
  engine rejects impossible transitions and audits every one.
- The question plan is generated deterministically, grounded in the
  posted opportunity requirements + the candidate's own Work ID, and
  passes a prohibited-topic gate (protected characteristics and
  unrelated sensitive personal topics are never asked).
- Answers are evaluated on explainable dimensions; RAW ANSWER TEXT IS
  NEVER PERSISTED (only dimension scores, strengths/improvements and
  objective evidence markers).
- Integrity signals are objective session-level events, bounded, labeled
  as review signals, and never affect evaluation or decisions.
- The employer retains the decision (advance/reject/hold/follow-up/
  human interview); the AI only produces an AI-assisted report that is
  explicitly marked human-review-required.
- No facial emotion analysis, no lie detection, no protected-characteristic
  inference — those capabilities do not exist anywhere in the platform.
"""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import InvalidInputError, NotFoundError, PermissionDeniedError
from app.core.timeutil import to_utc_naive, utc_now_naive
from app.models.ai_interview import (
    AiInterviewEvaluation,
    AiInterviewQuestion,
    AiInterviewReport,
    AiInterviewSession,
)
from app.models.career import Interview, JobApplication, Opportunity
from app.models.identity import PersonProfile
from app.models.enums import (
    AI_EVAL_DIMENSIONS,
    AI_FOLLOWUP_TYPE_DEPTH,
    AI_FOLLOWUP_TYPE_EVIDENCE,
    AI_FOLLOWUP_TYPE_EXAMPLE,
    AI_FOLLOWUP_TYPE_SCENARIO,
    AI_FOLLOWUP_TYPE_TECHNICAL_DETAIL,
    AI_INTERVIEW_DECISIONS,
    AI_INTERVIEW_STATUS_CANCELLED,
    AI_INTERVIEW_STATUS_COMPLETED,
    AI_INTERVIEW_STATUS_CONSENT_REQUIRED,
    AI_INTERVIEW_STATUS_EXPIRED,
    AI_INTERVIEW_STATUS_FAILED,
    AI_INTERVIEW_STATUS_IN_PROGRESS,
    AI_INTERVIEW_STATUS_PAUSED,
    AI_INTERVIEW_STATUS_READY,
    AI_INTERVIEW_STATUS_SCHEDULED,
    AI_INTERVIEW_TRANSITIONS,
    AI_INTERVIEW_TYPE_BEHAVIORAL,
    AI_INTERVIEW_TYPE_COMPETENCY,
    AI_INTERVIEW_TYPE_MIXED,
    AI_INTERVIEW_TYPE_ROLE_SPECIFIC,
    AI_INTERVIEW_TYPE_SCREENING,
    AI_INTERVIEW_TYPE_TECHNICAL,
    AI_INTEGRITY_SIGNAL_TYPES,
    AUDIT_ACTION_AI_INTERVIEW_CANCELLED,
    AUDIT_ACTION_AI_INTERVIEW_COMPLETED,
    AUDIT_ACTION_AI_INTERVIEW_CONSENT_GRANTED,
    AUDIT_ACTION_AI_INTERVIEW_CONSENT_WITHDRAWN,
    AUDIT_ACTION_AI_INTERVIEW_CREATED,
    AUDIT_ACTION_AI_INTERVIEW_DECISION_RECORDED,
    AUDIT_ACTION_AI_INTERVIEW_EXPIRED,
    AUDIT_ACTION_AI_INTERVIEW_INTEGRITY_SIGNAL,
    AUDIT_ACTION_AI_INTERVIEW_INVITED,
    AUDIT_ACTION_AI_INTERVIEW_PAUSED,
    AUDIT_ACTION_AI_INTERVIEW_PLAN_GENERATED,
    AUDIT_ACTION_AI_INTERVIEW_QUESTION_ASKED,
    AUDIT_ACTION_AI_INTERVIEW_REPORT_GENERATED,
    AUDIT_ACTION_AI_INTERVIEW_REPORT_VIEWED,
    AUDIT_ACTION_AI_INTERVIEW_RESPONSE_EVALUATED,
    AUDIT_ACTION_AI_INTERVIEW_RESUMED,
    AUDIT_ACTION_AI_INTERVIEW_STARTED,
    NOTIFICATION_KIND_INTERVIEW,
    PREP_CATEGORY_BEHAVIORAL,
    PREP_CATEGORY_CAREER_HISTORY,
    PREP_CATEGORY_COMPETENCY,
    PREP_CATEGORY_ROLE_SPECIFIC,
    PREP_CATEGORY_SITUATIONAL,
    PREP_CATEGORY_TECHNICAL,
)
from app.models.talent import OpportunityRequirement
from app.services import audit as audit_service
from app.services import events
from app.services import notifications
from app.services.career_advisor import person_for_user
from app.services.media import build_media_profile

# --- Session lifecycle helpers --------------------------------------------------

_INVITE_WINDOW_DAYS = 7
_MAX_INTEGRITY_SIGNALS = 50
_MAX_QUESTIONS = 10
_MAX_FOLLOWUPS_PER_SESSION = 3
_ENTRY_TOKEN_BYTES = 24


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _token_matches(stored_hash: str, token: str) -> bool:
    return hmac.compare_digest(stored_hash, _hash_token(token))


def _transition(session: AiInterviewSession, target: str) -> None:
    allowed = AI_INTERVIEW_TRANSITIONS.get(session.status, set())
    if target not in allowed:
        raise InvalidInputError(
            f"Invalid interview state transition {session.status} -> {target}."
        )
    session.status = target


def _lazy_expire(db: Session, session: AiInterviewSession) -> bool:
    """Deterministic lazy expiry — correctness never depends on a scheduler.

    Returns True when the session was transitioned to ``expired``.
    """
    if session.status in {
        AI_INTERVIEW_STATUS_COMPLETED,
        AI_INTERVIEW_STATUS_CANCELLED,
        AI_INTERVIEW_STATUS_EXPIRED,
        AI_INTERVIEW_STATUS_FAILED,
    }:
        return False
    if session.expires_at is None or to_utc_naive(session.expires_at) <= utc_now_naive():
        if session.status in {
            AI_INTERVIEW_STATUS_IN_PROGRESS,
            AI_INTERVIEW_STATUS_PAUSED,
        }:
            # A live session past its invite window but within the time
            # budget may still be completed by the time-budget check; only
            # pre-start statuses hard-expire on the invite window.
            return False
        if session.status in {
            AI_INTERVIEW_STATUS_SCHEDULED,
            AI_INTERVIEW_STATUS_CONSENT_REQUIRED,
            AI_INTERVIEW_STATUS_READY,
        }:
            _transition(session, AI_INTERVIEW_STATUS_EXPIRED)
            audit_service.record(
                db,
                actor_id=None,
                action=AUDIT_ACTION_AI_INTERVIEW_EXPIRED,
                resource_type="ai_interview_session",
                resource_id=str(session.id),
                organization_id=session.organization_id,
            )
            return True
    return False


def _time_budget_exhausted(session: AiInterviewSession) -> bool:
    if session.started_at is None:
        return False
    elapsed = utc_now_naive() - to_utc_naive(session.started_at)
    return elapsed >= timedelta(minutes=session.duration_minutes)


def _get_session(db: Session, session_id: uuid.UUID) -> AiInterviewSession:
    session = db.get(AiInterviewSession, session_id)
    if session is None:
        raise NotFoundError("Interview session not found.")
    return session


def require_org_session(
    db: Session, session_id: uuid.UUID, organization_id: uuid.UUID
) -> AiInterviewSession:
    """Return the session only when it belongs to ``organization_id``."""
    session = _get_session(db, session_id)
    if session.organization_id != organization_id:
        raise PermissionDeniedError(
            "This interview does not belong to your organization."
        )
    return session


def _get_session_by_token(db: Session, entry_token: str) -> AiInterviewSession:
    """Resolve a session by its entry-token hash (no existence oracle)."""
    session = db.scalar(
        select(AiInterviewSession).where(
            AiInterviewSession.entry_token_hash == _hash_token(entry_token)
        )
    )
    if session is None:
        raise PermissionDeniedError("Invalid interview entry token.")
    return session


def _claim_candidate(
    db: Session, user_id: uuid.UUID, session_id: uuid.UUID, entry_token: str
) -> AiInterviewSession:
    """Candidate-side gate: token must match AND belong to the caller's person."""
    session = _get_session(db, session_id)
    if not _token_matches(session.entry_token_hash, entry_token):
        raise PermissionDeniedError("Invalid interview entry token.")
    person = person_for_user(db, user_id)
    if person.id != session.candidate_person_id:
        raise PermissionDeniedError("This interview does not belong to your profile.")
    return session


def _candidate_user_id(db: Session, session: AiInterviewSession) -> Optional[uuid.UUID]:
    person = db.get(PersonProfile, session.candidate_person_id)
    return person.user_id if person else None


def _requirement_texts(db: Session, opportunity_id: Optional[uuid.UUID]) -> List[str]:
    if opportunity_id is None:
        return []
    rows = db.scalars(
        select(OpportunityRequirement.raw_text).where(
            OpportunityRequirement.opportunity_id == opportunity_id
        )
    ).all()
    return [r for r in rows if r][:12]


# --- Employer-facing configuration ----------------------------------------------

def create_session(
    db: Session,
    user_id: uuid.UUID,
    *,
    organization_id: uuid.UUID,
    candidate_person_id: uuid.UUID,
    application_id: Optional[uuid.UUID] = None,
    opportunity_id: Optional[uuid.UUID] = None,
    interview_id: Optional[uuid.UUID] = None,
    interview_type: str = AI_INTERVIEW_TYPE_SCREENING,
    duration_minutes: int = 30,
    question_count: int = 5,
    difficulty: str = "medium",
    language: str = "en",
    competencies: Optional[List[str]] = None,
    evaluation_dimensions: Optional[List[str]] = None,
    introduction: Optional[str] = None,
    closing: Optional[str] = None,
    voice_enabled: bool = False,
    video_enabled: bool = False,
    consent_required: bool = True,
) -> Tuple[AiInterviewSession, str]:
    """Create an employer-configured AI interview. Returns (session, entry_token).

    The plaintext entry token is returned exactly once; only its SHA-256
    hash is stored.
    """
    if interview_type not in {
        AI_INTERVIEW_TYPE_SCREENING,
        AI_INTERVIEW_TYPE_BEHAVIORAL,
        AI_INTERVIEW_TYPE_COMPETENCY,
        AI_INTERVIEW_TYPE_ROLE_SPECIFIC,
        AI_INTERVIEW_TYPE_TECHNICAL,
        AI_INTERVIEW_TYPE_MIXED,
    }:
        raise InvalidInputError(f"Unknown interview type '{interview_type}'.")
    duration_minutes = max(10, min(int(duration_minutes), 120))
    question_count = max(1, min(int(question_count), _MAX_QUESTIONS))
    if difficulty not in {"easy", "medium", "hard"}:
        raise InvalidInputError("difficulty must be easy, medium or hard.")
    if language not in {"en", "es", "fr", "de", "pt", "hi"}:
        raise InvalidInputError("Unsupported interview language.")
    competency_list = [str(c).strip()[:80] for c in (competencies or []) if str(c).strip()]
    _reject_prohibited_config(competency_list, introduction, closing)
    if evaluation_dimensions is not None:
        bad = set(evaluation_dimensions) - AI_EVAL_DIMENSIONS
        if bad:
            raise InvalidInputError(f"Unknown evaluation dimensions: {sorted(bad)}")

    # Tenant grounding: at least one anchor, and every anchor must belong
    # to this organization.
    if application_id is None and opportunity_id is None:
        raise InvalidInputError(
            "An application or opportunity anchor is required."
        )
    resolved_opp_id = opportunity_id
    resolved_app_id = application_id
    if application_id is not None:
        app = db.get(JobApplication, application_id)
        if app is None:
            raise NotFoundError("Application not found.")
        resolved_opp_id = app.opportunity_id
        resolved_app_id = app.id
        if app.person_id != candidate_person_id:
            raise InvalidInputError(
                "The application does not belong to the selected candidate."
            )
    if resolved_opp_id is not None:
        opp = db.get(Opportunity, resolved_opp_id)
        if opp is None:
            raise NotFoundError("Opportunity not found.")
        if opp.company_id != organization_id:
            raise PermissionDeniedError(
                "The opportunity does not belong to this organization."
            )
    if interview_id is not None:
        interview = db.get(Interview, interview_id)
        if interview is None:
            raise NotFoundError("Interview not found.")
        if interview.application_id != resolved_app_id:
            raise InvalidInputError(
                "The interview anchor does not match the application."
            )

    token = secrets.token_urlsafe(_ENTRY_TOKEN_BYTES)
    session = AiInterviewSession(
        organization_id=organization_id,
        application_id=resolved_app_id,
        opportunity_id=resolved_opp_id,
        interview_id=interview_id,
        candidate_person_id=candidate_person_id,
        created_by_user_id=user_id,
        interview_type=interview_type,
        status=AI_INTERVIEW_STATUS_SCHEDULED,
        language=language,
        duration_minutes=duration_minutes,
        question_count=question_count,
        difficulty=difficulty,
        competencies=competency_list or None,
        evaluation_dimensions=list(evaluation_dimensions) if evaluation_dimensions else None,
        introduction=introduction,
        closing=closing,
        media_profile=build_media_profile(
            interview_type=interview_type,
            language=language,
            voice_enabled=voice_enabled,
            video_enabled=video_enabled,
        ).as_dict(),
        consent_required=consent_required,
        entry_token_hash=_hash_token(token),
        expires_at=utc_now_naive() + timedelta(days=_INVITE_WINDOW_DAYS),
    )
    db.add(session)
    db.flush()
    audit_service.record(
        db,
        actor_id=user_id,
        action=AUDIT_ACTION_AI_INTERVIEW_CREATED,
        resource_type="ai_interview_session",
        resource_id=str(session.id),
        organization_id=organization_id,
        metadata={
            "interview_type": interview_type,
            "question_count": question_count,
            "candidate_person_id": str(candidate_person_id),
            "consent_required": consent_required,
        },
    )
    db.commit()
    db.refresh(session)
    return session, token


def invite(
    db: Session,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    organization_id: uuid.UUID,
) -> AiInterviewSession:
    """Notify the candidate and move the session to consent_required/ready."""
    session = _get_session(db, session_id)
    if session.organization_id != organization_id:
        raise PermissionDeniedError("This interview does not belong to your organization.")
    _lazy_expire(db, session)
    target = (
        AI_INTERVIEW_STATUS_CONSENT_REQUIRED
        if session.consent_required
        else AI_INTERVIEW_STATUS_READY
    )
    _transition(session, target)
    candidate_user_id = _candidate_user_id(db, session)
    if candidate_user_id is not None:
        notifications.notify(
            db,
            candidate_user_id,
            "You have been invited to an AI interview",
            body=(
                f"An employer invited you to a {session.interview_type} AI interview "
                f"({session.question_count} questions). Complete it before "
                f"{to_utc_naive(session.expires_at).isoformat()}."
            ),
            kind=NOTIFICATION_KIND_INTERVIEW,
        )
        events.emit(
            db,
            event_type="ai_interview.invited",
            resource_type="ai_interview_session",
            resource_id=str(session.id),
            recipient_user_id=candidate_user_id,
            organization_id=organization_id,
            actor_user_id=user_id,
            payload={"status": session.status},
        )
    audit_service.record(
        db,
        actor_id=user_id,
        action=AUDIT_ACTION_AI_INTERVIEW_INVITED,
        resource_type="ai_interview_session",
        resource_id=str(session.id),
        organization_id=organization_id,
    )
    db.commit()
    db.refresh(session)
    return session


# --- Consent --------------------------------------------------------------------

def grant_consent(
    db: Session,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    entry_token: str,
    *,
    mic: bool,
    camera: bool,
    recording: bool,
) -> AiInterviewSession:
    session = _claim_candidate(db, user_id, session_id, entry_token)
    _lazy_expire(db, session)
    if session.status not in {
        AI_INTERVIEW_STATUS_CONSENT_REQUIRED,
        AI_INTERVIEW_STATUS_READY,
    }:
        raise InvalidInputError(
            f"Consent can only be granted before the interview starts (status={session.status})."
        )
    if session.status == AI_INTERVIEW_STATUS_CONSENT_REQUIRED:
        _transition(session, AI_INTERVIEW_STATUS_READY)
    session.consent_granted_at = utc_now_naive()
    session.consent_version = "v1"
    session.consent_mic = bool(mic)
    session.consent_camera = bool(camera)
    session.consent_recording = bool(recording)
    audit_service.record(
        db,
        actor_id=user_id,
        action=AUDIT_ACTION_AI_INTERVIEW_CONSENT_GRANTED,
        resource_type="ai_interview_session",
        resource_id=str(session.id),
        organization_id=session.organization_id,
        metadata={
            "mic": bool(mic),
            "camera": bool(camera),
            "recording": bool(recording),
            "consent_version": session.consent_version,
        },
    )
    db.commit()
    db.refresh(session)
    return session


def withdraw_consent(
    db: Session,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    entry_token: str,
) -> AiInterviewSession:
    """Consent withdrawn → stop the session (cancelled, audited)."""
    session = _claim_candidate(db, user_id, session_id, entry_token)
    _lazy_expire(db, session)
    _transition(session, AI_INTERVIEW_STATUS_CANCELLED)
    session.cancelled_at = utc_now_naive()
    session.cancel_reason = "consent_withdrawn"
    session.consent_withdrawn_at = utc_now_naive()
    audit_service.record(
        db,
        actor_id=user_id,
        action=AUDIT_ACTION_AI_INTERVIEW_CONSENT_WITHDRAWN,
        resource_type="ai_interview_session",
        resource_id=str(session.id),
        organization_id=session.organization_id,
    )
    events.emit(
        db,
        event_type="ai_interview.cancelled",
        resource_type="ai_interview_session",
        resource_id=str(session.id),
        organization_id=session.organization_id,
        actor_user_id=user_id,
        payload={"reason": "consent_withdrawn"},
    )
    db.commit()
    db.refresh(session)
    return session


# --- Prohibited-topic gate ------------------------------------------------------

_PROHIBITED_TOPIC_PATTERNS = [
    r"\bage\b|\bbirth\s*date\b|\byear\s*of\s*birth\b",
    r"\breligion\b|\bfaith\b|\bchurch\b|\bmosque\b|\btemple\b",
    r"\brace\b|\bethnicity\b|\bethnic\b|\bnational\s*origin\b",
    r"\bgender\b|\bsex\b|\bpregnancy\b|\bpregnant\b|\bfamily\s*plan",
    r"\bmarital\s*status\b|\bmarried\b|\bsingle\b|\bspouse\b",
    r"\bsexual\s*orientation\b|\bgay\b|\blesbian\b|\btransgender\b",
    r"\bmedical\s*condition\b|\bdisability\b|\bhandicap\b|\bhealth\s*history\b",
    r"\bpolitical\s*(affiliation|views|party)\b",
    r"\bunion\s*membership\b",
    r"\bcriminal\s*history\b|\barrest\b|\bconviction\b",
    r"\bfinancial\s*status\b|\bdebt\b|\bcredit\s*score\b|\bbankruptcy\b",
    r"\battractiveness\b|\bappearance\b|\blooks\b",
    r"\blie\s*detect|\bdeception\s*detect|\bfacial\s*(emotion|analysis|scan)\b",
    r"\bpersonality\s*(test|score|inference)\b",
]
_PROHIBITED_RE = [re.compile(p, re.IGNORECASE) for p in _PROHIBITED_TOPIC_PATTERNS]


def _contains_prohibited(text: str) -> bool:
    return any(p.search(text or "") for p in _PROHIBITED_RE)


def _reject_prohibited_config(
    competencies: List[str], introduction: Optional[str], closing: Optional[str]
) -> None:
    for comp in competencies:
        if _contains_prohibited(comp):
            raise InvalidInputError(
                "Configuration contains a topic that may not be used in interviews."
            )
    for block in (introduction, closing):
        if block and _contains_prohibited(block):
            raise InvalidInputError(
                "Configuration contains a topic that may not be used in interviews."
            )


# --- Question plan (deterministic) ----------------------------------------------

def _digest_for_plan(db: Session, person_id: uuid.UUID) -> Dict:
    """Professional digest reduced to the fields the plan may ground on."""
    from app.services.career_advisor import profile_digest

    digest = profile_digest(db, person_id)
    recent = digest.get("experience_summary", {}).get("recent_roles", []) or []
    skills_all = digest.get("skills", {}).get("all", []) or []
    creds = digest.get("credentials", {}) or {}
    verified = creds.get("verified", []) or []
    if verified and isinstance(verified[0], dict):
        verified = [c.get("name", "") for c in verified]
    return {
        "roles": [str(r.get("title", "")) for r in recent][:4],
        "companies": [str(r.get("company", "")) for r in recent][:4],
        "skills": [str(s.get("name", "")) for s in skills_all][:10],
        "credentials": [str(c) for c in verified][:6],
        "headline": digest.get("current_position", {}).get("title") or "",
    }


def _type_categories(interview_type: str) -> List[str]:
    mapping = {
        AI_INTERVIEW_TYPE_SCREENING: [PREP_CATEGORY_BEHAVIORAL, PREP_CATEGORY_COMPETENCY],
        AI_INTERVIEW_TYPE_BEHAVIORAL: [PREP_CATEGORY_BEHAVIORAL, PREP_CATEGORY_SITUATIONAL],
        AI_INTERVIEW_TYPE_COMPETENCY: [PREP_CATEGORY_COMPETENCY, PREP_CATEGORY_SITUATIONAL],
        AI_INTERVIEW_TYPE_ROLE_SPECIFIC: [PREP_CATEGORY_ROLE_SPECIFIC, PREP_CATEGORY_COMPETENCY],
        AI_INTERVIEW_TYPE_TECHNICAL: [PREP_CATEGORY_TECHNICAL, PREP_CATEGORY_SITUATIONAL],
        AI_INTERVIEW_TYPE_MIXED: [
            PREP_CATEGORY_BEHAVIORAL,
            PREP_CATEGORY_COMPETENCY,
            PREP_CATEGORY_ROLE_SPECIFIC,
            PREP_CATEGORY_TECHNICAL,
            PREP_CATEGORY_SITUATIONAL,
            PREP_CATEGORY_CAREER_HISTORY,
        ],
    }
    return mapping.get(interview_type, [PREP_CATEGORY_BEHAVIORAL, PREP_CATEGORY_COMPETENCY])


_BEHAVIORAL_TEMPLATES = [
    ("Tell me about a time you faced a difficult situation at work. What did you do and what was the outcome?", "resilience"),
    ("Describe a time you had to persuade others to support your idea.", "influence"),
    ("Give an example of working effectively with someone who disagreed with you.", "collaboration"),
    ("Describe a time you took the lead on a task without being asked.", "initiative"),
    ("Tell me about a time a project did not go as planned and how you handled it.", "adaptability"),
]

_COMPETENCY_TEMPLATES = [
    "Describe a situation where you demonstrated {competency}.",
    "Walk me through a time you used {competency} to achieve a result.",
]

_SITUATIONAL_TEMPLATES = [
    "A key stakeholder disagrees with your approach. How would you handle it?",
    "You are given a task with an unrealistic deadline. What do you do?",
    "You discover a mistake in your own work that has already shipped. How do you respond?",
]

_TECHNICAL_TEMPLATES = [
    "Explain how you would approach {skill} from first principles.",
    "Describe a project where you applied {skill} and what the outcome was.",
]


def _follow_ups_for(category: str) -> List[Dict]:
    by_category = {
        PREP_CATEGORY_BEHAVIORAL: [
            {"type": AI_FOLLOWUP_TYPE_EVIDENCE, "question": "Can you give a concrete example with a specific outcome?"},
            {"type": AI_FOLLOWUP_TYPE_DEPTH, "question": "What exactly was your personal contribution in that situation?"},
        ],
        PREP_CATEGORY_COMPETENCY: [
            {"type": AI_FOLLOWUP_TYPE_DEPTH, "question": "Can you go deeper into how you approached that?"},
            {"type": AI_FOLLOWUP_TYPE_EXAMPLE, "question": "Can you share a specific example where that competency mattered?"},
        ],
        PREP_CATEGORY_ROLE_SPECIFIC: [
            {"type": AI_FOLLOWUP_TYPE_EXAMPLE, "question": "Tell me about a specific piece of work that prepared you for this."},
            {"type": AI_FOLLOWUP_TYPE_SCENARIO, "question": "How would you apply that experience on day one in this role?"},
        ],
        PREP_CATEGORY_TECHNICAL: [
            {"type": AI_FOLLOWUP_TYPE_TECHNICAL_DETAIL, "question": "What trade-offs did you consider in your approach?"},
            {"type": AI_FOLLOWUP_TYPE_DEPTH, "question": "How would you test or verify your solution?"},
        ],
        PREP_CATEGORY_SITUATIONAL: [
            {"type": AI_FOLLOWUP_TYPE_SCENARIO, "question": "What would you do first, and why?"},
            {"type": AI_FOLLOWUP_TYPE_EVIDENCE, "question": "Have you handled something similar? What happened?"},
        ],
        PREP_CATEGORY_CAREER_HISTORY: [
            {"type": AI_FOLLOWUP_TYPE_DEPTH, "question": "What did you learn from that experience?"},
            {"type": AI_FOLLOWUP_TYPE_EVIDENCE, "question": "Can you quantify the impact of that work?"},
        ],
    }
    return by_category.get(category, [])


def _generate_plan(db: Session, session: AiInterviewSession) -> int:
    """Deterministic plan: grounded, bounded, prohibited-topic-gated.

    Returns the number of questions persisted.
    """
    digest = _digest_for_plan(db, session.candidate_person_id)
    requirements = _requirement_texts(db, session.opportunity_id)
    role_title = ""
    if session.opportunity_id:
        opp = db.get(Opportunity, session.opportunity_id)
        if opp is not None:
            role_title = opp.title or ""
    competencies = [c for c in (session.competencies or []) if c]
    categories = _type_categories(session.interview_type)

    candidates: List[Dict] = []
    seen: set = set()

    def _push(category: str, question: str, competency: str, *, target_skill: Optional[str] = None, reason: str = "") -> None:
        key = question.lower().strip()
        if key in seen or _contains_prohibited(question):
            return
        seen.add(key)
        candidates.append(
            {
                "category": category,
                "competency": competency,
                "question": question,
                "target_skill": target_skill,
                "reason": reason,
            }
        )

    # Competency/behavioral questions, per configured competency.
    pool = competencies or (digest["skills"] or ["the role's core skills"])[:4]
    for idx, comp in enumerate(pool[:6]):
        if PREP_CATEGORY_BEHAVIORAL in categories:
            text, trait = _BEHAVIORAL_TEMPLATES[idx % len(_BEHAVIORAL_TEMPLATES)]
            _push(
                PREP_CATEGORY_BEHAVIORAL, text, trait,
                target_skill=comp[:120],
                reason="Explores real workplace behavior relevant to the configured competency.",
            )
        if PREP_CATEGORY_COMPETENCY in categories:
            for tpl in _COMPETENCY_TEMPLATES[:1]:
                _push(
                    PREP_CATEGORY_COMPETENCY, tpl.format(competency=comp), comp,
                    target_skill=comp[:120],
                    reason="Directly probes the configured competency with concrete evidence.",
                )
    # Role-specific, grounded in the posted requirements.
    if PREP_CATEGORY_ROLE_SPECIFIC in categories:
        if requirements:
            for req in requirements[:3]:
                _push(
                    PREP_CATEGORY_ROLE_SPECIFIC,
                    f"The role requires: {req}. Tell me about your experience with this.",
                    "role_fit",
                    target_skill=req[:120],
                    reason="Grounded in the posted requirement, asked verbatim.",
                )
        if role_title:
            _push(
                PREP_CATEGORY_ROLE_SPECIFIC,
                f"What does a typical day look like for a {role_title}?",
                "role_fit",
                reason="Opens the candidate's understanding of the role.",
            )
    # Technical, grounded in skills/requirements.
    if PREP_CATEGORY_TECHNICAL in categories:
        tech_pool = [r for r in requirements] or digest["skills"]
        for skill in tech_pool[:3]:
            _push(
                PREP_CATEGORY_TECHNICAL,
                _TECHNICAL_TEMPLATES[0].format(skill=skill),
                "technical_depth",
                target_skill=skill[:120],
                reason="Probes applied technical understanding, not memorized definitions.",
            )
    # Situational.
    if PREP_CATEGORY_SITUATIONAL in categories:
        for text in _SITUATIONAL_TEMPLATES[:2]:
            _push(PREP_CATEGORY_SITUATIONAL, text, "judgment", reason="Assesses judgment under realistic pressure.")
    # Career history — grounded in the candidate's REAL history.
    if PREP_CATEGORY_CAREER_HISTORY in categories:
        for role, company in zip(digest["roles"][:2], digest["companies"][:2]):
            if not role:
                continue
            _push(
                PREP_CATEGORY_CAREER_HISTORY,
                f"Your Work ID shows you worked as {role} at {company}. What did you accomplish there?",
                "career_history",
                reason="Grounded in the candidate's own listed history.",
            )

    target = max(1, min(session.question_count, _MAX_QUESTIONS))
    selected = candidates[:target]
    if not selected:
        raise InvalidInputError(
            "No valid questions could be generated for this configuration."
        )

    seq = 0
    for item in selected:
        seq += 1
        row = AiInterviewQuestion(
            session_id=session.id,
            sequence=seq,
            category=item["category"],
            competency=item["competency"],
            question=item["question"],
            difficulty=session.difficulty,
            target_skill=item["target_skill"],
            reason=item["reason"],
            suggested_dimensions=_dimensions_for(item["category"]),
            follow_ups=_follow_ups_for(item["category"])[:2],
            status="pending",
        )
        db.add(row)
    db.flush()
    return seq


def _dimensions_for(category: str) -> List[str]:
    base = ["relevance", "structure", "evidence", "completeness"]
    if category == PREP_CATEGORY_TECHNICAL:
        return ["technical_accuracy", "problem_solving", "relevance", "clarity"]
    if category == PREP_CATEGORY_BEHAVIORAL:
        return ["structure", "evidence", "relevance", "communication"]
    if category == PREP_CATEGORY_SITUATIONAL:
        return ["problem_solving", "structure", "relevance", "completeness"]
    if category == PREP_CATEGORY_ROLE_SPECIFIC:
        return ["role_knowledge", "relevance", "clarity", "completeness"]
    return base


def _role_title(db: Session, session: AiInterviewSession) -> str:
    if session.opportunity_id:
        opp = db.get(Opportunity, session.opportunity_id)
        if opp is not None:
            return opp.title or ""
    return "this role"


# --- Interview flow (candidate) -------------------------------------------------

def start(
    db: Session,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    entry_token: str,
) -> Dict:
    session = _claim_candidate(db, user_id, session_id, entry_token)
    _lazy_expire(db, session)
    _transition(session, AI_INTERVIEW_STATUS_IN_PROGRESS)
    session.started_at = utc_now_naive()
    existing = db.scalar(
        select(func.count(AiInterviewQuestion.id)).where(
            AiInterviewQuestion.session_id == session.id
        )
    )
    if not existing:
        count = _generate_plan(db, session)
        audit_service.record(
            db,
            actor_id=user_id,
            action=AUDIT_ACTION_AI_INTERVIEW_PLAN_GENERATED,
            resource_type="ai_interview_session",
            resource_id=str(session.id),
            organization_id=session.organization_id,
            metadata={"questions": count},
        )
    audit_service.record(
        db,
        actor_id=user_id,
        action=AUDIT_ACTION_AI_INTERVIEW_STARTED,
        resource_type="ai_interview_session",
        resource_id=str(session.id),
        organization_id=session.organization_id,
    )
    events.emit(
        db,
        event_type="ai_interview.started",
        resource_type="ai_interview_session",
        resource_id=str(session.id),
        organization_id=session.organization_id,
        actor_user_id=user_id,
    )
    db.commit()
    db.refresh(session)
    return {
        "session_id": str(session.id),
        "status": session.status,
        "introduction": session.introduction
        or (
            f"I am an AI interviewer conducting a structured {session.interview_type} "
            f"interview for {_role_title(db, session)}. I will ask about "
            f"{session.question_count} questions. Your answers are evaluated on "
            "job-relevant dimensions only, and no recording is made. "
            "An authorized human reviews the report — I do not make hiring decisions."
        ),
        "closing": session.closing or "Thank you. Your interview is complete.",
        "question_count": session.question_count,
        "duration_minutes": session.duration_minutes,
    }


def _next_question_row(db: Session, session_id: uuid.UUID) -> Optional[AiInterviewQuestion]:
    row = db.scalar(
        select(AiInterviewQuestion)
        .where(
            AiInterviewQuestion.session_id == session_id,
            AiInterviewQuestion.status == "pending",
        )
        .order_by(AiInterviewQuestion.sequence.asc())
        .limit(1)
    )
    return row


def get_next_question(
    db: Session,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    entry_token: str,
) -> Dict:
    session = _claim_candidate(db, user_id, session_id, entry_token)
    _lazy_expire(db, session)
    if session.status == AI_INTERVIEW_STATUS_PAUSED:
        raise InvalidInputError("The interview is paused — resume it first.")
    if session.status != AI_INTERVIEW_STATUS_IN_PROGRESS:
        raise InvalidInputError(
            f"Questions can only be fetched while the interview is in progress (status={session.status})."
        )
    if _time_budget_exhausted(session):
        return _finish(db, user_id, session, reason="time_budget")

    question = _next_question_row(db, session.id)
    if question is None:
        return _finish(db, user_id, session, reason="questions_exhausted")

    question.status = "asked"
    question.asked_at = utc_now_naive()
    audit_service.record(
        db,
        actor_id=user_id,
        action=AUDIT_ACTION_AI_INTERVIEW_QUESTION_ASKED,
        resource_type="ai_interview_question",
        resource_id=str(question.id),
        organization_id=session.organization_id,
        metadata={"sequence": question.sequence, "category": question.category},
    )
    db.commit()
    return _question_out(question, session)


def _question_out(question: AiInterviewQuestion, session: AiInterviewSession) -> Dict:
    return {
        "session_id": str(session.id),
        "question_id": str(question.id),
        "sequence": question.sequence,
        "category": question.category,
        "competency": question.competency,
        "question": question.question,
        "difficulty": question.difficulty,
        "target_skill": question.target_skill,
        "reason": question.reason,
        "suggested_dimensions": question.suggested_dimensions or [],
        "is_follow_up": question.follow_up_of is not None,
        "remaining": None,
        "note": (
            "Follow-up questions are linked to the same competency. "
            "You can ask to repeat a question at any time — that never "
            "counts against you."
        ),
    }


def repeat_question(
    db: Session,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    entry_token: str,
    question_id: uuid.UUID,
) -> Dict:
    """Candidate asks for a repeat/rephrase — no evaluation penalty."""
    session = _claim_candidate(db, user_id, session_id, entry_token)
    if session.status != AI_INTERVIEW_STATUS_IN_PROGRESS:
        raise InvalidInputError("The interview is not in progress.")
    question = db.get(AiInterviewQuestion, question_id)
    if question is None or question.session_id != session.id:
        raise NotFoundError("Question not found.")
    out = _question_out(question, session)
    out["rephrased"] = True
    out["question"] = f"Of course — let me repeat: {question.question}"
    audit_service.record(
        db,
        actor_id=user_id,
        action=AUDIT_ACTION_AI_INTERVIEW_QUESTION_ASKED,
        resource_type="ai_interview_question",
        resource_id=str(question.id),
        organization_id=session.organization_id,
        metadata={"repeat": True},
    )
    db.commit()
    return out


# --- Deterministic answer evaluation --------------------------------------------

_STAR_MARKERS = [
    "situation", "context", "task", "action", "result", "outcome",
    "i did", "i led", "i built", "i created", "i implemented", "i reduced",
    "we", "my team", "first", "then", "finally", "because", "as a result",
]
_EVIDENCE_MARKERS = [
    "by ", "%", "percent", "reduced", "increased", "improved", "cut", "saved",
    "doubled", "halved", "grew", "launched", "delivered", "shipped",
    "in ", "within", "from ", "to ", "users", "customers", "revenue",
]
_FILLER = {"um", "uh", "like", "basically", "you know", "sort of"}


def _evaluate_answer(
    db: Session,
    session: AiInterviewSession,
    question: AiInterviewQuestion,
    answer: str,
) -> Dict:
    text = (answer or "").strip()
    lowered = text.lower()
    length = len(text)
    markers = [m for m in _STAR_MARKERS if m in lowered]
    evidence = [m for m in _EVIDENCE_MARKERS if m in lowered]
    filler_hits = [f for f in _FILLER if f in lowered]
    target_terms = []
    if question.target_skill:
        target_terms = [t for t in question.target_skill.lower().split() if len(t) > 3]

    def _score(expl: str, value: int) -> Dict:
        return {"score": max(1, min(5, value)), "explanation": expl}

    dims = {}
    for dim in question.suggested_dimensions or ["relevance", "structure", "evidence", "completeness"]:
        if dim == "relevance":
            hits = sum(1 for t in target_terms if t in lowered)
            dims[dim] = _score(
                "Answer engages the question's subject." if hits else "Answer is only loosely related to the question.",
                5 if hits >= 2 else (4 if hits == 1 else (3 if length > 0 else 1)),
            )
        elif dim == "structure":
            n = len(markers)
            dims[dim] = _score(
                f"Answer uses {n} structural/STAR markers." if n else "Answer lacks an ordered structure.",
                5 if n >= 4 else (4 if n >= 2 else (3 if n == 1 else 2)),
            )
        elif dim == "evidence":
            n = len(evidence)
            dims[dim] = _score(
                f"Answer contains {n} concrete evidence markers (numbers, results)." if n else "No concrete evidence or measurable outcome provided.",
                5 if n >= 3 else (4 if n >= 2 else (3 if n == 1 else 1)),
            )
        elif dim == "completeness":
            dims[dim] = _score(
                "Answer is complete for a spoken response." if length >= 120 else "Answer is brief — consider a fuller example.",
                4 if length >= 180 else (3 if length >= 80 else (2 if length >= 30 else 1)),
            )
        elif dim == "clarity":
            dims[dim] = _score(
                "Answer is clear and readable." if filler_hits == 0 else "Answer contains filler language that reduces clarity.",
                4 if filler_hits == 0 else 2,
            )
        elif dim == "communication":
            dims[dim] = _score(
                "Clear, well-paced response." if length >= 60 and filler_hits == 0 else "Response would benefit from clearer delivery.",
                4 if length >= 60 and filler_hits == 0 else 2,
            )
        elif dim == "role_knowledge":
            hits = sum(1 for t in target_terms if t in lowered)
            dims[dim] = _score(
                "Demonstrates understanding of the role's domain." if hits else "Limited direct connection to the role's domain shown.",
                4 if hits >= 2 else (3 if hits == 1 else 2),
            )
        elif dim == "technical_accuracy":
            hits = sum(1 for t in target_terms if t in lowered)
            dims[dim] = _score(
                "Uses the relevant technical vocabulary." if hits else "Technical vocabulary is limited.",
                4 if hits >= 2 else (3 if hits == 1 else 2),
            )
        elif dim == "problem_solving":
            hits = [m for m in ("because", "as a result", "i did", "i would", "approach", "trade-off", "test") if m in lowered]
            dims[dim] = _score(
                f"Shows a reasoning chain ({len(hits)} reasoning markers)." if hits else "Reasoning chain is not visible.",
                4 if len(hits) >= 3 else (3 if hits else 2),
            )
        else:
            dims[dim] = _score("Not assessed for this question type.", 3)

    strengths = [f"{d}: {v['explanation']}" for d, v in dims.items() if v["score"] >= 4]
    improvements = [f"{d}: {v['explanation']}" for d, v in dims.items() if v["score"] <= 2]
    return {
        "dimensions": dims,
        "evidence_markers": evidence[:6],
        "strengths": strengths[:3],
        "improvements": improvements[:3],
        "length": length,
    }


def submit_response(
    db: Session,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    entry_token: str,
    question_id: uuid.UUID,
    answer: str,
) -> Dict:
    session = _claim_candidate(db, user_id, session_id, entry_token)
    _lazy_expire(db, session)
    if session.status != AI_INTERVIEW_STATUS_IN_PROGRESS:
        raise InvalidInputError("Responses can only be submitted while the interview is in progress.")
    if not answer or not answer.strip():
        raise InvalidInputError("An answer is required.")
    if len(answer) > 4000:
        raise InvalidInputError("Answer is too long.")
    if _time_budget_exhausted(session):
        return _finish(db, user_id, session, reason="time_budget")

    question = db.get(AiInterviewQuestion, question_id)
    if question is None or question.session_id != session.id:
        raise NotFoundError("Question not found.")
    if question.status != "asked":
        raise InvalidInputError("This question was not the active question.")

    result = _evaluate_answer(db, session, question, answer)
    evaluation = AiInterviewEvaluation(
        session_id=session.id,
        question_id=question.id,
        dimensions=result["dimensions"],
        strengths=result["strengths"],
        improvements=result["improvements"],
        evidence_markers=result["evidence_markers"],
        answer_length=result["length"],
    )
    db.add(evaluation)
    question.status = "answered"
    question.answered_at = utc_now_naive()
    db.flush()

    # Adaptive follow-up: weak evidence on a parent question with an unused
    # follow-up → ask a linked follow-up next (bounded per session).
    follow_up_row: Optional[AiInterviewQuestion] = None
    evidence_score = result["dimensions"].get("evidence", {}).get("score", 3)
    used_followups = db.scalar(
        select(func.count(AiInterviewQuestion.id)).where(
            AiInterviewQuestion.session_id == session.id,
            AiInterviewQuestion.follow_up_of.is_not(None),
        )
    )
    if (
        evidence_score <= 2
        and question.follow_ups
        and question.follow_up_of is None
        and (used_followups or 0) < _MAX_FOLLOWUPS_PER_SESSION
    ):
        follow_up_data = question.follow_ups[0]
        seq = db.scalar(
            select(func.max(AiInterviewQuestion.sequence)).where(
                AiInterviewQuestion.session_id == session.id
            )
        ) or 0
        follow_up_row = AiInterviewQuestion(
            session_id=session.id,
            sequence=seq + 1,
            category=question.category,
            competency=question.competency,
            question=follow_up_data["question"],
            difficulty=session.difficulty,
            target_skill=question.target_skill,
            reason="Adaptive follow-up linked to the same competency after a low-evidence answer.",
            suggested_dimensions=question.suggested_dimensions,
            follow_ups=[],
            follow_up_of=question.id,
            status="asked",
            asked_at=utc_now_naive(),
        )
        db.add(follow_up_row)
        evaluation.follow_up_used = follow_up_data["type"]
        db.flush()

    audit_service.record(
        db,
        actor_id=user_id,
        action=AUDIT_ACTION_AI_INTERVIEW_RESPONSE_EVALUATED,
        resource_type="ai_interview_question",
        resource_id=str(question.id),
        organization_id=session.organization_id,
        metadata={
            "sequence": question.sequence,
            "category": question.category,
            "follow_up": evaluation.follow_up_used,
            "answer_length": result["length"],
        },
    )
    db.commit()

    payload = {
        "session_id": str(session.id),
        "evaluation": {
            "dimensions": result["dimensions"],
            "strengths": result["strengths"],
            "improvements": result["improvements"],
            "evidence_markers": result["evidence_markers"],
            "disclaimer": (
                "This is structured evaluation feedback on job-relevant "
                "dimensions — it is not a hiring decision and not a "
                "prediction of interview success."
            ),
        },
        "next": None,
    }
    if follow_up_row is not None:
        payload["next"] = _question_out(follow_up_row, session)
    else:
        nxt = _next_question_row(db, session.id)
        if nxt is None:
            return _finish(db, user_id, session, reason="questions_exhausted", preceding=payload)
        payload["next"] = _question_out(nxt, session)
    return payload


# --- Lifecycle ------------------------------------------------------------------

def pause(
    db: Session, user_id: uuid.UUID, session_id: uuid.UUID, entry_token: str
) -> AiInterviewSession:
    session = _claim_candidate(db, user_id, session_id, entry_token)
    _lazy_expire(db, session)
    _transition(session, AI_INTERVIEW_STATUS_PAUSED)
    audit_service.record(
        db,
        actor_id=user_id,
        action=AUDIT_ACTION_AI_INTERVIEW_PAUSED,
        resource_type="ai_interview_session",
        resource_id=str(session.id),
        organization_id=session.organization_id,
    )
    db.commit()
    db.refresh(session)
    return session


def resume(
    db: Session, user_id: uuid.UUID, session_id: uuid.UUID, entry_token: str
) -> AiInterviewSession:
    session = _claim_candidate(db, user_id, session_id, entry_token)
    _lazy_expire(db, session)
    if _time_budget_exhausted(session):
        return _finish(db, user_id, session, reason="time_budget")  # type: ignore[return-value]
    _transition(session, AI_INTERVIEW_STATUS_IN_PROGRESS)
    audit_service.record(
        db,
        actor_id=user_id,
        action=AUDIT_ACTION_AI_INTERVIEW_RESUMED,
        resource_type="ai_interview_session",
        resource_id=str(session.id),
        organization_id=session.organization_id,
    )
    db.commit()
    db.refresh(session)
    return session


def cancel(
    db: Session,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    *,
    entry_token: Optional[str] = None,
    organization_id: Optional[uuid.UUID] = None,
    reason: str = "employer_cancelled",
) -> AiInterviewSession:
    if entry_token:
        session = _claim_candidate(db, user_id, session_id, entry_token)
    else:
        session = _get_session(db, session_id)
        if organization_id is None or session.organization_id != organization_id:
            raise PermissionDeniedError(
                "This interview does not belong to your organization."
            )
    _lazy_expire(db, session)
    _transition(session, AI_INTERVIEW_STATUS_CANCELLED)
    session.cancelled_at = utc_now_naive()
    session.cancel_reason = (reason or "cancelled")[:40]
    audit_service.record(
        db,
        actor_id=user_id,
        action=AUDIT_ACTION_AI_INTERVIEW_CANCELLED,
        resource_type="ai_interview_session",
        resource_id=str(session.id),
        organization_id=session.organization_id,
        metadata={"reason": session.cancel_reason},
    )
    events.emit(
        db,
        event_type="ai_interview.cancelled",
        resource_type="ai_interview_session",
        resource_id=str(session.id),
        organization_id=session.organization_id,
        actor_user_id=user_id,
        payload={"reason": session.cancel_reason},
    )
    db.commit()
    db.refresh(session)
    return session


def complete(
    db: Session,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    entry_token: str,
) -> Dict:
    session = _claim_candidate(db, user_id, session_id, entry_token)
    _lazy_expire(db, session)
    return _finish(db, user_id, session, reason="candidate_complete")


def _finish(
    db: Session,
    user_id: uuid.UUID,
    session: AiInterviewSession,
    *,
    reason: str,
    preceding: Optional[Dict] = None,
) -> Dict:
    if session.status in {AI_INTERVIEW_STATUS_COMPLETED, AI_INTERVIEW_STATUS_CANCELLED}:
        return {"session_id": str(session.id), "status": session.status, "already_terminal": True}
    if session.status not in {AI_INTERVIEW_STATUS_IN_PROGRESS, AI_INTERVIEW_STATUS_PAUSED}:
        raise InvalidInputError(
            f"The interview must be in progress to complete (status={session.status})."
        )
    _transition(session, AI_INTERVIEW_STATUS_COMPLETED)
    session.completed_at = utc_now_naive()
    report = _generate_report(db, session, generated_by=user_id)
    audit_service.record(
        db,
        actor_id=user_id,
        action=AUDIT_ACTION_AI_INTERVIEW_COMPLETED,
        resource_type="ai_interview_session",
        resource_id=str(session.id),
        organization_id=session.organization_id,
        metadata={"reason": reason},
    )
    audit_service.record(
        db,
        actor_id=user_id,
        action=AUDIT_ACTION_AI_INTERVIEW_REPORT_GENERATED,
        resource_type="ai_interview_report",
        resource_id=str(report.id),
        organization_id=session.organization_id,
    )
    events.emit(
        db,
        event_type="ai_interview.completed",
        resource_type="ai_interview_session",
        resource_id=str(session.id),
        organization_id=session.organization_id,
        actor_user_id=user_id,
        payload={"reason": reason},
    )
    events.emit(
        db,
        event_type="ai_interview.report_ready",
        resource_type="ai_interview_report",
        resource_id=str(report.id),
        organization_id=session.organization_id,
        actor_user_id=user_id,
    )
    db.commit()
    db.refresh(session)
    payload = preceding or {}
    payload["session_id"] = str(session.id)
    payload["status"] = session.status
    payload["reason"] = reason
    payload["note"] = "The interview is complete. An authorized human will review the report."
    return payload


def _generate_report(
    db: Session, session: AiInterviewSession, *, generated_by: uuid.UUID
) -> AiInterviewReport:
    questions = db.scalars(
        select(AiInterviewQuestion)
        .where(AiInterviewQuestion.session_id == session.id)
        .order_by(AiInterviewQuestion.sequence.asc())
    ).all()
    evaluations = db.scalars(
        select(AiInterviewEvaluation).where(AiInterviewEvaluation.session_id == session.id)
    ).all()
    by_question = {e.question_id: e for e in evaluations}

    competency_evidence: Dict[str, List[Dict]] = {}
    strengths: List[str] = []
    improvements: List[str] = []
    unanswered: List[str] = []
    for q in questions:
        if q.follow_up_of is not None:
            continue
        eval_row = by_question.get(q.id)
        if eval_row is None:
            unanswered.append(q.question)
            continue
        entry = {
            "competency": q.competency,
            "category": q.category,
            "evidence_markers": eval_row.evidence_markers or [],
            "evidence_score": eval_row.dimensions.get("evidence", {}).get("score"),
        }
        competency_evidence.setdefault(q.competency, []).append(entry)
        strengths.extend(eval_row.strengths or [])
        improvements.extend(eval_row.improvements or [])

    completed_plan = [q for q in questions if q.follow_up_of is None]
    answered = sum(1 for q in completed_plan if q.id in by_question)
    completion_pct = round((answered / len(completed_plan) * 100)) if completed_plan else 0
    avg_scores = []
    for e in evaluations:
        avg_scores.append(
            sum(d["score"] for d in e.dimensions.values()) / max(1, len(e.dimensions))
        )
    avg_score = round(sum(avg_scores) / len(avg_scores), 1) if avg_scores else None

    quality = {
        "answered": answered,
        "total_questions": len(completed_plan),
        "completion_pct": completion_pct,
        "average_dimension_score": avg_score,
        "time_taken_minutes": (
            round(
                (to_utc_naive(session.completed_at) - to_utc_naive(session.started_at)).total_seconds() / 60, 1
            )
            if session.started_at and session.completed_at
            else None
        ),
        "note": (
            "These are structured quality signals about the session itself — "
            "never a hiring probability."
        ),
    }

    report = AiInterviewReport(
        session_id=session.id,
        summary=(
            f"AI-assisted {session.interview_type} interview with "
            f"{answered} of {len(completed_plan)} planned questions answered. "
            f"See competency evidence and review signals below. "
            "HUMAN REVIEW REQUIRED — this report is an input to the employer's "
            "decision, not the decision itself."
        ),
        competency_evidence=list(competency_evidence.values()),
        strengths=list(dict.fromkeys(strengths))[:6],
        improvement_areas=list(dict.fromkeys(improvements))[:6],
        unanswered_areas=unanswered[:5],
        integrity_signals=session.integrity_signals or [],
        interview_quality=quality,
        generated_by_user_id=generated_by,
    )
    db.add(report)
    db.flush()
    return report


# --- Integrity signals ----------------------------------------------------------

def record_integrity_signal(
    db: Session,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    entry_token: str,
    signal_type: str,
    detail: Optional[str] = None,
) -> AiInterviewSession:
    """Objective session-level signal only. Never affects evaluation."""
    if signal_type not in AI_INTEGRITY_SIGNAL_TYPES:
        raise InvalidInputError(f"Unknown integrity signal type '{signal_type}'.")
    session = _claim_candidate(db, user_id, session_id, entry_token)
    signals = list(session.integrity_signals or [])
    if len(signals) >= _MAX_INTEGRITY_SIGNALS:
        raise InvalidInputError("Integrity signal limit reached for this session.")
    signals.append(
        {
            "type": signal_type,
            "at": utc_now_naive().isoformat(),
            "detail": (detail or "")[:120],
        }
    )
    session.integrity_signals = signals
    audit_service.record(
        db,
        actor_id=user_id,
        action=AUDIT_ACTION_AI_INTERVIEW_INTEGRITY_SIGNAL,
        resource_type="ai_interview_session",
        resource_id=str(session.id),
        organization_id=session.organization_id,
        metadata={
            "signal_type": signal_type,
            "note": "Signal only — never proof of wrongdoing, never an evaluation penalty.",
        },
    )
    db.commit()
    db.refresh(session)
    return session


# --- Reports & decisions --------------------------------------------------------

def employer_report(
    db: Session,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    organization_id: uuid.UUID,
) -> Dict:
    session = _get_session(db, session_id)
    if session.organization_id != organization_id:
        raise PermissionDeniedError("This interview does not belong to your organization.")
    report = db.scalar(
        select(AiInterviewReport).where(AiInterviewReport.session_id == session.id)
    )
    if report is None:
        raise NotFoundError("No report exists yet for this interview.")
    audit_service.record(
        db,
        actor_id=user_id,
        action=AUDIT_ACTION_AI_INTERVIEW_REPORT_VIEWED,
        resource_type="ai_interview_report",
        resource_id=str(report.id),
        organization_id=organization_id,
        metadata={"viewer": "employer"},
    )
    db.commit()
    return {
        "session_id": str(session.id),
        "candidate_person_id": str(session.candidate_person_id),
        "interview_type": session.interview_type,
        "status": session.status,
        "decision": session.decision,
        "decision_note": session.decision_note,
        "decided_by": str(session.decided_by) if session.decided_by else None,
        "decided_at": session.decided_at.isoformat() if session.decided_at else None,
        "summary": report.summary,
        "competency_evidence": report.competency_evidence,
        "strengths": report.strengths,
        "improvement_areas": report.improvement_areas,
        "unanswered_areas": report.unanswered_areas,
        "interview_quality": report.interview_quality,
        "integrity_signals": [
            {**s, "label": "REVIEW SIGNAL — not proof of wrongdoing"}
            for s in (report.integrity_signals or [])
        ],
        "generated_at": report.generated_at.isoformat() if report.generated_at else None,
        "disclaimer": (
            "AI-assisted assessment. Human review required. This report is an "
            "input to the employer's decision — it is not the decision."
        ),
    }


def candidate_feedback(
    db: Session,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    entry_token: str,
) -> Dict:
    session = _claim_candidate(db, user_id, session_id, entry_token)
    report = db.scalar(
        select(AiInterviewReport).where(AiInterviewReport.session_id == session.id)
    )
    if report is None:
        raise NotFoundError("No feedback is available yet for this interview.")
    audit_service.record(
        db,
        actor_id=user_id,
        action=AUDIT_ACTION_AI_INTERVIEW_REPORT_VIEWED,
        resource_type="ai_interview_report",
        resource_id=str(report.id),
        organization_id=session.organization_id,
        metadata={"viewer": "candidate"},
    )
    db.commit()
    return {
        "session_id": str(session.id),
        "status": session.status,
        "completed_at": session.completed_at.isoformat() if session.completed_at else None,
        "strengths": (report.strengths or [])[:3],
        "preparation_areas": (report.improvement_areas or [])[:3],
        "note": (
            "General preparation feedback only. Confidential employer "
            "deliberations and internal notes are never shared."
        ),
    }


def record_decision(
    db: Session,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    organization_id: uuid.UUID,
    decision: str,
    note: Optional[str] = None,
) -> AiInterviewSession:
    session = _get_session(db, session_id)
    if session.organization_id != organization_id:
        raise PermissionDeniedError("This interview does not belong to your organization.")
    if decision not in AI_INTERVIEW_DECISIONS:
        raise InvalidInputError(f"Unknown decision '{decision}'.")
    if session.status != AI_INTERVIEW_STATUS_COMPLETED:
        raise InvalidInputError("A decision can only be recorded after the interview is completed.")
    session.decision = decision
    session.decision_note = (note or "")[:500]
    session.decided_by = user_id
    session.decided_at = utc_now_naive()
    audit_service.record(
        db,
        actor_id=user_id,
        action=AUDIT_ACTION_AI_INTERVIEW_DECISION_RECORDED,
        resource_type="ai_interview_session",
        resource_id=str(session.id),
        organization_id=organization_id,
        metadata={"decision": decision},
    )
    candidate_user_id = _candidate_user_id(db, session)
    if candidate_user_id is not None:
        notifications.notify(
            db,
            candidate_user_id,
            "Your interview outcome has been reviewed",
            body="An authorized reviewer has recorded an outcome for your AI interview.",
            kind=NOTIFICATION_KIND_INTERVIEW,
        )
        events.emit(
            db,
            event_type="ai_interview.decision_recorded",
            resource_type="ai_interview_session",
            resource_id=str(session.id),
            recipient_user_id=candidate_user_id,
            organization_id=organization_id,
            actor_user_id=user_id,
        )
    db.commit()
    db.refresh(session)
    return session


# --- Views ----------------------------------------------------------------------

def employer_list(
    db: Session, organization_id: uuid.UUID, limit: int = 30
) -> List[Dict]:
    rows = db.scalars(
        select(AiInterviewSession)
        .where(AiInterviewSession.organization_id == organization_id)
        .order_by(AiInterviewSession.created_at.desc())
        .limit(min(limit, 100))
    ).all()
    return [employer_view(db, s) for s in rows]


def employer_view(db: Session, session: AiInterviewSession) -> Dict:
    eval_count = db.scalar(
        select(func.count(AiInterviewEvaluation.id)).where(
            AiInterviewEvaluation.session_id == session.id
        )
    )
    return {
        "session_id": str(session.id),
        "organization_id": str(session.organization_id),
        "candidate_person_id": str(session.candidate_person_id),
        "application_id": str(session.application_id) if session.application_id else None,
        "opportunity_id": str(session.opportunity_id) if session.opportunity_id else None,
        "interview_type": session.interview_type,
        "status": session.status,
        "language": session.language,
        "duration_minutes": session.duration_minutes,
        "question_count": session.question_count,
        "difficulty": session.difficulty,
        "competencies": session.competencies or [],
        "consent_required": session.consent_required,
        "consent_granted": session.consent_granted_at is not None,
        "consent_mic": session.consent_mic,
        "consent_camera": session.consent_camera,
        "consent_recording": session.consent_recording,
        "started_at": session.started_at.isoformat() if session.started_at else None,
        "completed_at": session.completed_at.isoformat() if session.completed_at else None,
        "expires_at": session.expires_at.isoformat() if session.expires_at else None,
        "evaluations_count": eval_count or 0,
        "integrity_signals_count": len(session.integrity_signals or []),
        "decision": session.decision,
        "decision_note": session.decision_note,
        "decided_by": str(session.decided_by) if session.decided_by else None,
        "decided_at": session.decided_at.isoformat() if session.decided_at else None,
        "created_at": session.created_at.isoformat() if session.created_at else None,
    }


def candidate_view(db: Session, session: AiInterviewSession) -> Dict:
    media = session.media_profile or {}
    return {
        "session_id": str(session.id),
        "status": session.status,
        "interview_type": session.interview_type,
        "language": session.language,
        "duration_minutes": session.duration_minutes,
        "question_count": session.question_count,
        "difficulty": session.difficulty,
        "opportunity_title": _role_title(db, session),
        "company_name": (
            db.get(Opportunity, session.opportunity_id).company_name
            if session.opportunity_id and db.get(Opportunity, session.opportunity_id)
            else None
        ),
        "consent_required": session.consent_required,
        "consent_granted": session.consent_granted_at is not None,
        "consent_mic": session.consent_mic,
        "consent_camera": session.consent_camera,
        "consent_recording": session.consent_recording,
        "media_profile": media,
        "voice_enabled": bool(media.get("voice_enabled")),
        "video_enabled": bool(media.get("video_enabled")),
        "started_at": session.started_at.isoformat() if session.started_at else None,
        "completed_at": session.completed_at.isoformat() if session.completed_at else None,
        "expires_at": session.expires_at.isoformat() if session.expires_at else None,
        "created_at": session.created_at.isoformat() if session.created_at else None,
        "note": (
            "This is an AI interviewer. It is not a human interviewer, and "
            "your answers are evaluated on job-relevant dimensions only."
        ),
    }


def session_out(db: Session, session: AiInterviewSession, *, for_employer: bool) -> Dict:
    return employer_view(db, session) if for_employer else candidate_view(db, session)