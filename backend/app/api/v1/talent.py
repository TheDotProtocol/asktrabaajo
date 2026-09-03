"""/api/v1/talent — the Talent Graph & Opportunity Intelligence API.

Every route is organization-scoped and permission-gated (``candidates.search``
/ ``pools.manage`` from the RBAC catalog). Discovery returns ONLY public Work
ID data; private sections, documents and contact details never leak through
search, profiles or matches. Company A can never read Company B's pools,
saved candidates or opportunity matches (membership + tenant scoping).
"""
from __future__ import annotations

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_org_permission
from app.core.errors import NotFoundError
from app.core.ratelimit import rate_limit_dependency
from app.db.session import get_db
from app.models.communication import Conversation
from app.models.enums import (
    PERMISSION_CANDIDATES_SEARCH,
    PERMISSION_COMMUNICATIONS_MANAGE,
    PERMISSION_COMMUNICATIONS_READ,
    PERMISSION_COMMUNICATIONS_SEND,
    PERMISSION_OUTREACH_CREATE,
    PERMISSION_OUTREACH_MANAGE,
    PERMISSION_OUTREACH_READ,
    PERMISSION_POOLS_MANAGE,
)
from app.models.identity import PersonProfile, User
from app.models.tenancy import Organization
from app.models.work import Skill
from app.schemas.common import MessageResponse
from app.schemas.communication import (
    ConversationOut,
    MessageOut,
    MessageSend,
    OpenConversationRequest,
    OutreachCompanyOut,
    OutreachCreate,
)
from app.schemas.talent import (
    CandidateSearchList,
    MatchedCandidateList,
    NormalizeRequest,
    NormalizeResult,
    PoolCreate,
    PoolMemberAdd,
    PoolMemberOut,
    RequirementOut,
    SaveCandidateRequest,
    SavedCandidateOut,
    SkillDetailOut,
    TaxonomyListOut,
    TaxonomySkillOut,
    TalentPoolDetailOut,
    TalentPoolOut,
)
from app.services import audit as audit_service
from app.services import communications as communications_service
from app.services import events as events_service
from app.services import notifications as notifications_service
from app.services import outreach as outreach_service
from app.services import skills_registry
from app.services import talent as talent_service

outreach_limit = rate_limit_dependency("outreach.create")
message_send_limit = rate_limit_dependency("message.send")
search_limit = rate_limit_dependency("candidates.search")

router = APIRouter(prefix="/talent", tags=["talent"])


def _candidate_name(db: Session, person_id: uuid.UUID) -> Optional[str]:
    person = db.get(PersonProfile, person_id)
    if person is None:
        return None
    user = db.get(User, person.user_id)
    return person.preferred_name or (user.full_name if user else None)


def _candidate_headline(db: Session, person_id: uuid.UUID) -> Optional[str]:
    person = db.get(PersonProfile, person_id)
    return person.headline if person else None


def _parse_skills(skills_csv: Optional[str]) -> Optional[List[str]]:
    if not skills_csv:
        return None
    return [s.strip() for s in skills_csv.split(",") if s.strip()]


# --- taxonomy -------------------------------------------------------------------


