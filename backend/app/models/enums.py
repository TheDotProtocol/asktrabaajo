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

# --- Education levels ---------------------------------------------------------
EDUCATION_LEVELS = {
    "school",
    "higher_secondary",
    "diploma",
    "vocational",
    "undergraduate",
    "postgraduate",
    "professional_qualification",
}

# --- Default verification state for self-reported records ---------------------
VERIFICATION_UNVERIFIED = "unverified"
VERIFICATION_PENDING = "pending"
VERIFICATION_VERIFIED = "verified"

# --- Privacy / visibility -----------------------------------------------------
VISIBILITY_PRIVATE = "private"
VISIBILITY_PUBLIC = "public"
VISIBILITY_AUTHORIZED_ONLY = "authorized_only"
VISIBILITY_LEVELS = {
    VISIBILITY_PRIVATE,
    VISIBILITY_PUBLIC,
    VISIBILITY_AUTHORIZED_ONLY,
}

# Work ID sections whose visibility a person may control.
VISIBILITY_SCOPES = {
    "profile",
    "contact",
    "education",
    "experience",
    "employment",
    "skills",
    "credentials",
    "documents",
}

# Consent resource scopes (who may access WHAT). Extended per workflow later.
CONSENT_SCOPE_WORK_ID_DOCUMENTS = "work_id:documents"
CONSENT_SCOPE_WORK_ID_CREDENTIALS = "work_id:credentials"
CONSENT_SCOPE_WORK_ID_PROFILE = "work_id:profile"
CONSENT_SCOPE_APPLICATION = "application"
CONSENT_SCOPES = {
    CONSENT_SCOPE_WORK_ID_DOCUMENTS,
    CONSENT_SCOPE_WORK_ID_CREDENTIALS,
    CONSENT_SCOPE_WORK_ID_PROFILE,
    CONSENT_SCOPE_APPLICATION,
}

# --- Audit results ------------------------------------------------------------
AUDIT_RESULT_SUCCESS = "success"
AUDIT_RESULT_FAILURE = "failure"
AUDIT_RESULT_DENIED = "denied"
