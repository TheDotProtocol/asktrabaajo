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

# --- Application lifecycle (jobseeker-owned, status machine) ------------------
APPLICATION_STATUS_DISCOVERED = "discovered"
APPLICATION_STATUS_SAVED = "saved"
APPLICATION_STATUS_APPLIED = "applied"
APPLICATION_STATUS_APPLICATION_RECEIVED = "application_received"
APPLICATION_STATUS_SCREENING = "screening"
APPLICATION_STATUS_ASSESSMENT = "assessment"
APPLICATION_STATUS_INTERVIEW = "interview"
APPLICATION_STATUS_OFFER = "offer"
APPLICATION_STATUS_ACCEPTED = "accepted"
APPLICATION_STATUS_REJECTED = "rejected"
APPLICATION_STATUS_WITHDRAWN = "withdrawn"
APPLICATION_STATUS_ON_HOLD = "on_hold"

# The person may move through this lifecycle themselves; later employer-driven
# transitions (screening -> interview -> offer) will be written by the company
# pipeline through the same state machine with permission checks.
APPLICATION_STATUSES = {
    APPLICATION_STATUS_DISCOVERED,
    APPLICATION_STATUS_SAVED,
    APPLICATION_STATUS_APPLIED,
    APPLICATION_STATUS_APPLICATION_RECEIVED,
    APPLICATION_STATUS_SCREENING,
    APPLICATION_STATUS_ASSESSMENT,
    APPLICATION_STATUS_INTERVIEW,
    APPLICATION_STATUS_OFFER,
    APPLICATION_STATUS_ACCEPTED,
    APPLICATION_STATUS_REJECTED,
    APPLICATION_STATUS_WITHDRAWN,
    APPLICATION_STATUS_ON_HOLD,
}

# Statuses reachable by the jobseeker through the self-service API. The
# employer side (Phase 6+) advances screening/assessment/interview/offer
# through authorized membership permissions, never by raw status writes.
APPLICATION_STATUS_USER_ACTIONS = {
    "apply": {
        "from": {APPLICATION_STATUS_SAVED, APPLICATION_STATUS_DISCOVERED},
        "to": APPLICATION_STATUS_APPLIED,
    },
    "withdraw": {
        "from": {APPLICATION_STATUS_APPLIED, APPLICATION_STATUS_APPLICATION_RECEIVED,
                 APPLICATION_STATUS_SCREENING, APPLICATION_STATUS_ON_HOLD},
        "to": APPLICATION_STATUS_WITHDRAWN,
    },
}

# --- Offer lifecycle -----------------------------------------------------------
# Employer side: draft -> sent. Candidate side: pending -> accepted/declined.
# The candidate's Offer Center treats pending/sent as "actionable".
OFFER_STATUS_DRAFT = "draft"
OFFER_STATUS_SENT = "sent"
OFFER_STATUS_PENDING = "pending"
OFFER_STATUS_VIEWED = "viewed"
OFFER_STATUS_ACCEPTED = "accepted"
OFFER_STATUS_DECLINED = "declined"
OFFER_STATUS_EXPIRED = "expired"
OFFER_STATUS_WITHDRAWN = "withdrawn"
OFFER_STATUSES = {
    OFFER_STATUS_DRAFT,
    OFFER_STATUS_SENT,
    OFFER_STATUS_PENDING,
    OFFER_STATUS_VIEWED,
    OFFER_STATUS_ACCEPTED,
    OFFER_STATUS_DECLINED,
    OFFER_STATUS_EXPIRED,
    OFFER_STATUS_WITHDRAWN,
}

# Statuses a candidate may respond to through the jobseeker Offer Center.
OFFER_CANDIDATE_DECIDABLE = {OFFER_STATUS_SENT, OFFER_STATUS_PENDING}

# --- Interview scheduling ------------------------------------------------------
INTERVIEW_STATUS_SCHEDULED = "scheduled"
INTERVIEW_STATUS_COMPLETED = "completed"
INTERVIEW_STATUS_CANCELLED = "cancelled"
INTERVIEW_STATUS_RESCHEDULE_REQUESTED = "reschedule_requested"
INTERVIEW_STATUSES = {
    INTERVIEW_STATUS_SCHEDULED,
    INTERVIEW_STATUS_COMPLETED,
    INTERVIEW_STATUS_CANCELLED,
    INTERVIEW_STATUS_RESCHEDULE_REQUESTED,
}

INTERVIEW_MODES = {"video", "phone", "onsite", "async"}

