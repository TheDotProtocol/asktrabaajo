"""Canonical value constants (stored as strings for portability)."""
from __future__ import annotations

# --- Enforcement + appeals (Phase 11) ------------------------------------------
# Action types — granular, never a generic "admin action".
ENFORCEMENT_TYPE_WARNING = "warning"
ENFORCEMENT_TYPE_CONTENT_RESTRICTION = "content_restriction"
ENFORCEMENT_TYPE_COMMUNICATION_RESTRICTION = "communication_restriction"
ENFORCEMENT_TYPE_ACCOUNT_RESTRICTION = "account_restriction"
ENFORCEMENT_TYPE_ORGANIZATION_RESTRICTION = "organization_restriction"
ENFORCEMENT_TYPE_SUSPENSION = "suspension"
ENFORCEMENT_TYPE_REINSTATEMENT = "reinstatement"
ENFORCEMENT_TYPES = {
    ENFORCEMENT_TYPE_WARNING,
    ENFORCEMENT_TYPE_CONTENT_RESTRICTION,
    ENFORCEMENT_TYPE_COMMUNICATION_RESTRICTION,
    ENFORCEMENT_TYPE_ACCOUNT_RESTRICTION,
    ENFORCEMENT_TYPE_ORGANIZATION_RESTRICTION,
    ENFORCEMENT_TYPE_SUSPENSION,
    ENFORCEMENT_TYPE_REINSTATEMENT,
}
# Actions that always require an APPROVAL SEPARATION (creator != approver).
ENFORCEMENT_APPROVAL_REQUIRED_TYPES = {
    ENFORCEMENT_TYPE_ACCOUNT_RESTRICTION,
    ENFORCEMENT_TYPE_ORGANIZATION_RESTRICTION,
    ENFORCEMENT_TYPE_SUSPENSION,
    ENFORCEMENT_TYPE_REINSTATEMENT,
}
# Enforcement scopes — granular by design: a communication restriction never
# suspends the whole account, a company restriction never touches unrelated
# users, a user restriction is not an organization restriction.
ENFORCEMENT_SCOPE_ACCOUNT = "account"
ENFORCEMENT_SCOPE_COMMUNICATIONS = "communications"
ENFORCEMENT_SCOPE_APPLICATIONS = "applications"
ENFORCEMENT_SCOPE_COMPANY_ORGANIZATION = "company_organization"
ENFORCEMENT_SCOPE_GOVERNANCE_PARTICIPATION = "governance_participation"
ENFORCEMENT_SCOPE_PLATFORM_ACCESS = "platform_access"
ENFORCEMENT_SCOPES = {
    ENFORCEMENT_SCOPE_ACCOUNT,
    ENFORCEMENT_SCOPE_COMMUNICATIONS,
    ENFORCEMENT_SCOPE_APPLICATIONS,
    ENFORCEMENT_SCOPE_COMPANY_ORGANIZATION,
    ENFORCEMENT_SCOPE_GOVERNANCE_PARTICIPATION,
    ENFORCEMENT_SCOPE_PLATFORM_ACCESS,
}
# Enforcement lifecycle (deterministic; ACTIVE/EXPIRED derived from timestamps).
ENFORCEMENT_STATUS_PROPOSED = "proposed"
ENFORCEMENT_STATUS_APPROVED = "approved"
ENFORCEMENT_STATUS_ACTIVE = "active"
ENFORCEMENT_STATUS_EXPIRED = "expired"
ENFORCEMENT_STATUS_REJECTED = "rejected"
ENFORCEMENT_STATUS_REVOKED = "revoked"
ENFORCEMENT_STATUSES = {
    ENFORCEMENT_STATUS_PROPOSED,
    ENFORCEMENT_STATUS_APPROVED,
    ENFORCEMENT_STATUS_ACTIVE,
    ENFORCEMENT_STATUS_EXPIRED,
    ENFORCEMENT_STATUS_REJECTED,
    ENFORCEMENT_STATUS_REVOKED,
}
# Statuses stored on the row (the stored lifecycle transitions).
ENFORCEMENT_STORED_STATUSES = {
    ENFORCEMENT_STATUS_PROPOSED,
    ENFORCEMENT_STATUS_APPROVED,
    ENFORCEMENT_STATUS_ACTIVE,
    ENFORCEMENT_STATUS_REJECTED,
    ENFORCEMENT_STATUS_REVOKED,
}
# Controlled reason codes — free-form sensitive narratives never enter the
# audit/event payloads; a bounded sanitized note is allowed.
ENFORCEMENT_REASON_HARASSMENT = "harassment"
ENFORCEMENT_REASON_FRAUD = "fraud"
ENFORCEMENT_REASON_IMPERSONATION = "impersonation"
ENFORCEMENT_REASON_POLICY_VIOLATION = "policy_violation"
ENFORCEMENT_REASON_DOCUMENT_MISUSE = "document_misuse"
ENFORCEMENT_REASON_OUTREACH_ABUSE = "outreach_abuse"
ENFORCEMENT_REASON_COMMUNICATIONS_ABUSE = "communications_abuse"
ENFORCEMENT_REASON_SUSPICIOUS_ACTIVITY = "suspicious_activity"
ENFORCEMENT_REASON_REPEATED_VIOLATIONS = "repeated_violations"
ENFORCEMENT_REASON_OTHER = "other"
ENFORCEMENT_REASON_CODES = {
    ENFORCEMENT_REASON_HARASSMENT,
    ENFORCEMENT_REASON_FRAUD,
    ENFORCEMENT_REASON_IMPERSONATION,
    ENFORCEMENT_REASON_POLICY_VIOLATION,
    ENFORCEMENT_REASON_DOCUMENT_MISUSE,
    ENFORCEMENT_REASON_OUTREACH_ABUSE,
    ENFORCEMENT_REASON_COMMUNICATIONS_ABUSE,
    ENFORCEMENT_REASON_SUSPICIOUS_ACTIVITY,
    ENFORCEMENT_REASON_REPEATED_VIOLATIONS,
    ENFORCEMENT_REASON_OTHER,
}
# Derived platform states for a target (computed from ACTIVE actions).
PLATFORM_STATE_ACTIVE = "active"
PLATFORM_STATE_RESTRICTED = "restricted"
PLATFORM_STATE_SUSPENDED = "suspended"
PLATFORM_STATES = {
    PLATFORM_STATE_ACTIVE,
    PLATFORM_STATE_RESTRICTED,
    PLATFORM_STATE_SUSPENDED,
}
# Appeal lifecycle + decision codes.
APPEAL_STATUS_SUBMITTED = "submitted"
APPEAL_STATUS_ASSIGNED = "assigned"
APPEAL_STATUS_UNDER_REVIEW = "under_review"
APPEAL_STATUS_DECIDED = "decided"
APPEAL_STATUS_WITHDRAWN = "withdrawn"
APPEAL_STATUSES = {
    APPEAL_STATUS_SUBMITTED,
    APPEAL_STATUS_ASSIGNED,
    APPEAL_STATUS_UNDER_REVIEW,
    APPEAL_STATUS_DECIDED,
    APPEAL_STATUS_WITHDRAWN,
}
APPEAL_DECISION_ACCEPTED = "accepted"
APPEAL_DECISION_REJECTED = "rejected"
APPEAL_DECISION_PARTIALLY_GRANTED = "partially_granted"
APPEAL_DECISIONS = {
    APPEAL_DECISION_ACCEPTED,
    APPEAL_DECISION_REJECTED,
    APPEAL_DECISION_PARTIALLY_GRANTED,
}
# Appeal reason codes (controlled; statement is the appellant's sanitized text).
APPEAL_REASON_WRONG_TARGET = "wrong_target"
APPEAL_REASON_NO_VIOLATION = "no_violation"
APPEAL_REASON_EVIDENCE_NEW = "new_evidence"
APPEAL_REASON_CIRCUMSTANCES_CHANGED = "circumstances_changed"
APPEAL_REASON_OTHER = "other"
APPEAL_REASON_CODES = {
    APPEAL_REASON_WRONG_TARGET,
    APPEAL_REASON_NO_VIOLATION,
    APPEAL_REASON_EVIDENCE_NEW,
    APPEAL_REASON_CIRCUMSTANCES_CHANGED,
    APPEAL_REASON_OTHER,
}

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
NOTIFICATION_KIND_GOVERNANCE = "governance"
NOTIFICATION_KINDS = {
    NOTIFICATION_KIND_APPLICATION,
    NOTIFICATION_KIND_INTERVIEW,
    NOTIFICATION_KIND_OFFER,
    NOTIFICATION_KIND_DOCUMENT,
    NOTIFICATION_KIND_CAREER,
    NOTIFICATION_KIND_SYSTEM,
    NOTIFICATION_KIND_OUTREACH,
    NOTIFICATION_KIND_COMMUNICATION,
    NOTIFICATION_KIND_GOVERNANCE,
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
REPORT_STATUS_ESCALATED = "escalated"
REPORT_STATUS_RESOLVED = "resolved"
REPORT_STATUS_CLOSED = "closed"
REPORT_STATUSES = {
    REPORT_STATUS_OPEN,
    REPORT_STATUS_IN_REVIEW,
    REPORT_STATUS_ASSIGNED,
    REPORT_STATUS_ESCALATED,
    REPORT_STATUS_RESOLVED,
    REPORT_STATUS_CLOSED,
}
# Statuses that keep a case "open" (actionable) for the dashboard.
REPORT_OPEN_STATUSES = {
    REPORT_STATUS_OPEN,
    REPORT_STATUS_IN_REVIEW,
    REPORT_STATUS_ASSIGNED,
    REPORT_STATUS_ESCALATED,
}
# --- Operational priority (Phase 10) — separate from severity. --------------
# Severity describes the intrinsic seriousness of what happened; priority
# describes how urgently the platform must act. A fraudulent job may be
# severity=high, priority=urgent; a minor complaint severity=low, normal.
REPORT_PRIORITY_LOW = "low"
REPORT_PRIORITY_NORMAL = "normal"
REPORT_PRIORITY_HIGH = "high"
REPORT_PRIORITY_URGENT = "urgent"
REPORT_PRIORITY_CRITICAL = "critical"
REPORT_PRIORITIES = {
    REPORT_PRIORITY_LOW,
    REPORT_PRIORITY_NORMAL,
    REPORT_PRIORITY_HIGH,
    REPORT_PRIORITY_URGENT,
    REPORT_PRIORITY_CRITICAL,
}
# (response_hours, resolution_hours) per priority — deterministic SLA policy.
REPORT_SLA_HOURS: dict = {
    REPORT_PRIORITY_LOW: (72, 240),
    REPORT_PRIORITY_NORMAL: (24, 120),
    REPORT_PRIORITY_HIGH: (8, 48),
    REPORT_PRIORITY_URGENT: (4, 24),
    REPORT_PRIORITY_CRITICAL: (1, 8),
}
# SLA state values (deterministic, lazy — no scheduler).
SLA_STATE_ON_TRACK = "on_track"
SLA_STATE_DUE_SOON = "due_soon"
SLA_STATE_BREACHED = "breached"
SLA_STATES = {SLA_STATE_ON_TRACK, SLA_STATE_DUE_SOON, SLA_STATE_BREACHED}
# How close to a deadline counts as "due soon" (uniform, deterministic).
SLA_DUE_SOON_SECONDS = 2 * 3600
# Governance team slugs (Phase 10).
GOVERNANCE_TEAM_SLUGS = {
    "platform_safety",
    "fraud",
    "employer_integrity",
    "candidate_integrity",
    "communications",
    "document_trust",
    "technical_abuse",
    "general_support",
}
# Neutral integrity-signal statuses (Phase 10). Signals are never
# accusations; they only mark "review required".
SIGNAL_STATUS_REVIEW_REQUIRED = "review_required"
SIGNAL_STATUS_ACTIVITY_PATTERN = "activity_pattern"
SIGNAL_STATUS_POLICY_SIGNAL = "policy_signal"
SIGNAL_STATUS_INVESTIGATION_PENDING = "investigation_pending"
SIGNAL_STATUSES = {
    SIGNAL_STATUS_REVIEW_REQUIRED,
    SIGNAL_STATUS_ACTIVITY_PATTERN,
    SIGNAL_STATUS_POLICY_SIGNAL,
    SIGNAL_STATUS_INVESTIGATION_PENDING,
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
    "governance.case.created",
    "governance.case.assigned",
    "governance.case.priority_changed",
    "governance.case.escalated",
    "governance.case.resolved",
    "governance.case.reopened",
    "enforcement.action.activated",
    "enforcement.action.revoked",
    "appeal.assigned",
    "appeal.decided",
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
PERMISSION_REPORTS_ESCALATE = "reports.escalate"
PERMISSION_REPORTS_TEAMS = "reports.teams"

# Phase 11 permission codes (also seeded in catalog + migration 0009).
PERMISSION_ENFORCEMENT_READ = "enforcement.read"
PERMISSION_ENFORCEMENT_CREATE = "enforcement.create"
PERMISSION_ENFORCEMENT_APPROVE = "enforcement.approve"
PERMISSION_ENFORCEMENT_REVOKE = "enforcement.revoke"
PERMISSION_ENFORCEMENT_REINSTATE = "enforcement.reinstate"
PERMISSION_APPEALS_READ = "appeals.read"
PERMISSION_APPEALS_MANAGE = "appeals.manage"
PERMISSION_APPEALS_DECIDE = "appeals.decide"

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

# --- Athena AI core (Phase 14) --------------------------------------------------
# Athena operates in explicit modes; GOVERNMENT / PLATFORM_OPERATOR are
# architecture-only in Phase 14 (no tools registered) and never reachable by
# ordinary users.
ATHENA_MODE_JOBSEEKER = "jobseeker"
ATHENA_MODE_EMPLOYER = "employer"
ATHENA_MODE_RECRUITER = "recruiter"
ATHENA_MODE_GOVERNMENT = "government"
ATHENA_MODE_PLATFORM_OPERATOR = "platform_operator"
ATHENA_MODES = {
    ATHENA_MODE_JOBSEEKER,
    ATHENA_MODE_EMPLOYER,
    ATHENA_MODE_RECRUITER,
    ATHENA_MODE_GOVERNMENT,
    ATHENA_MODE_PLATFORM_OPERATOR,
}
# Modes whose tool surface exists in Phase 14.
ATHENA_TOOL_MODES = {
    ATHENA_MODE_JOBSEEKER,
    ATHENA_MODE_EMPLOYER,
    ATHENA_MODE_RECRUITER,
}

ATHENA_SESSION_STATUS_ACTIVE = "active"
ATHENA_SESSION_STATUS_CLOSED = "closed"
ATHENA_SESSION_STATUS_EXPIRED = "expired"
ATHENA_SESSION_STATUSES = {
    ATHENA_SESSION_STATUS_ACTIVE,
    ATHENA_SESSION_STATUS_CLOSED,
    ATHENA_SESSION_STATUS_EXPIRED,
}

ATHENA_MESSAGE_ROLE_USER = "user"
ATHENA_MESSAGE_ROLE_ASSISTANT = "assistant"
ATHENA_MESSAGE_ROLE_SYSTEM = "system"
ATHENA_MESSAGE_ROLE_TOOL = "tool"
ATHENA_MESSAGE_ROLES = {
    ATHENA_MESSAGE_ROLE_USER,
    ATHENA_MESSAGE_ROLE_ASSISTANT,
    ATHENA_MESSAGE_ROLE_SYSTEM,
    ATHENA_MESSAGE_ROLE_TOOL,
}

# Risk classification for Athena tools (never derived from model output).
ATHENA_RISK_READ_ONLY = "read_only"
ATHENA_RISK_LOW_RISK_WRITE = "low_risk_write"
ATHENA_RISK_HIGH_RISK_WRITE = "high_risk_write"
ATHENA_RISK_LEVELS = {
    ATHENA_RISK_READ_ONLY,
    ATHENA_RISK_LOW_RISK_WRITE,
    ATHENA_RISK_HIGH_RISK_WRITE,
}

# High-risk actions always require an explicit user confirmation.
ATHENA_CONFIRMATION_REQUIRED_RISKS = {ATHENA_RISK_HIGH_RISK_WRITE}

ATHENA_CONFIRMATION_STATUS_PENDING = "pending"
ATHENA_CONFIRMATION_STATUS_APPROVED = "approved"
ATHENA_CONFIRMATION_STATUS_DENIED = "denied"
ATHENA_CONFIRMATION_STATUS_EXPIRED = "expired"
ATHENA_CONFIRMATION_STATUS_CANCELLED = "cancelled"
ATHENA_CONFIRMATION_STATUSES = {
    ATHENA_CONFIRMATION_STATUS_PENDING,
    ATHENA_CONFIRMATION_STATUS_APPROVED,
    ATHENA_CONFIRMATION_STATUS_DENIED,
    ATHENA_CONFIRMATION_STATUS_EXPIRED,
    ATHENA_CONFIRMATION_STATUS_CANCELLED,
}

# Provider-neutral AI error codes (never leak provider internals).
AI_ERROR_PROVIDER_UNAVAILABLE = "ai.provider_unavailable"
AI_ERROR_PROVIDER_TIMEOUT = "ai.provider_timeout"
AI_ERROR_OUTPUT_INVALID = "ai.output_invalid"
AI_ERROR_TOOL_NOT_AUTHORIZED = "ai.tool_not_authorized"
AI_ERROR_TOOL_VALIDATION_FAILED = "ai.tool_validation_failed"
AI_ERROR_RATE_LIMITED = "ai.rate_limited"
AI_ERROR_CONTEXT_LIMIT_EXCEEDED = "ai.context_limit_exceeded"
AI_ERROR_INTERNAL = "ai.internal_error"
AI_ERROR_CODES = {
    AI_ERROR_PROVIDER_UNAVAILABLE,
    AI_ERROR_PROVIDER_TIMEOUT,
    AI_ERROR_OUTPUT_INVALID,
    AI_ERROR_TOOL_NOT_AUTHORIZED,
    AI_ERROR_TOOL_VALIDATION_FAILED,
    AI_ERROR_RATE_LIMITED,
    AI_ERROR_CONTEXT_LIMIT_EXCEEDED,
    AI_ERROR_INTERNAL,
}

# Provider capabilities (only what Phase 14 requires is implemented).
AI_CAPABILITY_TEXT_GENERATION = "text_generation"
AI_CAPABILITY_STRUCTURED_OUTPUT = "structured_output"
AI_CAPABILITY_TOOL_CALLING = "tool_calling"
AI_CAPABILITIES = {
    AI_CAPABILITY_TEXT_GENERATION,
    AI_CAPABILITY_STRUCTURED_OUTPUT,
    AI_CAPABILITY_TOOL_CALLING,
}

# Athena audit actions.
AUDIT_ACTION_ATHENA_SESSION_CREATED = "athena.session.created"
AUDIT_ACTION_ATHENA_MESSAGE = "athena.message"
AUDIT_ACTION_ATHENA_TOOL_EXECUTED = "athena.tool.executed"
AUDIT_ACTION_ATHENA_TOOL_DENIED = "athena.tool.denied"
AUDIT_ACTION_ATHENA_CONFIRMATION_REQUESTED = "athena.confirmation.requested"
AUDIT_ACTION_ATHENA_CONFIRMATION_DECIDED = "athena.confirmation.decided"
AUDIT_ACTION_ATHENA_CONFIRMATION_EXPIRED = "athena.confirmation.expired"
