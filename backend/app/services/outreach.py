"""Controlled Talent Outreach service (Phase 8).

DISCOVER -> REQUEST -> CONSENT -> CONNECT -> COMMUNICATE -> APPLY

This module owns the REQUEST step:

- A member of an organization may request contact with a candidate they can
  legitimately see (discoverable OR already in the org's pipeline). The
  request carries the opportunity context and an introduction message —
  sending NEVER reveals private contact details.
- The candidate decides: accept (opens a controlled conversation through
  ``services.communications``), decline, report, or block the organization.
- Abuse controls are structural: a candidate can only be the target of one
  live request per organization, a cooldown window applies after any
  previous request, requests expire, and a blocked organization can never
  reach the candidate again until the candidate removes the block.
"""
from __future__ import annotations

import uuid
from datetime import timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import (
    ConflictError,
    InvalidInputError,
    NotFoundError,
    PermissionDeniedError,
)
from app.core.timeutil import utc_now_naive
from app.models.communication import OutreachBlock, OutreachRequest
from app.models.enums import (
    OUTREACH_ACTIONABLE,
    OUTREACH_CANCELLABLE,
    OUTREACH_STATUS_BLOCKED,
    OUTREACH_STATUS_CANCELLED,
    OUTREACH_STATUS_DECLINED,
    OUTREACH_STATUS_EXPIRED,
)
from app.models.identity import PersonProfile, User
from app.models.tenancy import Organization

# Statuses that keep a request "live" (duplicate/cooldown guards).
_LIVE_STATUSES = {"sent", "viewed"}


# --- helpers -----------------------------------------------------------------

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


def _candidate_user_id(db: Session, person_id: uuid.UUID) -> Optional[uuid.UUID]:
    person = db.get(PersonProfile, person_id)
    return person.user_id if person else None


def _display_name(db: Session, person: PersonProfile) -> Optional[str]:
    user = db.get(User, person.user_id) if person else None
    return person.preferred_name or (user.full_name if user else None)


def _person_visible(db: Session, person_id: uuid.UUID, organization_id: uuid.UUID) -> bool:
    """Can this organization legitimately see the person? Same rule as the
    Talent Graph: opted into discovery OR already in this org's pipeline."""
    from app.services import talent as talent_service

    return talent_service.person_visible_to_org(db, person_id, organization_id)


def _expire_stale(db: Session) -> None:
    """Mark requests past their expiry as expired (sent/viewed only)."""
    now = utc_now_naive()
    stale = db.scalars(
        select(OutreachRequest).where(
            OutreachRequest.status.in_(_LIVE_STATUSES),
            OutreachRequest.expires_at.is_not(None),
            OutreachRequest.expires_at < now,
        )
    ).all()
    if not stale:
        return
    for request in stale:
        request.status = OUTREACH_STATUS_EXPIRED
        request.responded_at = now
    db.commit()


def _owned_org_request(
    db: Session, organization_id: uuid.UUID, request_id: uuid.UUID
) -> OutreachRequest:
    request = db.get(OutreachRequest, request_id)
    if request is None or request.organization_id != organization_id:
        raise NotFoundError("Outreach request not found.")
    return request


def _owned_person_request(
    db: Session, person_id: uuid.UUID, request_id: uuid.UUID
) -> OutreachRequest:
    request = db.get(OutreachRequest, request_id)
    if request is None or request.person_id != person_id:
        raise NotFoundError("Outreach request not found.")
    return request


# --- payloads ----------------------------------------------------------------

def outreach_company_out(db: Session, request: OutreachRequest) -> dict:
    """Company-side view of one request (candidate name/headline visible to
    the org; no private candidate data is added)."""
    person = db.get(PersonProfile, request.person_id)
    org = db.get(Organization, request.organization_id)
    requester = db.get(User, request.requester_id)
    opp_title = None
    if request.opportunity_id:
        from app.models.career import Opportunity

        opp = db.get(Opportunity, request.opportunity_id)
        opp_title = opp.title if opp else None
    return {
        "id": str(request.id),
        "organization_id": str(request.organization_id),
        "organization_name": org.name if org else None,
        "candidate": {
            "person_id": str(request.person_id),
            "name": _display_name(db, person),
            "headline": person.headline if person else None,
        },
        "opportunity_id": str(request.opportunity_id) if request.opportunity_id else None,
        "opportunity_title": opp_title,
        "application_id": str(request.application_id) if request.application_id else None,
        "message": request.message,
        "context": request.context,
        "status": request.status,
        "requester_id": str(request.requester_id),
        "requester_name": requester.full_name if requester else None,
        "created_at": request.created_at,
        "expires_at": request.expires_at,
        "viewed_at": request.viewed_at,
        "responded_at": request.responded_at,
        "note": request.note,
    }