# --- Opportunity sources -------------------------------------------------------
OPPORTUNITY_SOURCE_PLATFORM = "platform"
OPPORTUNITY_SOURCE_COMPAT = "careers_compat"
OPPORTUNITY_SOURCE_EXTERNAL = "external"
OPPORTUNITY_SOURCES = {
    OPPORTUNITY_SOURCE_PLATFORM,
    OPPORTUNITY_SOURCE_COMPAT,
    OPPORTUNITY_SOURCE_EXTERNAL,
}

# --- Notification kinds --------------------------------------------------------
NOTIFICATION_KIND_APPLICATION = "application"
NOTIFICATION_KIND_INTERVIEW = "interview"
NOTIFICATION_KIND_OFFER = "offer"
NOTIFICATION_KIND_DOCUMENT = "document"
NOTIFICATION_KIND_CAREER = "career"
NOTIFICATION_KIND_SYSTEM = "system"
NOTIFICATION_KIND_OUTREACH = "outreach"
NOTIFICATION_KIND_COMMUNICATION = "communication"
NOTIFICATION_KINDS = {
    NOTIFICATION_KIND_APPLICATION,
    NOTIFICATION_KIND_INTERVIEW,
    NOTIFICATION_KIND_OFFER,
    NOTIFICATION_KIND_DOCUMENT,
    NOTIFICATION_KIND_CAREER,
    NOTIFICATION_KIND_SYSTEM,
    NOTIFICATION_KIND_OUTREACH,
    NOTIFICATION_KIND_COMMUNICATION,
}

# --- Job posting lifecycle (company-owned) -----------------------------------
JOB_STATUS_DRAFT = "draft"
JOB_STATUS_PENDING_REVIEW = "pending_review"
JOB_STATUS_PUBLISHED = "published"
JOB_STATUS_PAUSED = "paused"
JOB_STATUS_CLOSED = "closed"
JOB_STATUS_ARCHIVED = "archived"
JOB_STATUSES = {
    JOB_STATUS_DRAFT,
    JOB_STATUS_PENDING_REVIEW,
    JOB_STATUS_PUBLISHED,
    JOB_STATUS_PAUSED,
    JOB_STATUS_CLOSED,
    JOB_STATUS_ARCHIVED,
}

# Company org kinds eligible to own jobs/opportunities.
HIRING_ORG_KINDS = {"employer", "recruiter"}

# Organization verification states.
ORG_VERIFICATION_UNVERIFIED = "unverified"
ORG_VERIFICATION_PENDING = "pending"
ORG_VERIFICATION_VERIFIED = "verified"
ORG_VERIFICATION_STATUSES = {
    ORG_VERIFICATION_UNVERIFIED,
    ORG_VERIFICATION_PENDING,
    ORG_VERIFICATION_VERIFIED,
}

# --- Document requests (employer -> candidate) --------------------------------
DOC_REQUEST_STATUS_PENDING = "pending"
DOC_REQUEST_STATUS_APPROVED = "approved"
DOC_REQUEST_STATUS_DECLINED = "declined"
DOC_REQUEST_STATUS_EXPIRED = "expired"
DOC_REQUEST_STATUSES = {
    DOC_REQUEST_STATUS_PENDING,
    DOC_REQUEST_STATUS_APPROVED,
    DOC_REQUEST_STATUS_DECLINED,
    DOC_REQUEST_STATUS_EXPIRED,
}

# --- Interview scorecard recommendation ---------------------------------------
SCORECARD_RECOMMEND_ADVANCE = "advance"
SCORECARD_RECOMMEND_HOLD = "hold"
SCORECARD_RECOMMEND_REJECT = "reject"
SCORECARD_RECOMMENDATIONS = {
    SCORECARD_RECOMMEND_ADVANCE,
    SCORECARD_RECOMMEND_HOLD,
    SCORECARD_RECOMMEND_REJECT,
}

# --- Skill taxonomy (Phase 7) ---------------------------------------------------
SKILL_STATUS_ACTIVE = "active"
SKILL_STATUS_DEPRECATED = "deprecated"
SKILL_STATUSES = {SKILL_STATUS_ACTIVE, SKILL_STATUS_DEPRECATED}

# How one skill relates to another in the taxonomy graph.
SKILL_RELATION_PARENT = "parent"          # target is a broader category
SKILL_RELATION_CHILD = "child"            # target is a specialization
SKILL_RELATION_RELATED = "related"
SKILL_RELATION_COMPLEMENTARY = "complementary"
SKILL_RELATION_SIMILAR = "similar"
SKILL_RELATION_KINDS = {
    SKILL_RELATION_PARENT,
    SKILL_RELATION_CHILD,
    SKILL_RELATION_RELATED,
    SKILL_RELATION_COMPLEMENTARY,
    SKILL_RELATION_SIMILAR,
}

