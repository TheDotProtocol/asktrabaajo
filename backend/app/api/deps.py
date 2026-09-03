"""FastAPI dependencies: current user + permission enforcement."""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core import context
from app.core.errors import UnauthorizedError
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.enums import USER_STATUS_ACTIVE
from app.models.identity import User
from app.services import authz

_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    """Resolve the authenticated user from a Bearer access token."""
    if credentials is None or not credentials.credentials:
        raise UnauthorizedError("Authentication required.")

    payload = decode_access_token(credentials.credentials)
    try:
        user_id = uuid.UUID(str(payload.get("sub")))
    except (ValueError, TypeError):
        raise UnauthorizedError("Invalid access token.")

    user = db.get(User, user_id)
    if user is None or user.status != USER_STATUS_ACTIVE:
        raise UnauthorizedError("Account is not active.")

    if user.token_version != int(payload.get("token_version", -1)):
        raise UnauthorizedError("Access token has been revoked.")

    meta = context.get_request_context()
    meta["actor_id"] = str(user.id)
    context.set_request_context(meta)
    return user


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