def outreach_candidate_out(db: Session, request: OutreachRequest) -> dict:
    """Candidate-side view of one request (who, why, which opportunity, and
    NO private contact details of their own are echoed — they own them)."""
    org = db.get(Organization, request.organization_id)
    opp_title = None
    opp_company = None
    if request.opportunity_id:
        from app.models.career import Opportunity

        opp = db.get(Opportunity, request.opportunity_id)
        if opp:
            opp_title = opp.title
            opp_company = opp.company_name
    return {
        "id": str(request.id),
        "organization": {
            "id": str(request.organization_id),
            "name": org.name if org else None,
        },
        "opportunity": (
            {"id": str(request.opportunity_id), "title": opp_title,
             "company": opp_company}
            if request.opportunity_id
            else None
        ),
        "message": request.message,
        "context": request.context,
        "status": request.status,
        "created_at": request.created_at,
        "expires_at": request.expires_at,
        "responded_at": request.responded_at,
        "conversation_id": str(request.conversation_id) if request.conversation_id else None,
    }


# --- create / send -----------------------------------------------------------

def create_outreach(
    db: Session,
    organization_id: uuid.UUID,
    actor_id: uuid.UUID,
    *,
    person_id: uuid.UUID,
    message: str,
    opportunity_id: Optional[uuid.UUID] = None,
    context: Optional[str] = None,
) -> OutreachRequest:
    """Create + send one outreach request. Candidate remains in control; no
    private contact information is ever exposed by sending."""
    _require_member(db, organization_id, actor_id)
    org = _org(db, organization_id)
    if org.kind not in {"employer", "recruiter"}:
        raise InvalidInputError("Only hiring organizations can send outreach.")
    person = _person(db, person_id)
    if not _person_visible(db, person.id, organization_id):
        # Do not reveal the existence of a non-visible person.
        raise NotFoundError("Candidate not found.")

    # Standing block: candidate said this organization may not contact them.
    blocked = db.scalar(
        select(OutreachBlock.id).where(
            OutreachBlock.person_id == person.id,
            OutreachBlock.organization_id == organization_id,
        ).limit(1)
    )
    if blocked is not None:
        raise PermissionDeniedError(
            "This candidate has asked not to be contacted by your organization."
        )

    # The opportunity must belong to this organization (tenant scope).
    application_id = None
    if opportunity_id is not None:
        from app.models.career import JobApplication, Opportunity

        opp = db.get(Opportunity, opportunity_id)
        if opp is None or opp.company_id != organization_id:
            raise NotFoundError("Opportunity not found.")
        existing_application = db.scalar(
            select(JobApplication).where(
                JobApplication.person_id == person.id,
                JobApplication.opportunity_id == opp.id,
            ).limit(1)
        )
        if existing_application is not None:
            application_id = existing_application.id

    # Abuse controls: one live request per (org, person); cooldown after any
    # previous request regardless of outcome.
    live = db.scalar(
        select(OutreachRequest).where(
            OutreachRequest.organization_id == organization_id,
            OutreachRequest.person_id == person.id,
            OutreachRequest.status.in_(_LIVE_STATUSES),
        ).limit(1)
    )
    if live is not None:
        raise ConflictError(
            "An outreach request to this candidate is already pending."
        )
    settings = get_settings()
    cooldown_start = utc_now_naive() - timedelta(days=settings.outreach_cooldown_days)
    recent = db.scalar(
        select(OutreachRequest).where(
            OutreachRequest.organization_id == organization_id,
            OutreachRequest.person_id == person.id,
            OutreachRequest.created_at >= cooldown_start,
        ).order_by(OutreachRequest.created_at.desc()).limit(1)
    )
    if recent is not None:
        raise ConflictError(
            "Your organization recently contacted this candidate. Please wait "
            "before sending another request."
        )

    request = OutreachRequest(
        organization_id=organization_id,
        requester_id=actor_id,
        person_id=person.id,
        opportunity_id=opportunity_id,
        application_id=application_id,
        message=message.strip(),
        context=(context or "").strip() or None,
        status="sent",
        expires_at=utc_now_naive()
        + timedelta(days=settings.outreach_expiry_days),
    )
    db.add(request)
    db.commit()
    db.refresh(request)
    return request