@router.get("/{organization_id}/skills", response_model=TaxonomyListOut)
def list_taxonomy(
    organization_id: uuid.UUID,
    q: Optional[str] = Query(None, max_length=200),
    category: Optional[str] = Query(None, max_length=60),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TaxonomyListOut:
    require_org_permission(db, user, PERMISSION_CANDIDATES_SEARCH, organization_id)
    result = skills_registry.list_taxonomy(db, q=q, category=category, page=page,
                                           page_size=page_size)
    return TaxonomyListOut(
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
        categories=skills_registry.taxonomy_categories(db),
        items=[TaxonomySkillOut.model_validate(s) for s in result["items"]],
    )


@router.get("/{organization_id}/skills/categories", response_model=List[str])
def taxonomy_categories(
    organization_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list:
    require_org_permission(db, user, PERMISSION_CANDIDATES_SEARCH, organization_id)
    return skills_registry.taxonomy_categories(db)


@router.get("/{organization_id}/skills/{skill_id}", response_model=SkillDetailOut)
def taxonomy_skill(
    organization_id: uuid.UUID,
    skill_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    require_org_permission(db, user, PERMISSION_CANDIDATES_SEARCH, organization_id)
    detail = skills_registry.skill_detail(db, skill_id)
    if detail is None:
        raise NotFoundError("Skill not found.")
    return detail


@router.post("/{organization_id}/skills/normalize", response_model=NormalizeResult)
def normalize_skill(
    organization_id: uuid.UUID,
    body: NormalizeRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NormalizeResult:
    """Resolve free text to a canonical taxonomy skill (no creation)."""
    require_org_permission(db, user, PERMISSION_CANDIDATES_SEARCH, organization_id)
    token = skills_registry.normalize(body.text)
    skill = skills_registry.resolve_skill(db, body.text)
    return NormalizeResult(
        raw=body.text,
        normalized=token,
        canonical={"id": str(skill.id), "name": skill.name} if skill else None,
    )


# --- candidate discovery ---------------------------------------------------------


@router.get("/{organization_id}/candidates/search", response_model=CandidateSearchList)
def search_candidates(
    organization_id: uuid.UUID,
    q: Optional[str] = Query(None, max_length=200),
    skills: Optional[str] = Query(None, max_length=400, description="Comma-separated"),
    location: Optional[str] = Query(None, max_length=120),
    country: Optional[str] = Query(None, max_length=80),
    min_years: Optional[float] = Query(None, ge=0, le=50),
    seniority: Optional[str] = Query(None, max_length=40),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    _rl: None = Depends(search_limit),
    db: Session = Depends(get_db),
) -> CandidateSearchList:
    require_org_permission(db, user, PERMISSION_CANDIDATES_SEARCH, organization_id)
    result = talent_service.search_candidates(
        db,
        organization_id,
        user.id,
        q=q,
        skills=_parse_skills(skills),
        location=location,
        country=country,
        min_years=min_years,
        seniority=seniority,
        page=page,
        page_size=page_size,
    )
    audit_service.record(
        db,
        actor_id=user.id,
        action="talent.search",
        resource_type="candidate_search",
        organization_id=organization_id,
        metadata={"q": q, "skills": skills, "page": page, "results": result["total"]},
    )
    db.commit()
    return CandidateSearchList(**result)


@router.get("/{organization_id}/candidates/saved", response_model=List[SavedCandidateOut])
def list_saved_candidates(
    organization_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list:
    require_org_permission(db, user, PERMISSION_POOLS_MANAGE, organization_id)
    items = talent_service.list_saved_candidates(db, organization_id, user.id)
    return [SavedCandidateOut(**i) for i in items]


@router.get("/{organization_id}/candidates/{person_id}")
def candidate_profile(
    organization_id: uuid.UUID,
    person_id: uuid.UUID,
    opportunity_id: Optional[uuid.UUID] = Query(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Discovery-safe candidate profile with progressive disclosure."""
    require_org_permission(db, user, PERMISSION_CANDIDATES_SEARCH, organization_id)
    payload = talent_service.candidate_profile_for_org(
        db, organization_id, person_id, user.id, opportunity_id=opportunity_id
    )
    audit_service.record(
        db,
        actor_id=user.id,
        action="talent.candidate.viewed",
        resource_type="person_profile",
        resource_id=person_id,
        organization_id=organization_id,
    )
    db.commit()
    return payload


@router.post(
    "/{organization_id}/candidates/{person_id}/saved",
    response_model=SavedCandidateOut,
)
def save_candidate(
    organization_id: uuid.UUID,
    person_id: uuid.UUID,
    body: SaveCandidateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    require_org_permission(db, user, PERMISSION_POOLS_MANAGE, organization_id)
    saved = talent_service.save_candidate(
        db, organization_id, person_id, user.id, note=body.note, tags=body.tags
    )
    audit_service.record(
        db,
        actor_id=user.id,
        action="talent.candidate.saved",
        resource_type="saved_candidate",
        resource_id=saved.id,
        organization_id=organization_id,
        metadata={"person_id": str(person_id)},
    )
    db.commit()
    return {
        "id": str(saved.id),
        "person_id": str(person_id),
        "name": _candidate_name(db, person_id),
        "headline": _candidate_headline(db, person_id),
        "note": saved.note,
        "tags": saved.tags,
        "saved_at": saved.created_at,
        "context": "discovery",
    }


@router.delete(
    "/{organization_id}/candidates/{person_id}/saved", response_model=MessageResponse
)
def unsave_candidate(
    organization_id: uuid.UUID,
    person_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    require_org_permission(db, user, PERMISSION_POOLS_MANAGE, organization_id)
    talent_service.unsave_candidate(db, organization_id, person_id, user.id)
    audit_service.record(
        db,
        actor_id=user.id,
        action="talent.candidate.unsaved",
        resource_type="saved_candidate",
        organization_id=organization_id,
        metadata={"person_id": str(person_id)},
    )
    db.commit()
    return MessageResponse(message="Candidate removed from your saved list.")


# --- ranked matches ---------------------------------------------------------------


@router.get(
    "/{organization_id}/opportunities/{opportunity_id}/candidates",
    response_model=MatchedCandidateList,
)
def opportunity_candidates(
    organization_id: uuid.UUID,
    opportunity_id: uuid.UUID,
    exclude_applied: bool = Query(True),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MatchedCandidateList:
    require_org_permission(db, user, PERMISSION_CANDIDATES_SEARCH, organization_id)
    result = talent_service.match_candidates_for_opportunity(
        db, organization_id, opportunity_id, user.id,
        exclude_applied=exclude_applied, page=page, page_size=page_size,
    )
    audit_service.record(
        db,
        actor_id=user.id,
        action="talent.opportunity.matches.viewed",
        resource_type="opportunity",
        resource_id=opportunity_id,
        organization_id=organization_id,
        metadata={"page": page, "results": result["total"]},
    )
    db.commit()
    return MatchedCandidateList(**result)


@router.get(
    "/{organization_id}/opportunities/{opportunity_id}/requirements",
    response_model=List[RequirementOut],
)
def opportunity_requirements(
    organization_id: uuid.UUID,
    opportunity_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list:
    """Structured requirements for an opportunity (raw employer wording
    preserved; canonical skill linked when one resolves)."""
    require_org_permission(db, user, PERMISSION_CANDIDATES_SEARCH, organization_id)
    from app.models.career import Opportunity

    opp = db.get(Opportunity, opportunity_id)
    if opp is None or opp.company_id != organization_id:
        raise NotFoundError("Opportunity not found.")
    skills_registry.normalize_opportunity_requirements(db, opp)
    db.commit()
    from app.models.talent import OpportunityRequirement

    rows = db.scalars(
        select(OpportunityRequirement).where(
            OpportunityRequirement.opportunity_id == opportunity_id
        )
    ).all()
    return [
        {
            "id": str(r.id),
            "skill": db.get(Skill, r.skill_id).name if r.skill_id else None,
            "raw_text": r.raw_text,
            "requirement_kind": r.requirement_kind,
            "min_years": r.min_years,
        }
        for r in rows
    ]


# --- talent pools -----------------------------------------------------------------


@router.get("/{organization_id}/pools", response_model=List[TalentPoolOut])
def list_pools(
    organization_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list:
    require_org_permission(db, user, PERMISSION_POOLS_MANAGE, organization_id)
    pools = talent_service.list_pools(db, organization_id, user.id)
    return [TalentPoolOut(**p) for p in pools]


@router.post("/{organization_id}/pools", response_model=TalentPoolOut, status_code=201)
def create_pool(
    organization_id: uuid.UUID,
    body: PoolCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    require_org_permission(db, user, PERMISSION_POOLS_MANAGE, organization_id)
    pool = talent_service.create_pool(
        db, organization_id, user.id, name=body.name, description=body.description
    )
    audit_service.record(
        db,
        actor_id=user.id,
        action="talent.pool.created",
        resource_type="talent_pool",
        resource_id=pool.id,
        organization_id=organization_id,
    )
    db.commit()
    return {
        "id": str(pool.id),
        "name": pool.name,
        "description": pool.description,
        "created_at": pool.created_at,
        "member_count": 0,
    }


@router.get("/{organization_id}/pools/{pool_id}", response_model=TalentPoolDetailOut)
def pool_detail(
    organization_id: uuid.UUID,
    pool_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TalentPoolDetailOut:
    require_org_permission(db, user, PERMISSION_POOLS_MANAGE, organization_id)
    detail = talent_service.pool_detail(db, organization_id, pool_id, user.id)
    return TalentPoolDetailOut(**detail)


@router.delete("/{organization_id}/pools/{pool_id}", response_model=MessageResponse)
def delete_pool(
    organization_id: uuid.UUID,
    pool_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    require_org_permission(db, user, PERMISSION_POOLS_MANAGE, organization_id)
    talent_service.delete_pool(db, organization_id, pool_id, user.id)
    audit_service.record(
        db,
        actor_id=user.id,
        action="talent.pool.deleted",
        resource_type="talent_pool",
        resource_id=pool_id,
        organization_id=organization_id,
    )
    db.commit()
    return MessageResponse(message="Talent pool deleted.")


@router.post(
    "/{organization_id}/pools/{pool_id}/members", response_model=PoolMemberOut,
    status_code=201,
)
def add_pool_member(
    organization_id: uuid.UUID,
    pool_id: uuid.UUID,
    body: PoolMemberAdd,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    require_org_permission(db, user, PERMISSION_POOLS_MANAGE, organization_id)
    member = talent_service.add_pool_member(
        db, organization_id, pool_id, body.person_id, user.id, note=body.note
    )
    audit_service.record(
        db,
        actor_id=user.id,
        action="talent.pool.member_added",
        resource_type="talent_pool_member",
        resource_id=member.id,
        organization_id=organization_id,
        metadata={"person_id": str(body.person_id), "pool_id": str(pool_id)},
    )
    db.commit()
    return {
        "person_id": str(body.person_id),
        "name": _candidate_name(db, body.person_id),
        "headline": _candidate_headline(db, body.person_id),
        "note": member.note,
        "added_at": member.created_at,
    }


@router.delete(
    "/{organization_id}/pools/{pool_id}/members/{person_id}",
    response_model=MessageResponse,
)
def remove_pool_member(
    organization_id: uuid.UUID,
    pool_id: uuid.UUID,
    person_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    require_org_permission(db, user, PERMISSION_POOLS_MANAGE, organization_id)
    talent_service.remove_pool_member(db, organization_id, pool_id, person_id, user.id)
    audit_service.record(
        db,
        actor_id=user.id,
        action="talent.pool.member_removed",
        resource_type="talent_pool_member",
        organization_id=organization_id,
        metadata={"person_id": str(person_id), "pool_id": str(pool_id)},
    )
    db.commit()
    return MessageResponse(message="Candidate removed from the pool.")


# --- Controlled outreach + communications (Phase 8) ----------------------------


def _candidate_user_id(db: Session, person_id: uuid.UUID):
    person = db.get(PersonProfile, person_id)
    return person.user_id if person else None


def _opportunity_title(db: Session, opportunity_id) -> Optional[str]:
    if opportunity_id is None:
        return None
    from app.models.career import Opportunity

    opp = db.get(Opportunity, opportunity_id)
    return opp.title if opp else None


@router.post("/{organization_id}/outreach", response_model=OutreachCompanyOut,
             status_code=201)
def create_outreach(
    organization_id: uuid.UUID,
    body: OutreachCreate,
    user: User = Depends(get_current_user),
    _rl: None = Depends(outreach_limit),
    db: Session = Depends(get_db),
) -> dict:
    """Request contact with a candidate (candidate stays in control)."""
    require_org_permission(db, user, PERMISSION_OUTREACH_CREATE, organization_id)
    request = outreach_service.create_outreach(
        db,
        organization_id,
        user.id,
        person_id=body.person_id,
        message=body.message,
        opportunity_id=body.opportunity_id,
        context=body.context,
    )
    audit_service.record(
        db,
        actor_id=user.id,
        action="talent.outreach.created",
        resource_type="outreach_request",
        resource_id=request.id,
        organization_id=organization_id,
        metadata={
            "person_id": str(body.person_id),
            "opportunity_id": str(body.opportunity_id) if body.opportunity_id else None,
        },
    )
    # Notify the candidate through their feed (never by email/phone).
    candidate_user_id = _candidate_user_id(db, request.person_id)
    if candidate_user_id:
        org_name = _org_name(db, organization_id)
        notifications_service.notify(
            db,
            candidate_user_id,
            "A company would like to contact you",
            f"{org_name} sent you an outreach request about "
            f"{_opportunity_title(db, request.opportunity_id) or 'an opportunity'}.",
            kind="outreach",
        )
        events_service.emit(
            db,
            event_type="outreach.created",
            resource_type="outreach_request",
            resource_id=request.id,
            recipient_user_id=candidate_user_id,
            actor_user_id=user.id,
            organization_id=organization_id,
            payload={
                "opportunity_id": (
                    str(request.opportunity_id) if request.opportunity_id else None
                ),
                "organization_id": str(organization_id),
            },
        )
    db.commit()
    return outreach_service.outreach_company_out(db, request)


def _org_name(db: Session, organization_id) -> Optional[str]:
    org = db.get(Organization, organization_id)
    return org.name if org else None


@router.get("/{organization_id}/outreach", response_model=list[OutreachCompanyOut])
def list_outreach(
    organization_id: uuid.UUID,
    status: Optional[str] = Query(None, max_length=20),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list:
    require_org_permission(db, user, PERMISSION_OUTREACH_READ, organization_id)
    return outreach_service.list_org_outreach(db, organization_id, status=status)


@router.get("/{organization_id}/outreach/{request_id}",
            response_model=OutreachCompanyOut)
def get_outreach(
    organization_id: uuid.UUID,
    request_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    require_org_permission(db, user, PERMISSION_OUTREACH_READ, organization_id)
    return outreach_service.get_org_outreach(db, organization_id, request_id)


@router.post("/{organization_id}/outreach/{request_id}/cancel", response_model=dict)
def cancel_outreach(
    organization_id: uuid.UUID,
    request_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Cancel a live request (requester, or anyone with outreach.manage)."""
    require_org_permission(db, user, PERMISSION_OUTREACH_CREATE, organization_id)
    request = outreach_service.cancel_outreach(
        db, organization_id, request_id, user.id
    )
    audit_service.record(
        db,
        actor_id=user.id,
        action="talent.outreach.cancelled",
        resource_type="outreach_request",
        resource_id=request.id,
        organization_id=organization_id,
    )
    db.commit()
    return {"id": str(request.id), "status": request.status}


@router.get("/{organization_id}/communications",
            response_model=list[ConversationOut])
def list_communications(
    organization_id: uuid.UUID,
    status: Optional[str] = Query(None, max_length=20),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list:
    require_org_permission(db, user, PERMISSION_COMMUNICATIONS_READ, organization_id)
    return communications_service.list_org_conversations(
        db, organization_id, user.id, status=status
    )


@router.post("/{organization_id}/communications", response_model=ConversationOut,
             status_code=201)
def open_application_conversation(
    organization_id: uuid.UUID,
    body: OpenConversationRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Open a controlled conversation from an existing application (idempotent
    per application: the same thread keeps interview/offer context attached)."""
    require_org_permission(db, user, PERMISSION_COMMUNICATIONS_SEND, organization_id)
    from app.models.career import Opportunity
    from app.services.company_os import _application_owned

    app = _application_owned(db, organization_id, body.application_id, actor_id=user.id)
    # Reuse an existing thread for this application when one exists.
    existing = db.scalar(
        select(Conversation).where(Conversation.application_id == app.id).limit(1)
    )
    if existing is not None:
        return communications_service.conversation_out(db, existing, user.id)

    opp = db.get(Opportunity, app.opportunity_id)
    conversation = communications_service.create_conversation(
        db,
        organization_id=organization_id,
        person_id=app.person_id,
        actor_id=user.id,
        opportunity_id=opp.id if opp else None,
        application_id=app.id,
    )
    audit_service.record(
        db,
        actor_id=user.id,
        action="communications.conversation.opened",
        resource_type="conversation",
        resource_id=conversation.id,
        organization_id=organization_id,
        metadata={"application_id": str(app.id)},
    )
    db.commit()
    candidate_user_id = _candidate_user_id(db, app.person_id)
    if candidate_user_id:
        notifications_service.notify(
            db,
            candidate_user_id,
            "A conversation has been opened about your application",
            f"{_org_name(db, organization_id)} can now discuss your application "
            "with you through AskTrabaajo.",
            kind="communication",
        )
        events_service.emit(
            db,
            event_type="conversation.opened",
            resource_type="conversation",
            resource_id=conversation.id,
            recipient_user_id=candidate_user_id,
            actor_user_id=user.id,
            organization_id=organization_id,
            payload={"application_id": str(app.id)},
        )
    db.commit()
    return communications_service.conversation_out(db, conversation, user.id)


@router.get("/{organization_id}/communications/{conversation_id}",
            response_model=ConversationOut)
def get_conversation(
    organization_id: uuid.UUID,
    conversation_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    require_org_permission(db, user, PERMISSION_COMMUNICATIONS_READ, organization_id)
    payload = communications_service.get_org_conversation(
        db, organization_id, conversation_id, user.id
    )
    audit_service.record(
        db,
        actor_id=user.id,
        action="communications.conversation.viewed",
        resource_type="conversation",
        resource_id=conversation_id,
        organization_id=organization_id,
    )
    db.commit()
    return payload


@router.post("/{organization_id}/communications/{conversation_id}/messages",
             response_model=MessageOut, status_code=201)
def send_org_message(
    organization_id: uuid.UUID,
    conversation_id: uuid.UUID,
    body: MessageSend,
    user: User = Depends(get_current_user),
    _rl: None = Depends(message_send_limit),
    db: Session = Depends(get_db),
) -> dict:
    require_org_permission(db, user, PERMISSION_COMMUNICATIONS_SEND, organization_id)
    from app.services.communications import _org_owns

    conversation = _org_owns(db, organization_id, conversation_id, user.id)
    message = communications_service.send_message(
        db, conversation, user.id, sender_side="recruiter", body=body.body
    )
    audit_service.record(
        db,
        actor_id=user.id,
        action="communications.message.sent",
        resource_type="conversation_message",
        resource_id=message.id,
        organization_id=organization_id,
        metadata={"conversation_id": str(conversation_id)},
    )
    candidate_user_id = _candidate_user_id(db, conversation.person_id)
    if candidate_user_id:
        notifications_service.notify(
            db,
            candidate_user_id,
            "New message from a company",
            f"{_org_name(db, organization_id)} sent you a message in AskTrabaajo.",
            kind="communication",
        )
        # Realtime event: minimal metadata, NEVER the message body.
        events_service.emit(
            db,
            event_type="message.sent",
            resource_type="conversation_message",
            resource_id=message.id,
            recipient_user_id=candidate_user_id,
            actor_user_id=user.id,
            organization_id=organization_id,
            payload={"conversation_id": str(conversation_id), "sender_side": "recruiter"},
        )
    db.commit()
    return communications_service._message_out(db, message)


@router.post("/{organization_id}/communications/{conversation_id}/read",
             response_model=dict)
def mark_conversation_read(
    organization_id: uuid.UUID,
    conversation_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    require_org_permission(db, user, PERMISSION_COMMUNICATIONS_READ, organization_id)
    from app.services.communications import _org_owns

    conversation = _org_owns(db, organization_id, conversation_id, user.id)
    communications_service.mark_conversation_read(db, conversation, user.id)
    return {"conversation_id": str(conversation_id), "ok": True}


@router.post("/{organization_id}/communications/{conversation_id}/close",
             response_model=ConversationOut)
def close_conversation(
    organization_id: uuid.UUID,
    conversation_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    require_org_permission(db, user, PERMISSION_COMMUNICATIONS_MANAGE, organization_id)
    from app.services.communications import _org_owns

    conversation = _org_owns(db, organization_id, conversation_id, user.id)
    closed = communications_service.close_conversation(db, conversation, user.id)
    audit_service.record(
        db,
        actor_id=user.id,
        action="communications.conversation.closed",
        resource_type="conversation",
        resource_id=conversation_id,
        organization_id=organization_id,
    )
    db.commit()
    return communications_service.conversation_out(db, closed, user.id)
