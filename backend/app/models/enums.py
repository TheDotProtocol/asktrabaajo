"""Canonical value constants (stored as strings for portability)."""
from __future__ import annotations

# --- User lifecycle -----------------------------------------------------------
USER_STATUS_ACTIVE = "active"
USER_STATUS_SUSPENDED = "suspended"
USER_STATUS_PENDING_VERIFICATION = "pending_verification"
USER_STATUSES = {
    USER_STATUS_ACTIVE,
    USER_STATUS_SUSPENDED,
    USER_STATUS_PENDING_VERIFICATION,
}

# --- Organization kinds -------------------------------------------------------
ORG_KIND_EMPLOYER = "employer"
ORG_KIND_RECRUITER = "recruiter"
ORG_KIND_GOVERNMENT = "government"
ORG_KIND_PLATFORM = "platform"
ORG_KINDS = {ORG_KIND_EMPLOYER, ORG_KIND_RECRUITER, ORG_KIND_GOVERNMENT, ORG_KIND_PLATFORM}

ORG_STATUS_ACTIVE = "active"
ORG_STATUS_SUSPENDED = "suspended"
ORG_STATUSES = {ORG_STATUS_ACTIVE, ORG_STATUS_SUSPENDED}

# --- Credential / document verification states --------------------------------
CREDENTIAL_STATUS_UNVERIFIED = "unverified"
CREDENTIAL_STATUS_PENDING = "pending"
CREDENTIAL_STATUS_VERIFIED = "verified"
CREDENTIAL_STATUS_EXPIRED = "expired"
CREDENTIAL_STATUS_REVOKED = "revoked"
CREDENTIAL_STATUSES = {
    CREDENTIAL_STATUS_UNVERIFIED,
    CREDENTIAL_STATUS_PENDING,
    CREDENTIAL_STATUS_VERIFIED,
    CREDENTIAL_STATUS_EXPIRED,
    CREDENTIAL_STATUS_REVOKED,
}

# --- Employment types ---------------------------------------------------------
EMPLOYMENT_TYPES = {
    "full_time",
    "part_time",
    "contract",
    "freelance",
    "internship",
}

# --- Audit results ------------------------------------------------------------
AUDIT_RESULT_SUCCESS = "success"
AUDIT_RESULT_FAILURE = "failure"
AUDIT_RESULT_DENIED = "denied"
