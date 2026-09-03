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
from app.db.session import get_db
from app.models.enums import PERMISSION_CANDIDATES_SEARCH, PERMISSION_POOLS_MANAGE
from app.models.identity import PersonProfile, User
from app.models.work import Skill
from app.schemas.common import MessageResponse
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
from app.services import skills_registry
from app.services import talent as talent_service

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
