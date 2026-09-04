"""Interview preparation API — candidate-owned mock-interview practice.

Preparation layer only: no live interviewer, no recording, no biometrics.
Sessions are metadata containers with lazy expiry and owner deletion;
questions/answers are generated and evaluated at request time and are
never persisted by these endpoints (mock turns run inside an Athena chat
only if the candidate chooses that surface, under its retention policy).
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.errors import AppError
from app.db.session import get_db
from app.models.identity import User
from app.schemas.career import (
    PrepAnswerRequest,
    PrepQuestionsRequest,
    PrepSessionCreateRequest,
)
from app.services import interview_prep as prep

router = APIRouter(prefix="/interview-prep", tags=["interview-prep"])


def _raise_app(exc: AppError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=exc.message)


@router.post("/sessions", status_code=201)
def create_session(
    body: PrepSessionCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    try:
        session = prep.create_session(
            db,
            user.id,
            opportunity_id=body.opportunity_id,
            application_id=body.application_id,
            interview_id=body.interview_id,
            focus_areas=body.focus_areas,
        )
    except AppError as exc:
        raise _raise_app(exc) from exc
    return prep.session_out(session)


@router.get("/sessions")
def list_sessions(
    active_only: bool = Query(default=False),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list:
    sessions = prep.list_owned_sessions(
        db, user.id, include_completed=not active_only, limit=limit
    )
    return [prep.session_out(s) for s in sessions]


@router.get("/sessions/{session_id}")
def get_session(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    try:
        session = prep.get_session_for_user(db, user.id, session_id)
    except AppError as exc:
        raise _raise_app(exc) from exc
    return prep.session_out(session)


@router.post("/sessions/{session_id}/questions")
def session_questions(
    session_id: uuid.UUID,
    body: PrepQuestionsRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    try:
        return prep.generate_questions(
            db,
            user.id,
            session_id,
            count=body.count,
            categories=body.categories,
        )
    except AppError as exc:
        raise _raise_app(exc) from exc


@router.post("/sessions/{session_id}/answers")
def evaluate_answer(
    session_id: uuid.UUID,
    body: PrepAnswerRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    try:
        return prep.evaluate_answer(
            db,
            user.id,
            session_id,
            question=body.question,
            answer=body.answer,
        )
    except AppError as exc:
        raise _raise_app(exc) from exc


@router.post("/sessions/{session_id}/complete")
def complete_session(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    try:
        session = prep.complete_session(db, user.id, session_id)
    except AppError as exc:
        raise _raise_app(exc) from exc
    return prep.session_out(session)


@router.delete("/sessions/{session_id}", status_code=204)
def delete_session(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    from fastapi import Response

    try:
        prep.delete_session(db, user.id, session_id)
    except AppError as exc:
        raise _raise_app(exc) from exc
    return Response(status_code=204)
