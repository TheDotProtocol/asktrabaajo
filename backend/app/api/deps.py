"""FastAPI dependencies: current user + permission enforcement."""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core import context
from app.core.config import get_settings
from app.core.errors import UnauthorizedError
from app.core.security import decode_access_token
from app.db.session import get_db, set_session_identity
from app.models.enums import (
    USER_STATUS_ACTIVE,
    USER_STATUS_PENDING_VERIFICATION,
    USER_STATUS_SUSPENDED,
)
from app.models.identity import User
from app.models.tenancy import Membership
from app.services import authz

_bearer = HTTPBearer(auto_error=False)


def _resolve_token_user(
    credentials: Optional[HTTPAuthorizationCredentials],
    db: Session,
    *,
    allow_suspended: bool,
) -> User:
    if credentials is None or not credentials.credentials:
        raise UnauthorizedError("Authentication required.")

    payload = decode_access_token(credentials.credentials)
    try:
        user_id = uuid.UUID(str(payload.get("sub")))
    except (ValueError, TypeError):
        raise UnauthorizedError("Invalid access token.")

    user = db.get(User, user_id)
    if user is None:
        raise UnauthorizedError("Account is not active.")
    # Lazy enforcement reconciliation: a suspension whose window lapsed (no
    # scheduler ran) releases the identity gate on the next authenticated
    # request; a just-opened window suspends the target immediately.
    if user.status == USER_STATUS_SUSPENDED:
        from app.services import enforcement as enforcement_service

        before = user.status
        enforcement_service.reconcile_user(db, user)
        if before != user.status:
            db.commit()
    # Suspended identities keep a LIMITED session: the default dependency
    # rejects them everywhere; only appeal surfaces opt into suspended
    # access. Pending-verification accounts are never admitted.
    if user.status == USER_STATUS_PENDING_VERIFICATION:
        raise UnauthorizedError("Account is not active.")
    if user.status != USER_STATUS_ACTIVE and not allow_suspended:
        raise UnauthorizedError("Account is not active.")

    if user.token_version != int(payload.get("token_version", -1)):
        raise UnauthorizedError("Access token has been revoked.")

    # PostgreSQL RLS session identity (Phase 13): stamp the request's DB
    # session with the canonical actor so database-level policies see the
    # same identity the application authorized. Reset happens in get_db's
    # finally; values are never client-supplied.
    if get_settings().rls_session_context and db.bind is not None and (
        db.bind.dialect.name == "postgresql"
    ):
        org_ids = [
            m.organization_id
            for m in db.query(Membership)
            .filter(Membership.user_id == user.id)
            .all()
        ]
        set_session_identity(db, user.id, org_ids)

    meta = context.get_request_context()
    meta["actor_id"] = str(user.id)
    context.set_request_context(meta)
    return user


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    """Resolve the authenticated user from a Bearer access token.

    Default gate: suspended identities are rejected (product surface).
    """
    return _resolve_token_user(credentials, db, allow_suspended=False)


def get_suspended_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    """Limited-access dependency for the enforcement appeal surface.

    Used ONLY by appeal submission/withdrawal/self-view and the caller's own
    derived platform state. Every other route keeps the default hard gate.
    """
    return _resolve_token_user(credentials, db, allow_suspended=True)


def require_org_permission(
    db: Session, user: User, permission_code: str, organization_id: uuid.UUID
) -> None:
    """Authorization = membership + role + permission + tenant scope."""
    authz.require_permission(db, user.id, permission_code, organization_id)


def require_super_admin(db: Session, user: User) -> None:
    """Platform-level SUPER_ADMIN only — company roles never satisfy this."""
    authz.require_permission(db, user.id, "admin.manage")
    if not authz.is_platform_super_admin(db, user.id):
        from app.core.errors import PermissionDeniedError

        raise PermissionDeniedError("Platform administrator privileges required.")


def current_user_id(user: User) -> uuid.UUID:
    return user.id
