"""/api/v1/auth — register, login, refresh, logout, me, password lifecycle,
sessions, email verification, MFA foundation."""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.errors import AppError, UnauthorizedError
from app.core.ratelimit import rate_limit_dependency
from app.core.security import (
    create_mfa_token,
    decode_mfa_token,
    hash_token,
)
from app.db.session import get_db
from app.models.identity import RefreshToken, User
from app.models.tenancy import Membership, Organization
from app.schemas.auth import (
    ChangePasswordRequest,
    EmailVerificationMessage,
    ForgotPasswordRequest,
    LoginRequest,
    LoginResult,
    LogoutRequest,
    MeResponse,
    MembershipBrief,
    MfaCodeRequest,
    MfaEnableResponse,
    MfaLoginRequest,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    SessionOut,
    TokenPair,
    VerifyEmailRequest,
)
from app.schemas.common import MessageResponse, PersonSummary
from app.services import audit as audit_service
from app.services import auth_service, authz, email as email_service, mfa as mfa_service
from app.services.auth_service import (
    authenticate,
    change_password,
    get_person_for_user,
    issue_token_pair,
    list_active_sessions,
    refresh_access_token,
    register_user,
    request_email_verification,
    request_password_reset,
    reset_password,
    revoke_all_user_tokens,
    revoke_refresh_token,
    verify_email_with_token,
)

router = APIRouter(prefix="/auth", tags=["auth"])

login_limit = rate_limit_dependency("login", max_requests=10)
verify_limit = rate_limit_dependency("mfa_verify", max_requests=5)
reset_limit = rate_limit_dependency("reset", max_requests=5)


def _token_pair(access: str, refresh: str) -> TokenPair:
    return TokenPair(
        access_token=access,
        refresh_token=refresh,
        expires_in_seconds=get_settings().access_token_minutes * 60,
    )


def _login_result(access: str, refresh: str) -> LoginResult:
    return LoginResult(
        mfa_required=False,
        access_token=access,
        refresh_token=refresh,
        expires_in_seconds=get_settings().access_token_minutes * 60,
    )


def _audit(db: Session, actor_id: Optional[uuid.UUID], action: str,
           resource_id=None, result: str = "success", meta=None) -> None:
    audit_service.record(
        db,
        actor_id=actor_id,
        action=action,
        resource_type="user",
        resource_id=resource_id or actor_id,
        result=result,
        metadata=meta,
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
        mfa_enabled=user.mfa_enabled,
        person=PersonSummary.model_validate(person) if person else None,
        memberships=briefs,
        permissions=permissions,
        super_admin=authz.is_platform_super_admin(db, user.id),
    )


# --- registration / login ----------------------------------------------------


@router.post("/register", response_model=TokenPair, status_code=201)
def register(body: RegisterRequest, db: Session = Depends(get_db)) -> TokenPair:
    user = register_user(
        db, email=str(body.email), password=body.password, full_name=body.full_name
    )
    _audit(db, user.id, "auth.register")
    access, refresh = issue_token_pair(db, user)
    db.commit()
    return _token_pair(access, refresh)


@router.post("/login", response_model=LoginResult, dependencies=[Depends(login_limit)])
def login(body: LoginRequest, db: Session = Depends(get_db)) -> LoginResult:
    user = authenticate(db, email=str(body.email), password=body.password)

    if user.mfa_enabled and user.mfa_secret:
        mfa_token = create_mfa_token(user.id)
        _audit(db, user.id, "auth.login.mfa_pending")
        db.commit()
        return LoginResult(mfa_required=True, mfa_token=mfa_token)

    access, refresh = issue_token_pair(db, user)
    _audit(db, user.id, "auth.login")
    db.commit()
    return _login_result(access, refresh)


@router.post(
    "/mfa/verify",
    response_model=TokenPair,
    dependencies=[Depends(verify_limit)],
)
def mfa_verify(body: MfaLoginRequest, db: Session = Depends(get_db)) -> TokenPair:
    user_id = decode_mfa_token(body.mfa_token)
    user = db.get(User, user_id)
    if user is None or not user.mfa_enabled or not user.mfa_secret:
        raise UnauthorizedError("MFA is not enabled for this account.")

    if not mfa_service.verify_code(user.mfa_secret, body.code):
        _audit(db, user.id, "auth.mfa.verify_failed", result="failure")
        db.commit()
        raise AppError(
            "Invalid authentication code.", code="invalid_code", status_code=400
        )

    access, refresh = issue_token_pair(db, user)
    _audit(db, user.id, "auth.login")
    db.commit()
    return _token_pair(access, refresh)


@router.post("/refresh", response_model=TokenPair)
def refresh(body: RefreshRequest, db: Session = Depends(get_db)) -> TokenPair:
    access, refresh, user = refresh_access_token(db, body.refresh_token)
    _audit(db, user.id, "auth.refresh")
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
        _audit(db, row.user_id, "auth.logout")
        db.commit()
    return MessageResponse(message="Logged out.")


