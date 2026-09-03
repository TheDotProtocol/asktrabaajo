"""Authorization core.

Authorization = USER + MEMBERSHIP + ORGANIZATION + ROLE + PERMISSION + RESOURCE.

Checks are implemented here once and used by every route through
``app.api.deps``. SUPER_ADMIN is a platform-scope role reachable only via a
membership in a platform-kind organization — company roles can never
elevate to it.
"""
from __future__ import annotations

import uuid
from typing import Optional, Set

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import PermissionDeniedError
from app.models.tenancy import (
    ROLE_SUPER_ADMIN,
    Membership,
    Organization,
    Role,
    RolePermission,
)

ROLE_SCOPE_PLATFORM = "platform"


def get_org_membership(
    db: Session, user_id: uuid.UUID, organization_id: uuid.UUID
) -> Optional[Membership]:
    return db.scalar(
        select(Membership).where(
            Membership.user_id == user_id,
            Membership.organization_id == organization_id,
        )
    )


def is_platform_super_admin(db: Session, user_id: uuid.UUID) -> bool:
    """True only when the user holds super_admin inside a platform org."""
    row = db.execute(
        select(Membership.id)
        .join(Organization, Organization.id == Membership.organization_id)
        .where(
            Membership.user_id == user_id,
            Membership.role_code == ROLE_SUPER_ADMIN,
            Organization.kind == "platform",
        )
        .limit(1)
    ).first()
    return row is not None


def permission_codes_for_org(
    db: Session, user_id: uuid.UUID, organization_id: uuid.UUID
) -> Set[str]:
    """Permissions a user holds through their membership in one org."""
    rows = db.execute(
        select(RolePermission.permission_code)
        .join(Membership, Membership.role_code == RolePermission.role_code)
        .where(
            Membership.user_id == user_id,
            Membership.organization_id == organization_id,
        )
    ).all()
    return {r[0] for r in rows}


def effective_permission_codes(db: Session, user_id: uuid.UUID) -> Set[str]:
    """Union of all permissions across the user's memberships."""
    rows = db.execute(
        select(RolePermission.permission_code)
        .join(Membership, Membership.role_code == RolePermission.role_code)
        .where(Membership.user_id == user_id)
    ).all()
    codes = {r[0] for r in rows}
    if is_platform_super_admin(db, user_id):
        codes.add("admin.manage")
    return codes


def has_permission(
    db: Session,
    user_id: uuid.UUID,
    permission_code: str,
    organization_id: Optional[uuid.UUID] = None,
) -> bool:
    """Does the user hold ``permission_code``?

    - When ``organization_id`` is given, only memberships in that
      organization count (plus platform super admin, who is global).
    - Otherwise the union of all memberships counts.
    """
    if is_platform_super_admin(db, user_id):
        return True

    if organization_id is not None:
        membership = get_org_membership(db, user_id, organization_id)
        if membership is None:
            return False
        # A membership alone does not imply org-scope permissions unless the
        # role is an organization-scope role.
        role = db.get(Role, membership.role_code)
        if role is None:
            return False
        return permission_code in permission_codes_for_org(db, user_id, organization_id)

    return permission_code in effective_permission_codes(db, user_id)


def require_permission(
    db: Session,
    user_id: uuid.UUID,
    permission_code: str,
    organization_id: Optional[uuid.UUID] = None,
) -> None:
    """Raise PermissionDeniedError unless the user holds the permission."""
    if not has_permission(db, user_id, permission_code, organization_id):
        scope = f"organization={organization_id} " if organization_id else ""
        raise PermissionDeniedError(
            f"Missing permission '{permission_code}' ({scope}scope).",
            details={"permission": permission_code},
        )


def require_membership(
    db: Session, user_id: uuid.UUID, organization_id: uuid.UUID
) -> Membership:
    """Return the user's membership or raise 403 (existence hidden → 403)."""
    membership = get_org_membership(db, user_id, organization_id)
    if membership is None:
        raise PermissionDeniedError("You are not a member of this organization.")
    return membership


def has_platform_permission(db: Session, user_id: uuid.UUID, permission_code: str) -> bool:
    """True when the user holds ``permission_code`` through a membership in a
    PLATFORM-kind organization (moderator, governance auditor, super admin).
    Company/government memberships can never satisfy platform governance
    permissions — this is the Phase 9 governance boundary."""
    if is_platform_super_admin(db, user_id):
        return True
    if permission_code not in effective_permission_codes(db, user_id):
        return False
    row = db.execute(
        select(Membership.id)
        .join(Organization, Organization.id == Membership.organization_id)
        .where(
            Membership.user_id == user_id,
            Organization.kind == "platform",
        )
        .limit(1)
    ).first()
    return row is not None


def require_platform_permission(
    db: Session, user_id: uuid.UUID, permission_code: str
) -> None:
    """Raise 403 unless the user holds a platform-scope permission."""
    if not has_platform_permission(db, user_id, permission_code):
        raise PermissionDeniedError(
            f"Missing platform permission '{permission_code}'.",
            details={"permission": permission_code},
        )