# Where a person's claim to a skill originates (provenance, never inferred
# as verified).
SKILL_EVIDENCE_SELF = "self"
SKILL_EVIDENCE_EXPERIENCE = "experience"
SKILL_EVIDENCE_EMPLOYMENT = "employment"
SKILL_EVIDENCE_EDUCATION = "education"
SKILL_EVIDENCE_CERTIFICATION = "certification"
SKILL_EVIDENCE_ASSESSMENT = "assessment"
SKILL_EVIDENCE_TYPES = {
    SKILL_EVIDENCE_SELF,
    SKILL_EVIDENCE_EXPERIENCE,
    SKILL_EVIDENCE_EMPLOYMENT,
    SKILL_EVIDENCE_EDUCATION,
    SKILL_EVIDENCE_CERTIFICATION,
    SKILL_EVIDENCE_ASSESSMENT,
}

# Opportunity requirement kind (normalized from employer/job text).
REQUIREMENT_KIND_REQUIRED = "required"
REQUIREMENT_KIND_PREFERRED = "preferred"
REQUIREMENT_KINDS = {REQUIREMENT_KIND_REQUIRED, REQUIREMENT_KIND_PREFERRED}

# Career-path catalogue states.
CAREER_PATH_ACTIVE = "active"
CAREER_PATH_ARCHIVED = "archived"
CAREER_PATH_STATUSES = {CAREER_PATH_ACTIVE, CAREER_PATH_ARCHIVED}

# Candidate discovery is organisation-scoped but pools are searchable only by
# members holding the talent permissions below.
PERMISSION_CANDIDATES_SEARCH = "candidates.search"
PERMISSION_POOLS_MANAGE = "pools.manage"

# --- Talent outreach (Phase 8) --------------------------------------------------
# A recruiter/company requests contact with a candidate; the candidate stays in
# control. Only an ACCEPTED request opens a controlled AskTrabaajo conversation.
OUTREACH_STATUS_SENT = "sent"
OUTREACH_STATUS_VIEWED = "viewed"
OUTREACH_STATUS_ACCEPTED = "accepted"
OUTREACH_STATUS_DECLINED = "declined"
OUTREACH_STATUS_EXPIRED = "expired"
OUTREACH_STATUS_CANCELLED = "cancelled"
OUTREACH_STATUS_BLOCKED = "blocked"
OUTREACH_STATUSES = {
    OUTREACH_STATUS_SENT,
    OUTREACH_STATUS_VIEWED,
    OUTREACH_STATUS_ACCEPTED,
    OUTREACH_STATUS_DECLINED,
    OUTREACH_STATUS_EXPIRED,
    OUTREACH_STATUS_CANCELLED,
    OUTREACH_STATUS_BLOCKED,
}
# Statuses the candidate may still respond to.
OUTREACH_ACTIONABLE = {OUTREACH_STATUS_SENT, OUTREACH_STATUS_VIEWED}
# Statuses a company may still cancel.
OUTREACH_CANCELLABLE = {OUTREACH_STATUS_SENT, OUTREACH_STATUS_VIEWED}

# --- Controlled communication channel (Phase 8) ---------------------------------
CONVERSATION_STATUS_ACTIVE = "active"
CONVERSATION_STATUS_CLOSED = "closed"
CONVERSATION_STATUSES = {CONVERSATION_STATUS_ACTIVE, CONVERSATION_STATUS_CLOSED}
# Which side of an AskTrabaajo conversation authored a message.
MESSAGE_SIDE_CANDIDATE = "candidate"
MESSAGE_SIDE_RECRUITER = "recruiter"
MESSAGE_SIDES = {MESSAGE_SIDE_CANDIDATE, MESSAGE_SIDE_RECRUITER}

# Phase 8 permission codes (also seeded in catalog + migration 0006).
PERMISSION_OUTREACH_CREATE = "talent.outreach.create"
PERMISSION_OUTREACH_READ = "talent.outreach.read"
PERMISSION_OUTREACH_MANAGE = "talent.outreach.manage"
PERMISSION_COMMUNICATIONS_READ = "communications.read"
PERMISSION_COMMUNICATIONS_SEND = "communications.send"
PERMISSION_COMMUNICATIONS_MANAGE = "communications.manage"

