"""Tenancy service: organization creation + membership management."""
from __future__ import annotations

import re
import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import (
    ConflictError,
    InvalidInputError,
    NotFoundError,
    PermissionDeniedError,
)
from app.models.catalog import role_scope_allows_org_kind
from app.models.enums import ORG_KINDS, ORG_KIND_PLATFORM
from app.models.tenancy import Membership, Organization, Role

ORG_ROLES = {"org_admin", "hr", "recruiter", "hiring_manager"}
GOVERNMENT_ROLES = {"government_admin", "government_user"}


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "org"


def create_organization(
    db: Session,
    *,
    actor_id: uuid.UUID,
    name: str,
    kind: str,
    slug: Optional[str] = None,
) -> Organization:
    """Create an organization and make the actor its org_admin.

    Platform-kind organizations may only be created by platform super admins
    (checked in the API layer before calling this).
    """
    if kind not in ORG_KINDS:
        raise InvalidInputError(f"kind must be one of {sorted(ORG_KINDS)}.")
    if kind in {ORG_KIND_PLATFORM, "government"}:
        # Platform and government organizations are provisioned only by
        # platform administrators — never by self-service.
        from app.services.authz import is_platform_super_admin

        if not is_platform_super_admin(db, actor_id):
            raise PermissionDeniedError(
                "Only platform administrators can create this type of organization."
            )

    base_slug = slug or slugify(name)
    candidate = base_slug
    counter = 1
    while db.scalar(select(Organization).where(Organization.slug == candidate)):
        counter += 1
        candidate = f"{base_slug}-{counter}"

    org = Organization(name=name.strip(), slug=candidate, kind=kind, created_by=actor_id)
    db.add(org)
    db.flush()

    admin_role = "org_admin" if kind in {"employer", "recruiter"} else "government_admin"
    db.add(
        Membership(
            user_id=actor_id,
            organization_id=org.id,
            role_code=admin_role,
            created_by=actor_id,
        )
    )
    db.commit()
    db.refresh(org)
    return org


def validate_role_for_org(db: Session, role_code: str, kind: str) -> Role:
    role = db.get(Role, role_code)
    if role is None:
        raise InvalidInputError(f"Unknown role '{role_code}'.")
    if not role_scope_allows_org_kind(role.scope, kind):
        raise InvalidInputError(
            f"Role '{role_code}' cannot be granted inside a '{kind}' organization."
        )
    return role


def add_membership(
    db: Session,
    *,
    organization: Organization,
    user_id: uuid.UUID,
    role_code: str,
    actor_id: uuid.UUID,
) -> Membership:
    """Grant ``role_code`` to a user inside an organization (idempotent upsert)."""
    validate_role_for_org(db, role_code, organization.kind)

    existing = db.scalar(
        select(Membership).where(
            Membership.organization_id == organization.id,
            Membership.user_id == user_id,
        )
    )
    if existing is not None:
        raise ConflictError("User is already a member of this organization.")

    membership = Membership(
        organization_id=organization.id,
        user_id=user_id,
        role_code=role_code,
        created_by=actor_id,
    )
    db.add(membership)
    db.commit()
    db.refresh(membership)
    return membership


def update_membership_role(
    db: Session,
    *,
    organization: Organization,
    membership: Membership,
    role_code: str,
    actor_id: uuid.UUID,
) -> Membership:
    validate_role_for_org(db, role_code, organization.kind)
    membership.role_code = role_code
    membership.created_by = actor_id
    db.commit()
    db.refresh(membership)
    return membership


def remove_membership(db: Session, *, membership: Membership) -> None:
    db.delete(membership)
    db.commit()


def get_organization(db: Session, organization_id: uuid.UUID) -> Organization:
    org = db.get(Organization, organization_id)
    if org is None:
        raise NotFoundError("Organization not found.")
    return org
