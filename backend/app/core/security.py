"""Security primitives: password hashing and JWT access tokens.

Deliberately small. Refresh tokens are opaque random values hashed at rest
(see ``app/services/auth_service``); access tokens are short-lived JWTs.
"""
from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import bcrypt
import jwt

from app.core.config import get_settings
from app.core.errors import UnauthorizedError

TOKEN_TYPE_ACCESS = "access"


def hash_password(password: str) -> str:
    """Hash a password with bcrypt (12 rounds default)."""
    if not password or len(password) < 8:
        raise ValueError("Password must be at least 8 characters long.")
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode(
        "utf-8"
    )


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(
            password.encode("utf-8"), password_hash.encode("utf-8")
        )
    except ValueError:
        return False


def generate_random_token() -> str:
    """Opaque high-entropy token (refresh tokens, verification tokens)."""
    return secrets.token_urlsafe(48)


def hash_token(token: str) -> str:
    """Deterministic hash for storing opaque tokens at rest."""
    import hashlib

    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_access_token(user_id: uuid.UUID, token_version: int) -> str:
    """Create a short-lived JWT access token."""
    settings = get_settings()
    expires = _now() + timedelta(minutes=settings.access_token_minutes)
    payload: Dict[str, Any] = {
        "sub": str(user_id),
        "type": TOKEN_TYPE_ACCESS,
        "token_version": token_version,
        "jti": uuid.uuid4().hex,
        "iat": _now(),
        "exp": expires,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> Dict[str, Any]:
    """Decode + validate an access token. Raises UnauthorizedError when bad."""
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm],
            options={"require": ["sub", "type", "exp", "token_version"]},
        )
    except jwt.ExpiredSignatureError:
        raise UnauthorizedError("Access token has expired.")
    except jwt.PyJWTError:
        raise UnauthorizedError("Invalid access token.")
    if payload.get("type") != TOKEN_TYPE_ACCESS:
        raise UnauthorizedError("Invalid token type.")
    return payload


def new_request_id() -> str:
    return uuid.uuid4().hex
