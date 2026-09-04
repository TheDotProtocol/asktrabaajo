"""AI Interview Engine API — /api/v1/ai-interviews (Phase 16).

Two authorization surfaces, both enforced server-side:

- EMPLOYER side: org membership + ``interviews.manage`` / ``interviews.read``
  permissions. Sessions are tenant-scoped to the caller's organization.
- CANDIDATE side: the SHA-256 entry-token must match AND the caller's
  person profile must be the session's candidate. A guessed session URL
  is useless; the token is single-purpose per session.

No facial emotion analysis, no lie detection, no protected-characteristic
inference, no autonomous hiring — those capabilities do not exist. The
employer records the human decision; the engine only produces an
AI-assisted report marked human-review-required.
"""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_org_permission
from app.core.errors import AppError
from app.core.ratelimit import rate_limit_dependency
from app.db.session import get_db
from app.models.identity import User
from app.schemas.ai_interview import (
    AiInterviewCreateOut,
    AiInterviewCreateRequest,
    ConsentRequest,
    DecisionRequest,
    EntryTokenIn,
    IntegritySignalRequest,
    RepeatRequest,
    ResponseRequest,
)
from app.services import ai_interview as engine

router = APIRouter(prefix="/ai-interviews", tags=["ai-interviews"])


def _raise_app(exc: AppError) -> Exception:
    from fastapi import HTTPException

    return HTTPException(status_code=exc.status_code, detail=exc.message)


def _entry_token_header(x_interview_token: Optional[str]) -> str:
    if not x_interview_token:
        from fastapi import HTTPException

        raise HTTPException(status_code=401, detail="Interview entry token required.")
    return x_interview_token


# --- Employer side --------------------------------------------------------------

@router.post("", response_model=AiInterviewCreateOut, status_code=201,
             dependencies=[Depends(rate_limit_dependency("ai_interview.create"))])