# --- Platform governance (Phase 9) ---------------------------------------------
REPORT_CATEGORY_ABUSE = "abuse"
REPORT_CATEGORY_HARASSMENT = "harassment"
REPORT_CATEGORY_FRAUD = "fraud"
REPORT_CATEGORY_IMPERSONATION = "impersonation"
REPORT_CATEGORY_POLICY_VIOLATION = "policy_violation"
REPORT_CATEGORY_COMMUNICATION_DISPUTE = "communication_dispute"
REPORT_CATEGORY_DOCUMENT_MISUSE = "document_misuse"
REPORT_CATEGORY_RECRUITER_MISCONDUCT = "recruiter_misconduct"
REPORT_CATEGORY_SUSPICIOUS_ACTIVITY = "suspicious_activity"
REPORT_CATEGORY_PLATFORM_INTEGRITY = "platform_integrity"
REPORT_CATEGORY_OTHER = "other"
REPORT_CATEGORIES = {
    REPORT_CATEGORY_ABUSE,
    REPORT_CATEGORY_HARASSMENT,
    REPORT_CATEGORY_FRAUD,
    REPORT_CATEGORY_IMPERSONATION,
    REPORT_CATEGORY_POLICY_VIOLATION,
    REPORT_CATEGORY_COMMUNICATION_DISPUTE,
    REPORT_CATEGORY_DOCUMENT_MISUSE,
    REPORT_CATEGORY_RECRUITER_MISCONDUCT,
    REPORT_CATEGORY_SUSPICIOUS_ACTIVITY,
    REPORT_CATEGORY_PLATFORM_INTEGRITY,
    REPORT_CATEGORY_OTHER,
}
REPORT_SEVERITY_LOW = "low"
REPORT_SEVERITY_MEDIUM = "medium"
REPORT_SEVERITY_HIGH = "high"
REPORT_SEVERITY_CRITICAL = "critical"
REPORT_SEVERITIES = {
    REPORT_SEVERITY_LOW,
    REPORT_SEVERITY_MEDIUM,
    REPORT_SEVERITY_HIGH,
    REPORT_SEVERITY_CRITICAL,
}
REPORT_STATUS_OPEN = "open"
REPORT_STATUS_IN_REVIEW = "in_review"
REPORT_STATUS_ASSIGNED = "assigned"
REPORT_STATUS_RESOLVED = "resolved"
REPORT_STATUS_CLOSED = "closed"
REPORT_STATUSES = {
    REPORT_STATUS_OPEN,
    REPORT_STATUS_IN_REVIEW,
    REPORT_STATUS_ASSIGNED,
    REPORT_STATUS_RESOLVED,
    REPORT_STATUS_CLOSED,
}
# Report target kinds that may be referenced (references only, never dumps).
REPORT_TARGET_TYPES = {
    "user",
    "organization",
    "opportunity",
    "job_application",
    "outreach_request",
    "conversation",
    "message",
    "document_request",
    "person_profile",
}

# --- Realtime event types (Phase 9) --------------------------------------------
EVENT_TYPES = {
    "outreach.created",
    "outreach.accepted",
    "outreach.declined",
    "outreach.blocked",
    "outreach.expired",
    "conversation.opened",
    "message.sent",
    "message.read",
    "application.updated",
    "interview.updated",
    "offer.updated",
    "report.created",
}

# --- Notification channels (Phase 9) -------------------------------------------
NOTIFICATION_CHANNEL_IN_APP = "in_app"
NOTIFICATION_CHANNEL_EMAIL = "email"
NOTIFICATION_CHANNEL_PUSH = "push"
NOTIFICATION_CHANNEL_SMS = "sms"
NOTIFICATION_CHANNELS = {
    NOTIFICATION_CHANNEL_IN_APP,
    NOTIFICATION_CHANNEL_EMAIL,
    NOTIFICATION_CHANNEL_PUSH,
    NOTIFICATION_CHANNEL_SMS,
}

# Phase 9 permission codes (also seeded in catalog + migration 0007).
PERMISSION_REPORTS_READ = "reports.read"
PERMISSION_REPORTS_MANAGE = "reports.manage"
PERMISSION_REPORTS_ASSIGN = "reports.assign"
PERMISSION_REPORTS_RESOLVE = "reports.resolve"
PERMISSION_REPORTS_AUDIT = "reports.audit"
PERMISSION_MODERATION_READ = "moderation.read"
PERMISSION_MODERATION_MANAGE = "moderation.manage"
PERMISSION_PLATFORM_AUDIT_READ = "platform.audit.read"

# Explainable match modes (never a bare percentage).
MATCH_MODE_STRONG = "strong"
MATCH_MODE_POTENTIAL = "potential"
MATCH_MODE_CAREER_TRANSITION = "career_transition"
MATCH_MODE_EXPLORE = "explore"
MATCH_MODES = {
    MATCH_MODE_STRONG,
    MATCH_MODE_POTENTIAL,
    MATCH_MODE_CAREER_TRANSITION,
    MATCH_MODE_EXPLORE,
}