# --- company side ------------------------------------------------------------

def list_org_outreach(
    db: Session, organization_id: uuid.UUID, status: Optional[str] = None
) -> list:
    """All outreach requests sent by one organization (recruiter view)."""
    _expire_stale(db)
    query = select(OutreachRequest).where(
        OutreachRequest.organization_id == organization_id
    )
    if status:
        if status not in {
            "sent", "viewed", "accepted", "declined", "expired",
            "cancelled", "blocked",
        }:
            raise InvalidInputError(f"Unknown outreach status '{status}'.")
        query = query.where(OutreachRequest.status == status)
    requests = db.scalars(
        query.order_by(OutreachRequest.created_at.desc())
    ).all()
    return [outreach_company_out(db, r) for r in requests]


def get_org_outreach(
    db: Session, organization_id: uuid.UUID, request_id: uuid.UUID
) -> dict:
    request = _owned_org_request(db, organization_id, request_id)
    _expire_stale(db)
    return outreach_company_out(db, request)


def cancel_outreach(
    db: Session, organization_id: uuid.UUID, request_id: uuid.UUID, actor_id: uuid.UUID
) -> OutreachRequest:
    """Withdraw a live request. The original requester, or any member holding
    outreach.manage, may cancel."""
    _require_member(db, organization_id, actor_id)
    request = _owned_org_request(db, organization_id, request_id)
    from app.services import authz
    from app.models.enums import PERMISSION_OUTREACH_MANAGE

    can_manage = authz.has_permission(
        db, actor_id, PERMISSION_OUTREACH_MANAGE, organization_id
    )
    if request.requester_id != actor_id and not can_manage:
        raise PermissionDeniedError(
            "Only the requester or an outreach manager can cancel this request."
        )
    if request.status not in OUTREACH_CANCELLABLE:
        raise InvalidInputError(
            f"An outreach request with status '{request.status}' cannot be cancelled."
        )
    request.status = OUTREACH_STATUS_CANCELLED
    request.responded_at = utc_now_naive()
    db.commit()
    db.refresh(request)
    return request


# --- candidate side ----------------------------------------------------------

def list_candidate_outreach(db: Session, person_id: uuid.UUID) -> list:
    """Every outreach addressed to this person (candidate inbox)."""
    _expire_stale(db)
    requests = db.scalars(
        select(OutreachRequest)
        .where(OutreachRequest.person_id == person_id)
        .order_by(OutreachRequest.created_at.desc())
    ).all()
    return [outreach_candidate_out(db, r) for r in requests]


def get_candidate_outreach(
    db: Session, person_id: uuid.UUID, request_id: uuid.UUID, actor_id: uuid.UUID
) -> dict:
    """Candidate reads one request (marks it viewed on first open)."""
    request = _owned_person_request(db, person_id, request_id)
    if request.status == "sent":
        request.status = "viewed"
        request.viewed_at = utc_now_naive()
        db.commit()
        db.refresh(request)
    return outreach_candidate_out(db, request)


def accept_outreach(
    db: Session, person_id: uuid.UUID, request_id: uuid.UUID, actor_id: uuid.UUID
) -> dict:
    """Candidate accepts -> a controlled conversation is opened. Acceptance
    grants in-platform communication only — never private contact details."""
    request = _owned_person_request(db, person_id, request_id)
    _expire_stale(db)
    if request.status not in OUTREACH_ACTIONABLE:
        raise InvalidInputError(
            f"An outreach request with status '{request.status}' cannot be accepted."
        )
    if request.status == OUTREACH_STATUS_EXPIRED:
        raise InvalidInputError("This outreach request has expired.")
    request.status = "accepted"
    request.responded_at = utc_now_naive()

    from app.services.communications import create_conversation

    conversation = create_conversation(
        db,
        organization_id=request.organization_id,
        person_id=request.person_id,
        actor_id=actor_id,
        opportunity_id=request.opportunity_id,
        application_id=request.application_id,
        outreach_id=request.id,
    )
    request.conversation_id = conversation.id
    db.commit()
    db.refresh(request)
    return {
        "id": str(request.id),
        "status": request.status,
        "conversation_id": str(conversation.id),
    }


