"""/api/v1/auth — register, login, refresh, logout, me."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_token
from app.db.session import get_db
from app.models.identity import RefreshToken, User
from app.models.tenancy import Membership, Organization
from app.schemas.auth import (
    LoginRequest,
    LogoutRequest,
    MeResponse,
    MembershipBrief,
    RefreshRequest,
    RegisterRequest,
    TokenPair,
)
from app.schemas.common import MessageResponse, PersonSummary
from app.api.deps import get_current_user
from app.services import audit as audit_service
from app.services import auth_service, authz
from app.services.auth_service import (
    authenticate,
    get_person_for_user,
    issue_token_pair,
    refresh_access_token,
    register_user,
    revoke_refresh_token,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _token_pair(access: str, refresh: str) -> TokenPair:
    return TokenPair(
        access_token=access,
        refresh_token=refresh,
        expires_in_seconds=get_settings().access_token_minutes * 60,
    )


def _build_me(db: Session, user: User) -> MeResponse:
    person = get_person_for_user(db, user.id)
    memberships = db.execute(
        select(Membership, Organization)
        .join(Organization, Organization.id == Membership.organization_id)
        .where(Membership.user_id == user.id)
    ).all()

    briefs = [
        MembershipBrief(
            organization_id=org.id,
            organization_name=org.name,
            organization_slug=org.slug,
            organization_kind=org.kind,
            role=m.role_code,
        )
        for m, org in memberships
    ]
    permissions = sorted(authz.effective_permission_codes(db, user.id))
    return MeResponse(
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        status=user.status,
        email_verified=user.email_verified_at is not None,
        person=PersonSummary.model_validate(person) if person else None,
        memberships=briefs,
        permissions=permissions,
        super_admin=authz.is_platform_super_admin(db, user.id),
    )


@router.post("/register", response_model=TokenPair, status_code=201)
def register(body: RegisterRequest, db: Session = Depends(get_db)) -> TokenPair:
    user = register_user(
        db, email=str(body.email), password=body.password, full_name=body.full_name
    )
    audit_service.record(
        db,
        actor_id=user.id,
        action="auth.register",
        resource_type="user",
        resource_id=user.id,
    )
    access, refresh = issue_token_pair(db, user)
    db.commit()
    return _token_pair(access, refresh)


@router.post("/login", response_model=TokenPair)
def login(body: LoginRequest, db: Session = Depends(get_db)) -> TokenPair:
    user = authenticate(db, email=str(body.email), password=body.password)
    access, refresh = issue_token_pair(db, user)
    db.commit()
    audit_service.record(
        db,
        actor_id=user.id,
        action="auth.login",
        resource_type="user",
        resource_id=user.id,
    )
    db.commit()
    return _token_pair(access, refresh)


@router.post("/refresh", response_model=TokenPair)
def refresh(body: RefreshRequest, db: Session = Depends(get_db)) -> TokenPair:
    access, refresh, user = refresh_access_token(db, body.refresh_token)
    audit_service.record(
        db,
        actor_id=user.id,
        action="auth.refresh",
        resource_type="user",
        resource_id=user.id,
    )
    db.commit()
    return _token_pair(access, refresh)


@router.post("/logout", response_model=MessageResponse)
def logout(body: LogoutRequest, db: Session = Depends(get_db)) -> MessageResponse:
    token_hash = hash_token(body.refresh_token)
    row = db.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    revoke_refresh_token(db, body.refresh_token)
    if row is not None:
        audit_service.record(
            db,
            actor_id=row.user_id,
            action="auth.logout",
            resource_type="user",
            resource_id=row.user_id,
        )
        db.commit()
    return MessageResponse(message="Logged out.")


@router.get("/me", response_model=MeResponse)
def me(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> MeResponse:
    return _build_me(db, user)
