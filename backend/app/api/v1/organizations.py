"""/api/v1/organizations — tenancy + membership management.

Company HR/recruiter memberships can never reach platform-level privileges:
platform and government organizations are provisioned only by platform
super admins, and role scope is validated against organization kind.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_org_permission, require_super_admin
from app.core.errors import InvalidInputError, NotFoundError, PermissionDeniedError
from app.db.session import get_db
from app.models.identity import User
from app.models.tenancy import Membership, Organization
from app.schemas.common import MessageResponse
from app.schemas.tenancy import (
    MemberAddRequest,
    MemberListResponse,
    MemberOut,
    MemberUpdateRequest,
    OrganizationCreate,
    OrganizationOut,
)
from app.services import audit as audit_service
from app.services import authz, tenancy

router = APIRouter(prefix="/organizations", tags=["organizations"])


def _member_out(row: Membership) -> MemberOut:
    user = row._user  # populated by helper below
    return MemberOut(
        user_id=row.user_id,
        email=user.email,
        full_name=user.full_name,
        role=row.role_code,
        created_at=row.created_at,
    )


@router.post("", response_model=OrganizationOut, status_code=201)
def create_org(
    body: OrganizationCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Organization:
    if body.kind in {"platform", "government"}:
        require_super_admin(db, user)
    org = tenancy.create_organization(
        db, actor_id=user.id, name=body.name, slug=body.slug, kind=body.kind
    )
    audit_service.record(
        db,
        actor_id=user.id,
        action="organization.created",
        resource_type="organization",
        resource_id=org.id,
        organization_id=org.id,
        metadata={"kind": org.kind, "name": org.name},
    )
    db.commit()
    return org


@router.get("", response_model=list)
def list_my_organizations(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list:
    rows = db.execute(
        select(Membership, Organization)
        .join(Organization, Organization.id == Membership.organization_id)
        .where(Membership.user_id == user.id)
        .order_by(Organization.name)
    ).all()
    return [
        {
            "organization_id": str(org.id),
            "name": org.name,
            "slug": org.slug,
            "kind": org.kind,
            "status": org.status,
            "role": m.role_code,
        }
        for m, org in rows
    ]


@router.get("/{organization_id}", response_model=OrganizationOut)
def get_organization(
    organization_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Organization:
    authz.require_membership(db, user.id, organization_id)
    return tenancy.get_organization(db, organization_id)


@router.post("/{organization_id}/members", response_model=MemberOut, status_code=201)
def add_member(
    organization_id: uuid.UUID,
    body: MemberAddRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MemberOut:
    require_org_permission(db, user, "members.manage", organization_id)
    org = tenancy.get_organization(db, organization_id)
    target = db.scalar(
        select(User).where(func.lower(User.email) == str(body.user_email).lower())
    )
    if target is None:
        raise NotFoundError("No account found for this email.")
    membership = tenancy.add_membership(
        db,
        organization=org,
        user_id=target.id,
        role_code=body.role,
        actor_id=user.id,
    )
    audit_service.record(
        db,
        actor_id=user.id,
        action="organization.membership.added",
        resource_type="membership",
        resource_id=membership.id,
        organization_id=org.id,
        metadata={"target_user_id": str(target.id), "role": body.role},
    )
    db.commit()
    membership._user = target
    return _member_out(membership)


@router.get("/{organization_id}/members", response_model=MemberListResponse)
def list_members(
    organization_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MemberListResponse:
    require_org_permission(db, user, "members.read", organization_id)
    memberships = db.execute(
        select(Membership)
        .where(Membership.organization_id == organization_id)
        .order_by(Membership.created_at)
    ).scalars().all()

    user_ids = [m.user_id for m in memberships]
    users = {
        u.id: u
        for u in db.execute(select(User).where(User.id.in_(user_ids))).scalars()
    }
    members = []
    for m in memberships:
        m._user = users[m.user_id]
        members.append(_member_out(m))
    return MemberListResponse(organization_id=organization_id, members=members)


@router.patch("/{organization_id}/members/{member_user_id}", response_model=MemberOut)
def update_member_role(
    organization_id: uuid.UUID,
    member_user_id: uuid.UUID,
    body: MemberUpdateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MemberOut:
    require_org_permission(db, user, "members.manage", organization_id)
    org = tenancy.get_organization(db, organization_id)
    membership = authz.get_org_membership(db, member_user_id, organization_id)
    if membership is None:
        raise NotFoundError("User is not a member of this organization.")
    _guard_last_admin(db, org, membership, new_role=body.role)

    old_role = membership.role_code
    tenancy.update_membership_role(
        db,
        organization=org,
        membership=membership,
        role_code=body.role,
        actor_id=user.id,
    )
    audit_service.record(
        db,
        actor_id=user.id,
        action="organization.membership.role_changed",
        resource_type="membership",
        resource_id=membership.id,
        organization_id=org.id,
        metadata={
            "target_user_id": str(member_user_id),
            "from_role": old_role,
            "to_role": body.role,
        },
    )
    db.commit()
    target_user = db.get(User, member_user_id)
    membership._user = target_user
    return _member_out(membership)


@router.delete("/{organization_id}/members/{member_user_id}", response_model=MessageResponse)
def remove_member(
    organization_id: uuid.UUID,
    member_user_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    require_org_permission(db, user, "members.manage", organization_id)
    org = tenancy.get_organization(db, organization_id)
    membership = authz.get_org_membership(db, member_user_id, organization_id)
    if membership is None:
        raise NotFoundError("User is not a member of this organization.")
    _guard_last_admin(db, org, membership)

    tenancy.remove_membership(db, membership=membership)
    audit_service.record(
        db,
        actor_id=user.id,
        action="organization.membership.removed",
        resource_type="membership",
        resource_id=membership.id,
        organization_id=org.id,
        metadata={"target_user_id": str(member_user_id)},
    )
    db.commit()
    return MessageResponse(message="Member removed.")


def _guard_last_admin(
    db: Session,
    org: Organization,
    membership: Membership,
    new_role: str | None = None,
) -> None:
    """Never leave an organization without an org_admin.

    Applies when the changed/removed membership currently holds org_admin
    and would no longer do so, and no other org_admin remains.
    """
    would_lose_admin = membership.role_code == "org_admin" and new_role != "org_admin"
    if not would_lose_admin:
        return
    other_admins = db.scalar(
        select(func.count(Membership.id)).where(
            Membership.organization_id == org.id,
            Membership.role_code == "org_admin",
            Membership.id != membership.id,
        )
    )
    if (other_admins or 0) == 0:
        raise InvalidInputError(
            "Cannot remove the last organization admin. Promote another member first."
        )