def create_interview(
    body: AiInterviewCreateRequest,
    organization_id: uuid.UUID = Query(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    try:
        require_org_permission(db, user, "interviews.manage", organization_id)
        session, token = engine.create_session(
            db,
            user.id,
            organization_id=organization_id,
            candidate_person_id=body.candidate_person_id,
            application_id=body.application_id,
            opportunity_id=body.opportunity_id,
            interview_id=body.interview_id,
            interview_type=body.interview_type,
            duration_minutes=body.duration_minutes,
            question_count=body.question_count,
            difficulty=body.difficulty,
            language=body.language,
            competencies=body.competencies,
            evaluation_dimensions=body.evaluation_dimensions,
            introduction=body.introduction,
            closing=body.closing,
            voice_enabled=body.voice_enabled,
            video_enabled=body.video_enabled,
            consent_required=body.consent_required,
        )
        return {
            "session_id": session.id,
            "entry_token": token,
            "expires_at": session.expires_at.isoformat() if session.expires_at else None,
        }
    except AppError as exc:
        raise _raise_app(exc) from exc


@router.get("")
def list_interviews(
    organization_id: uuid.UUID = Query(...),
    limit: int = Query(default=30, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    try:
        require_org_permission(db, user, "interviews.read", organization_id)
        return {"interviews": engine.employer_list(db, organization_id, limit=limit)}
    except AppError as exc:
        raise _raise_app(exc) from exc


@router.get("/{session_id}")
def get_interview(
    session_id: uuid.UUID,
    organization_id: uuid.UUID = Query(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    try:
        require_org_permission(db, user, "interviews.read", organization_id)
        session = engine.require_org_session(db, session_id, organization_id)
        return engine.employer_view(db, session)
    except AppError as exc:
        raise _raise_app(exc) from exc


@router.post("/{session_id}/invite",
             dependencies=[Depends(rate_limit_dependency("ai_interview.invite"))])
def invite_candidate(
    session_id: uuid.UUID,
    organization_id: uuid.UUID = Query(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    try:
        require_org_permission(db, user, "interviews.manage", organization_id)
        session = engine.invite(db, user.id, session_id, organization_id)
        return {"session_id": str(session.id), "status": session.status}
    except AppError as exc:
        raise _raise_app(exc) from exc


@router.post("/{session_id}/cancel")
def cancel_by_employer(
    session_id: uuid.UUID,
    organization_id: uuid.UUID = Query(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    try:
        require_org_permission(db, user, "interviews.manage", organization_id)
        session = engine.cancel(
            db, user.id, session_id, organization_id=organization_id, reason="employer_cancelled"
        )
        return {"session_id": str(session.id), "status": session.status}
    except AppError as exc:
        raise _raise_app(exc) from exc


@router.get("/{session_id}/report")
def employer_report(
    session_id: uuid.UUID,
    organization_id: uuid.UUID = Query(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    try:
        require_org_permission(db, user, "interviews.read", organization_id)
        return engine.employer_report(db, user.id, session_id, organization_id)
    except AppError as exc:
        raise _raise_app(exc) from exc


@router.post("/{session_id}/decision")
def record_decision(
    session_id: uuid.UUID,
    body: DecisionRequest,
    organization_id: uuid.UUID = Query(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    try:
        require_org_permission(db, user, "interviews.manage", organization_id)
        session = engine.record_decision(
            db, user.id, session_id, organization_id, body.decision, body.note
        )
        return {"session_id": str(session.id), "decision": session.decision}
    except AppError as exc:
        raise _raise_app(exc) from exc


# --- Candidate side (entry-token bound) ----------------------------------------

@router.post("/claim")
def claim_session(
    body: EntryTokenIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Resolve the session the entry token opens — for the candidate's own person."""
    try:
        from app.services.ai_interview import _claim_candidate, _lazy_expire

        session = engine._get_session_by_token(db, body.entry_token)
        session = _claim_candidate(db, user.id, session.id, body.entry_token)
        _lazy_expire(db, session)
        db.commit()
        return engine.candidate_view(db, session)
    except AppError as exc:
        raise _raise_app(exc) from exc


@router.post("/{session_id}/consent",
             dependencies=[Depends(rate_limit_dependency("ai_interview.respond"))])
def grant_consent(
    session_id: uuid.UUID,
    body: ConsentRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    x_interview_token: Optional[str] = Header(default=None),
) -> dict:
    try:
        session = engine.grant_consent(
            db, user.id, session_id, _entry_token_header(x_interview_token),
            mic=body.mic, camera=body.camera, recording=body.recording,
        )
        return {"session_id": str(session.id), "status": session.status}
    except AppError as exc:
        raise _raise_app(exc) from exc


@router.post("/{session_id}/consent/withdraw")
def withdraw_consent(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    x_interview_token: Optional[str] = Header(default=None),
) -> dict:
    try:
        session = engine.withdraw_consent(
            db, user.id, session_id, _entry_token_header(x_interview_token)
        )
        return {"session_id": str(session.id), "status": session.status}
    except AppError as exc:
        raise _raise_app(exc) from exc


@router.post("/{session_id}/start")
def start_interview(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    x_interview_token: Optional[str] = Header(default=None),
) -> dict:
    try:
        return engine.start(db, user.id, session_id, _entry_token_header(x_interview_token))
    except AppError as exc:
        raise _raise_app(exc) from exc


@router.get("/{session_id}/next-question")
def next_question(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    x_interview_token: Optional[str] = Header(default=None),
) -> dict:
    try:
        return engine.get_next_question(
            db, user.id, session_id, _entry_token_header(x_interview_token)
        )
    except AppError as exc:
        raise _raise_app(exc) from exc


@router.post("/{session_id}/responses",
             dependencies=[Depends(rate_limit_dependency("ai_interview.respond"))])
def submit_response(
    session_id: uuid.UUID,
    body: ResponseRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    x_interview_token: Optional[str] = Header(default=None),
) -> dict:
    try:
        return engine.submit_response(
            db, user.id, session_id, _entry_token_header(x_interview_token),
            body.question_id, body.answer,
        )
    except AppError as exc:
        raise _raise_app(exc) from exc


@router.post("/{session_id}/repeat")
def repeat_question(
    session_id: uuid.UUID,
    body: RepeatRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    x_interview_token: Optional[str] = Header(default=None),
) -> dict:
    try:
        return engine.repeat_question(
            db, user.id, session_id, _entry_token_header(x_interview_token), body.question_id
        )
    except AppError as exc:
        raise _raise_app(exc) from exc


@router.post("/{session_id}/pause")
def pause_interview(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    x_interview_token: Optional[str] = Header(default=None),
) -> dict:
    try:
        session = engine.pause(db, user.id, session_id, _entry_token_header(x_interview_token))
        return {"session_id": str(session.id), "status": session.status}
    except AppError as exc:
        raise _raise_app(exc) from exc


@router.post("/{session_id}/resume")
def resume_interview(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    x_interview_token: Optional[str] = Header(default=None),
) -> dict:
    try:
        session = engine.resume(db, user.id, session_id, _entry_token_header(x_interview_token))
        return {"session_id": str(session.id), "status": session.status}
    except AppError as exc:
        raise _raise_app(exc) from exc


@router.post("/{session_id}/complete")
def complete_interview(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    x_interview_token: Optional[str] = Header(default=None),
) -> dict:
    try:
        return engine.complete(db, user.id, session_id, _entry_token_header(x_interview_token))
    except AppError as exc:
        raise _raise_app(exc) from exc


@router.post("/{session_id}/integrity-signals")
def integrity_signal(
    session_id: uuid.UUID,
    body: IntegritySignalRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    x_interview_token: Optional[str] = Header(default=None),
) -> dict:
    try:
        session = engine.record_integrity_signal(
            db, user.id, session_id, _entry_token_header(x_interview_token),
            body.signal_type, body.detail,
        )
        return {
            "session_id": str(session.id),
            "recorded": True,
            "note": "Signal recorded as a review signal only.",
        }
    except AppError as exc:
        raise _raise_app(exc) from exc


@router.get("/{session_id}/feedback")
def candidate_feedback(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    x_interview_token: Optional[str] = Header(default=None),
) -> dict:
    try:
        return engine.candidate_feedback(
            db, user.id, session_id, _entry_token_header(x_interview_token)
        )
    except AppError as exc:
        raise _raise_app(exc) from exc