@router.get("/me", response_model=MeResponse)
def me(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> MeResponse:
    return _build_me(db, user)


# --- password lifecycle ------------------------------------------------------


@router.post("/change-password", response_model=TokenPair)
def change_pw(
    body: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TokenPair:
    access, refresh = change_password(
        db, user=user, current_password=body.current_password,
        new_password=body.new_password,
    )
    _audit(db, user.id, "auth.password_changed")
    db.commit()
    return _token_pair(access, refresh)


@router.post("/forgot-password", response_model=MessageResponse,
             dependencies=[Depends(reset_limit)])
def forgot_password(
    body: ForgotPasswordRequest, db: Session = Depends(get_db)
) -> MessageResponse:
    """Always returns the same message — never reveals account existence."""
    token = request_password_reset(db, email=str(body.email))
    if token is not None:
        user = db.scalar(
            select(User).where(User.email == str(body.email).strip().lower())
        )
        email_service.send(
            str(body.email),
            "Reset your AskTrabaajo password",
            f"Your password reset code is:\n{token}\n\n"
            "It expires in 60 minutes and can be used once.",
        )
        if user is not None:
            _audit(db, user.id, "auth.password_reset_requested")
            db.commit()
    return MessageResponse(
        message="If an account exists for this email, a reset link has been sent."
    )


@router.post("/reset-password", response_model=MessageResponse,
             dependencies=[Depends(reset_limit)])
def reset_pw(body: ResetPasswordRequest, db: Session = Depends(get_db)) -> MessageResponse:
    user = reset_password(db, token=body.token, new_password=body.new_password)
    _audit(db, user.id, "auth.password_reset")
    db.commit()
    return MessageResponse(message="Password reset. You can now log in.")


# --- email verification ------------------------------------------------------


@router.post("/verify-email/send", response_model=MessageResponse)
def send_email_verification(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> MessageResponse:
    if user.email_verified_at is not None:
        return MessageResponse(message="Email is already verified.")
    token = request_email_verification(db, user=user)
    email_service.send(
        user.email,
        "Verify your AskTrabaajo email",
        f"Your email verification code is:\n{token}\n\n"
        "It expires in 24 hours and can be used once.",
    )
    _audit(db, user.id, "auth.email_verification_requested")
    db.commit()
    return MessageResponse(message="Verification email sent.")


@router.post("/verify-email", response_model=EmailVerificationMessage,
             dependencies=[Depends(verify_limit)])
def verify_email(body: VerifyEmailRequest, db: Session = Depends(get_db)) -> EmailVerificationMessage:
    user = verify_email_with_token(db, token=body.token)
    _audit(db, user.id, "auth.email_verified")
    db.commit()
    return EmailVerificationMessage(
        message="Email verified.", email_verified=True
    )


# --- sessions ----------------------------------------------------------------


@router.get("/sessions", response_model=list)
def list_sessions(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list:
    rows = list_active_sessions(db, user.id)
    return [
        SessionOut(
            id=row.id,
            created_at=row.created_at,
            expires_at=row.expires_at,
            ip_address=row.ip_address,
            user_agent=row.user_agent,
        ).model_dump(mode="json")
        for row in rows
    ]


@router.post("/sessions/revoke-all", response_model=MessageResponse)
def revoke_all_sessions(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> MessageResponse:
    revoke_all_user_tokens(db, user.id)
    _audit(db, user.id, "auth.sessions_revoked_all")
    db.commit()
    return MessageResponse(message="All sessions revoked. Please log in again.")


# --- MFA foundation ----------------------------------------------------------


@router.post("/mfa/enable", response_model=MfaEnableResponse)
def mfa_enable(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> MfaEnableResponse:
    if not user.mfa_secret:
        user.mfa_secret = mfa_service.generate_secret()
        user.mfa_enabled = False
        db.commit()
    assert user.mfa_secret
    return MfaEnableResponse(
        secret=user.mfa_secret,
        otpauth_uri=mfa_service.provisioning_uri(user.mfa_secret, user.email),
        confirmed=user.mfa_enabled,
    )


@router.post("/mfa/confirm", response_model=MfaEnableResponse)
def mfa_confirm(
    body: MfaCodeRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MfaEnableResponse:
    if not user.mfa_secret:
        raise UnauthorizedError("Enable MFA first to receive a secret.")
    if not mfa_service.verify_code(user.mfa_secret, body.code):
        raise AppError(
            "Invalid authentication code.", code="invalid_code", status_code=400
        )
    user.mfa_enabled = True
    db.commit()
    _audit(db, user.id, "auth.mfa_enabled")
    db.commit()
    return MfaEnableResponse(
        secret=user.mfa_secret,
        otpauth_uri=mfa_service.provisioning_uri(user.mfa_secret, user.email),
        confirmed=True,
    )


@router.post("/mfa/disable", response_model=MessageResponse,
             dependencies=[Depends(verify_limit)])
def mfa_disable(
    body: MfaCodeRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    if not user.mfa_enabled or not user.mfa_secret:
        raise UnauthorizedError("MFA is not enabled.")
    if not mfa_service.verify_code(user.mfa_secret, body.code):
        raise AppError(
            "Invalid authentication code.", code="invalid_code", status_code=400
        )
    user.mfa_secret = None
    user.mfa_enabled = False
    db.commit()
    _audit(db, user.id, "auth.mfa_disabled")
    db.commit()
    return MessageResponse(message="MFA disabled.")
