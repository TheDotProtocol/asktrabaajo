"""MFA foundation — RFC 6238 TOTP implemented with the standard library.

No third-party dependency is introduced (clean foundation, no new packages).
The same verification routine is used by the API and the tests, so tests
exercise real application logic.

Production considerations (later phases):
- shared secrets are stored in the users table; encryption at rest lands
  with the credential-protection work (P4/P8 roadmap)
- enforcement per role (company/government/admin) is a Phase-5 concern
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import struct
import time
from typing import Optional

MFA_ISSUER = "AskTrabaajo"
MFA_STEP_SECONDS = 30
MFA_DIGITS = 6
MFA_VERIFY_WINDOW = 1  # ±1 step tolerance for clock drift


def generate_secret() -> str:
    """20 random bytes → base32 (160-bit secrets, per RFC 4226)."""
    return base64.b32encode(os.urandom(20)).decode("ascii").rstrip("=")


def _hotp(secret_b32: str, counter: int) -> str:
    key = base64.b32decode(secret_b32 + "=" * ((8 - len(secret_b32) % 8) % 8))
    digest = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    binary = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    return str(binary % (10 ** MFA_DIGITS)).zfill(MFA_DIGITS)


def current_code(secret_b32: str, at: Optional[int] = None) -> str:
    """The current TOTP code for a secret (used by tests + enable flows)."""
    step = int(time.time() // MFA_STEP_SECONDS) if at is None else at
    return _hotp(secret_b32, step)


def verify_code(secret_b32: str, code: str, window: int = MFA_VERIFY_WINDOW) -> bool:
    """Constant-time-ish check with ±window step tolerance."""
    if not code or not secret_b32:
        return False
    code = code.strip()
    if len(code) != MFA_DIGITS or not code.isdigit():
        return False
    step = int(time.time() // MFA_STEP_SECONDS)
    for offset in range(-window, window + 1):
        expected = _hotp(secret_b32, step + offset)
        if hmac.compare_digest(expected, code):
            return True
    return False


def provisioning_uri(secret_b32: str, email: str) -> str:
    label = email.replace(":", "")
    return (
        f"otpauth://totp/{MFA_ISSUER}:{label}?secret={secret_b32}"
        f"&issuer={MFA_ISSUER}&algorithm=SHA1&digits={MFA_DIGITS}&period={MFA_STEP_SECONDS}"
    )
