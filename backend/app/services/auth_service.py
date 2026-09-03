"""Authentication service: register, login, token issuance + refresh rotation.

Refresh tokens are opaque random strings stored hashed in
``refresh_tokens``. Rotation revokes the presented token and issues a new
pair; presenting an already-revoked token is treated as theft and revokes
every active token for the user.
"""
from __future__ import annotations

import uuid
from datetime import timedelta
from typing import Optional, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import context
from app.core.config import get_settings
from app.core.timeutil import utc_now_naive
from app.core.errors import (
    ConflictError,
    NotFoundError,
    UnauthorizedError,
)
from app.core.security import (
    create_access_token,
    generate_random_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.models.enums import USER_STATUS_ACTIVE
from app.models.identity import PersonProfile, RefreshToken, User


def _now():
    return utc_now_naive()


def register_user(
    db: Session, *, email: str, password: str, full_name: str
) -> User:
    """Create an account + its person profile. Raises ConflictError on dupes."""
    normalized = email.strip().lower()
    existing = db.scalar(select(User).where(User.email == normalized))
    if existing is not None:
        raise ConflictError("An account with this email already exists.")

    user = User(
        email=normalized,
        password_hash=hash_password(password),
        full_name=full_name.strip(),
        status=USER_STATUS_ACTIVE,
    )
    db.add(user)
    db.flush()
    db.add(PersonProfile(user_id=user.id))
    db.commit()
    db.refresh(user)
    return user


def authenticate(db: Session, *, email: str, password: str) -> User:
    """Verify credentials. Never reveals whether the email exists."""
    user = db.scalar(select(User).where(User.email == email.strip().lower()))
    if user is None or not verify_password(password, user.password_hash):
        raise UnauthorizedError("Invalid email or password.")
    if user.status != USER_STATUS_ACTIVE:
        raise UnauthorizedError("This account is not active.")
    return user


def _issue_refresh_token(db: Session, user: User) -> str:
    settings = get_settings()
    plain = generate_random_token()
    meta = context.request_meta()
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_token(plain),
            expires_at=_now() + timedelta(days=settings.refresh_token_days),
            user_agent=meta.get("user_agent"),
            ip_address=meta.get("ip_address"),
        )
    )
    db.flush()
    return plain


def issue_token_pair(db: Session, user: User) -> Tuple[str, str]:
    """Issue (access_token, refresh_token). Caller commits."""
    access = create_access_token(user.id, user.token_version)
    refresh = _issue_refresh_token(db, user)
    return access, refresh


def refresh_access_token(
    db: Session, refresh_token: str
) -> Tuple[str, str, User]:
    """Rotate a refresh token → new (access, refresh) pair.

    Raises UnauthorizedError on missing/expired tokens and revokes the whole
    user's token family when a revoked token is replayed.
    """
    token_hash = hash_token(refresh_token)
    row = db.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    if row is None:
        raise UnauthorizedError("Invalid refresh token.")

    if row.revoked_at is not None:
        # Reuse of a rotated token → likely theft. Kill all sessions.
        db.execute(
            RefreshToken.__table__.update()
            .where(RefreshToken.user_id == row.user_id)
            .where(RefreshToken.revoked_at.is_(None))
            .values(revoked_at=_now())
        )
        db.commit()
        raise UnauthorizedError("Refresh token reuse detected; all sessions revoked.")

    if row.expires_at < _now():
        raise UnauthorizedError("Refresh token has expired.")

    user = db.get(User, row.user_id)
    if user is None or user.status != USER_STATUS_ACTIVE:
        raise UnauthorizedError("Account is not active.")

    row.revoked_at = _now()
    access = create_access_token(user.id, user.token_version)
    refresh = _issue_refresh_token(db, user)
    db.commit()
    return access, refresh, user


def revoke_refresh_token(db: Session, refresh_token: str) -> None:
    """Revoke a single refresh token (logout)."""
    row = db.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == hash_token(refresh_token))
    )
    if row is not None and row.revoked_at is None:
        row.revoked_at = _now()
        db.commit()


def revoke_all_user_tokens(db: Session, user_id: uuid.UUID) -> None:
    db.execute(
        RefreshToken.__table__.update()
        .where(RefreshToken.user_id == user_id)
        .where(RefreshToken.revoked_at.is_(None))
        .values(revoked_at=_now())
    )
    db.commit()


def bump_token_version(db: Session, user: User) -> None:
    """Invalidate every outstanding access token for a user."""
    user.token_version += 1
    db.commit()


def get_user_by_id(db: Session, user_id: uuid.UUID) -> Optional[User]:
    return db.get(User, user_id)


def get_person_for_user(db: Session, user_id: uuid.UUID) -> Optional[PersonProfile]:
    return db.scalar(select(PersonProfile).where(PersonProfile.user_id == user_id))


def ensure_person(db: Session, user_id: uuid.UUID) -> PersonProfile:
    person = get_person_for_user(db, user_id)
    if person is None:
        raise NotFoundError("Person profile not found for account.")
    return person