def decline_outreach(
    db: Session,
    person_id: uuid.UUID,
    request_id: uuid.UUID,
    note: Optional[str] = None,
) -> dict:
    request = _owned_person_request(db, person_id, request_id)
    if request.status not in OUTREACH_ACTIONABLE:
        raise InvalidInputError(
            f"An outreach request with status '{request.status}' cannot be declined."
        )
    request.status = OUTREACH_STATUS_DECLINED
    request.responded_at = utc_now_naive()
    request.note = note
    db.commit()
    db.refresh(request)
    return {"id": str(request.id), "status": request.status}


def report_outreach(
    db: Session, person_id: uuid.UUID, request_id: uuid.UUID, actor_id: uuid.UUID,
    note: Optional[str] = None,
) -> dict:
    """Candidate reports an outreach: request is marked blocked and the
    organization is added to the candidate's standing block list."""
    request = _owned_person_request(db, person_id, request_id)
    request.status = OUTREACH_STATUS_BLOCKED
    request.responded_at = utc_now_naive()
    request.note = note
    add_block(db, person_id, request.organization_id, actor_id, reason=note)
    db.commit()
    db.refresh(request)
    return {"id": str(request.id), "status": request.status}


# --- candidate blocks ----------------------------------------------------------

def add_block(
    db: Session,
    person_id: uuid.UUID,
    organization_id: uuid.UUID,
    actor_id: uuid.UUID,
    reason: Optional[str] = None,
) -> OutreachBlock:
    existing = db.scalar(
        select(OutreachBlock).where(
            OutreachBlock.person_id == person_id,
            OutreachBlock.organization_id == organization_id,
        ).limit(1)
    )
    if existing is not None:
        return existing
    block = OutreachBlock(
        person_id=person_id,
        organization_id=organization_id,
        created_by=actor_id,
        reason=(reason or "")[:300] or None,
    )
    db.add(block)
    db.flush()
    # Any pending requests from this organization become blocked too.
    pending = db.scalars(
        select(OutreachRequest).where(
            OutreachRequest.organization_id == organization_id,
            OutreachRequest.person_id == person_id,
            OutreachRequest.status.in_(_LIVE_STATUSES),
        )
    ).all()
    for request in pending:
        request.status = OUTREACH_STATUS_BLOCKED
        request.responded_at = utc_now_naive()
    return block


def block_organization(
    db: Session,
    person_id: uuid.UUID,
    organization_id: uuid.UUID,
    actor_id: uuid.UUID,
    reason: Optional[str] = None,
) -> OutreachBlock:
    block = add_block(db, person_id, organization_id, actor_id, reason=reason)
    db.commit()
    db.refresh(block)
    return block


def unblock_organization(
    db: Session, person_id: uuid.UUID, organization_id: uuid.UUID, actor_id: uuid.UUID
) -> None:
    """Remove a block (only the person's own account may do so)."""
    person = _person(db, person_id)
    if person.user_id != actor_id:
        raise PermissionDeniedError("Only the candidate can change their blocks.")
    block = db.scalar(
        select(OutreachBlock).where(
            OutreachBlock.person_id == person_id,
            OutreachBlock.organization_id == organization_id,
        ).limit(1)
    )
    if block is None:
        raise NotFoundError("This organization is not blocked.")
    db.delete(block)
    db.commit()


def list_blocks(db: Session, person_id: uuid.UUID) -> list:
    blocks = db.scalars(
        select(OutreachBlock)
        .where(OutreachBlock.person_id == person_id)
        .order_by(OutreachBlock.created_at.desc())
    ).all()
    result = []
    for block in blocks:
        org = db.get(Organization, block.organization_id)
        result.append(
            {
                "organization_id": str(block.organization_id),
                "organization_name": org.name if org else None,
                "reason": block.reason,
                "created_at": block.created_at,
            }
        )
    return result
