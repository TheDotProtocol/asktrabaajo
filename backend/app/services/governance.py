"""Platform governance service (Phase 9 + Phase 10 operations).

The governance domain sits ABOVE the product domains:

- Any authenticated user may FILE a report (abuse, fraud, impersonation,
  policy violation, communication dispute, document misuse, recruiter
  misconduct, suspicious activity, platform integrity, ...). The report
  REFERENCES platform objects; it never copies private Work ID data or
  document contents.
- Phase 10 turns the same row into the operational case model: explicit
  priority (separate from severity), governance-team routing, escalation
  markers and a DETERMINISTIC SLA policy derived from priority. No second
  moderation system and no scheduler — SLA state is evaluated lazily from
  stored deadlines.
- Only platform-scope roles (moderator, governance auditor, super admin)
  may READ the queue, and only with ``reports.*`` permissions. Employers,
  recruiters, candidates and government analysts can never access it.
- Every governance action is audited; internal notes are visible to
  governance roles only.

Least privilege: reading a case gives the moderator the case fields + audit
history + notes + *case links* — NOT the target's private Work ID sections.
Integrity signals are neutral activity-pattern markers ("review required"),
never accusations.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.core.errors import (
    InvalidInputError,
    NotFoundError,
    PermissionDeniedError,
)
from app.core.timeutil import utc_now_naive
from app.models.audit import AuditLogEntry
from app.models.communication import OutreachRequest, OutreachBlock
from app.models.enums import (
    PERMISSION_PLATFORM_AUDIT_READ,
    PERMISSION_REPORTS_ESCALATE,
    PERMISSION_REPORTS_MANAGE,
    PERMISSION_REPORTS_READ,
    PERMISSION_REPORTS_TEAMS,
    REPORT_CATEGORIES,
    REPORT_OPEN_STATUSES,
    REPORT_PRIORITIES,
    REPORT_PRIORITY_NORMAL,
    REPORT_SEVERITIES,
    REPORT_SLA_HOURS,
    REPORT_STATUS_CLOSED,
    REPORT_STATUS_ESCALATED,
    REPORT_STATUSES,
    REPORT_STATUS_OPEN,
    REPORT_STATUS_RESOLVED,
    REPORT_TARGET_TYPES,
    SIGNAL_STATUS_REVIEW_REQUIRED,
    SLA_STATE_BREACHED,
    SLA_STATE_DUE_SOON,
    SLA_STATE_ON_TRACK,
)
from app.models.governance import (
    GovernanceCaseLink,
    GovernanceReport,
    GovernanceReportNote,
    GovernanceTeam,
    GovernanceTeamMember,
)
from app.models.identity import User
from app.models.tenancy import Membership, Organization, RolePermission

# Table name of the canonical roles catalog used to decide who is a governance
# actor (avoids importing the seed catalog inside service logic).
_GOVERNANCE_ROLES = {"moderator", "super_admin", "governance_auditor"}

# --- internal helpers ---------------------------------------------------------

def _require_platform(db: Session, user_id: uuid.UUID, permission: str) -> None:
    from app.services import authz

    authz.require_platform_permission(db, user_id, permission)


def _report(db: Session, report_id: uuid.UUID) -> GovernanceReport:
    report = db.get(GovernanceReport, report_id)
    if report is None:
        raise NotFoundError("Report not found.")
    return report


def _team(db: Session, team_id: Optional[uuid.UUID]) -> Optional[GovernanceTeam]:
    if team_id is None:
        return None
    return db.get(GovernanceTeam, team_id)


def _mark_first_responded(report: GovernanceReport, now: datetime) -> None:
    if report.first_responded_at is None and report.status != REPORT_STATUS_OPEN:
        report.first_responded_at = now


def _apply_sla_deadlines(report: GovernanceReport, now: datetime) -> None:
    """(Re)compute deterministic SLA deadlines from the current priority.

    Deadlines restart whenever priority changes or a case is escalated so
    the clock measures the CURRENT service level — documented in the phase
    report. First response is not erased by a restart.
    """
    resp_h, resol_h = REPORT_SLA_HOURS.get(
        report.priority, REPORT_SLA_HOURS[REPORT_PRIORITY_NORMAL]
    )
    report.sla_response_due_at = now + timedelta(hours=resp_h)
    report.sla_resolution_due_at = now + timedelta(hours=resol_h)


# SLA-filtered views and due-soon counts evaluate the newest N open cases in
# Python (exact, deterministic) instead of pushing per-priority thresholds into
# SQL. N is bounded so no query scans the whole table.
MAX_SLA_SCAN = 10_000


def _due_soon_threshold_seconds(report: GovernanceReport) -> tuple:
    """(response_threshold_s, resolution_threshold_s) = 20% of each window."""
    resp_h, resol_h = REPORT_SLA_HOURS.get(
        report.priority, REPORT_SLA_HOURS[REPORT_PRIORITY_NORMAL]
    )
    return 0.2 * resp_h * 3600, 0.2 * resol_h * 3600


def sla_state_for(report: GovernanceReport, now: Optional[datetime] = None) -> str:
    """Deterministic, lazy SLA state — no scheduler.

    Rules (uniform and testable):
    - resolved/closed cases are on track (their status is the outcome).
    - breached: the response deadline passed before a first response, OR the
      resolution deadline passed while the case is still open.
    - due_soon: an open deadline has no more than 20% of ITS OWN window
      remaining (per-priority), and is not already breached.
    - otherwise on_track.
    """
    now = now or utc_now_naive()
    if report.status in (REPORT_STATUS_RESOLVED, REPORT_STATUS_CLOSED):
        return SLA_STATE_ON_TRACK
    response_open = (
        report.sla_response_due_at is not None
        and report.first_responded_at is None
    )
    resolution_open = report.sla_resolution_due_at is not None
    if (response_open and report.sla_response_due_at < now) or (
        resolution_open and report.sla_resolution_due_at < now
    ):
        return SLA_STATE_BREACHED
    resp_threshold, resol_threshold = _due_soon_threshold_seconds(report)
    if (response_open and report.sla_response_due_at <= now + timedelta(seconds=resp_threshold)) or (
        resolution_open
        and report.sla_resolution_due_at <= now + timedelta(seconds=resol_threshold)
    ):
        return SLA_STATE_DUE_SOON
    return SLA_STATE_ON_TRACK


def _scan_open_for_sla(db: Session) -> list:
    """Newest open cases (bounded) for exact SLA evaluation in Python."""
    rows = db.scalars(
        select(GovernanceReport)
        .where(GovernanceReport.status.in_(REPORT_OPEN_STATUSES))
        .order_by(GovernanceReport.created_at.desc())
        .limit(MAX_SLA_SCAN)
    ).all()
    return list(rows)


def _open_filter():
    return GovernanceReport.status.in_(REPORT_OPEN_STATUSES)


def _breached_filter(now: datetime):
    return and_(
        ~GovernanceReport.status.in_([REPORT_STATUS_RESOLVED, REPORT_STATUS_CLOSED]),
        or_(
            and_(
                GovernanceReport.sla_response_due_at.is_not(None),
                GovernanceReport.first_responded_at.is_(None),
                GovernanceReport.sla_response_due_at < now,
            ),
            and_(
                GovernanceReport.sla_resolution_due_at.is_not(None),
                GovernanceReport.sla_resolution_due_at < now,
            ),
        ),
    )


def _case_ref(report_id: uuid.UUID) -> str:
    return f"GOV-{str(report_id)[:8].upper()}"


def _sanitize_payload(payload: Optional[dict]) -> dict:
    """Strip anything that could carry secrets or message contents."""
    if not isinstance(payload, dict):
        return {}
    BLOCKED = ("password", "token", "secret", "body", "authorization", "credential")
    out = {}
    for key, value in payload.items():
        if any(part in key.lower() for part in BLOCKED):
            continue
        if isinstance(value, dict):
            out[key] = _sanitize_payload(value)
        elif isinstance(value, str) and len(value) > 500:
            out[key] = value[:500] + "…"
        else:
            out[key] = value
    return out


# --- filing -------------------------------------------------------------------

def create_report(
    db: Session,
    actor_id: uuid.UUID,
    *,
    target_type: str,
    target_id: str,
    category: str,
    description: str,
    organization_id: Optional[uuid.UUID] = None,
    severity: str = "medium",
    evidence_refs: Optional[list] = None,
) -> GovernanceReport:
    if target_type not in REPORT_TARGET_TYPES:
        raise InvalidInputError(
            f"target_type must be one of {sorted(REPORT_TARGET_TYPES)}."
        )
    if category not in REPORT_CATEGORIES:
        raise InvalidInputError(f"category must be one of {sorted(REPORT_CATEGORIES)}.")
    if severity not in REPORT_SEVERITIES:
        raise InvalidInputError(f"severity must be one of {sorted(REPORT_SEVERITIES)}.")
    if organization_id is not None and db.get(Organization, organization_id) is None:
        raise InvalidInputError("organization_id does not reference an organization.")

    # Evidence references only — {type, id, note}. Contents never accepted.
    normalized_refs = None
    if evidence_refs:
        normalized_refs = []
        for ref in evidence_refs[:10]:
            if not isinstance(ref, dict) or "type" not in ref or "id" not in ref:
                raise InvalidInputError(
                    "evidence_refs entries must be {type, id, note?} references."
                )
            normalized_refs.append(
                {
                    "type": str(ref["type"])[:40],
                    "id": str(ref["id"])[:64],
                    "note": (str(ref.get("note"))[:300] if ref.get("note") else None),
                }
            )

    now = utc_now_naive()
    report = GovernanceReport(
        reporter_user_id=actor_id,
        target_type=target_type,
        target_id=str(target_id)[:64],
        organization_id=organization_id,
        category=category,
        severity=severity,
        priority=REPORT_PRIORITY_NORMAL,
        status=REPORT_STATUS_OPEN,
        description=description.strip(),
        evidence_refs=normalized_refs,
    )
    _apply_sla_deadlines(report, now)
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


# --- queue / detail --------------------------------------------------------------

def list_reports(
    db: Session,
    actor_id: uuid.UUID,
    *,
    status: Optional[str] = None,
    severity: Optional[str] = None,
    priority: Optional[str] = None,
    category: Optional[str] = None,
    team_id: Optional[uuid.UUID] = None,
    assigned_to: Optional[uuid.UUID] = None,
    unassigned: bool = False,
    mine: bool = False,
    escalated: bool = False,
    sla: Optional[str] = None,
    organization_id: Optional[uuid.UUID] = None,
    sort: str = "created_at",
    page: int = 1,
    page_size: int = 25,
) -> dict:
    _require_platform(db, actor_id, PERMISSION_REPORTS_READ)
    query = select(GovernanceReport)
    if status:
        if status not in REPORT_STATUSES:
            raise InvalidInputError(f"Unknown status '{status}'.")
        query = query.where(GovernanceReport.status == status)
    if severity:
        if severity not in REPORT_SEVERITIES:
            raise InvalidInputError(f"Unknown severity '{severity}'.")
        query = query.where(GovernanceReport.severity == severity)
    if priority:
        if priority not in REPORT_PRIORITIES:
            raise InvalidInputError(f"Unknown priority '{priority}'.")
        query = query.where(GovernanceReport.priority == priority)
    if category:
        query = query.where(GovernanceReport.category == category)
    if team_id:
        query = query.where(GovernanceReport.team_id == team_id)
    if assigned_to:
        query = query.where(GovernanceReport.assigned_moderator_id == assigned_to)
    if unassigned:
        query = query.where(
            GovernanceReport.assigned_moderator_id.is_(None),
            GovernanceReport.status.in_(REPORT_OPEN_STATUSES),
        )
    if mine:
        query = query.where(
            GovernanceReport.assigned_moderator_id == actor_id,
            GovernanceReport.status.in_(REPORT_OPEN_STATUSES),
        )
    if escalated:
        query = query.where(GovernanceReport.status == REPORT_STATUS_ESCALATED)
    if organization_id:
        query = query.where(GovernanceReport.organization_id == organization_id)

    now = utc_now_naive()
    sla_mode = sla in (SLA_STATE_BREACHED, SLA_STATE_DUE_SOON)
    if sla is not None and not sla_mode:
        raise InvalidInputError(
            f"sla must be one of {[SLA_STATE_BREACHED, SLA_STATE_DUE_SOON]}."
        )

    ordering = {
        "created_at": GovernanceReport.created_at.desc(),
        "updated_at": GovernanceReport.updated_at.desc(),
        "severity": GovernanceReport.severity.asc(),
        "priority": GovernanceReport.priority.asc(),
        "sla_due": GovernanceReport.sla_resolution_due_at.asc().nulls_last(),
    }
    order = ordering.get(sort, ordering["created_at"])

    if not sla_mode:
        total = len(
            db.scalars(select(func.count()).select_from(query.subquery())).all()
        )
        rows = db.scalars(
            query.order_by(order).offset((page - 1) * page_size).limit(page_size)
        ).all()
        return {
            "items": [report_out(db, r) for r in rows],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    # Exact, deterministic SLA filtering in Python over the bounded newest
    # matching scan (SLA state needs per-priority thresholds that SQL cannot
    # express portably). Documented in the phase report.
    ids = [r[0] for r in db.execute(query.with_only_columns(GovernanceReport.id)).all()]
    base = {
        r.id: r
        for r in db.scalars(
            select(GovernanceReport).where(
                GovernanceReport.id.in_(ids[:MAX_SLA_SCAN])
            )
        ).all()
    }
    matched = [
        base[cid]
        for cid in ids[:MAX_SLA_SCAN]
        if cid in base and sla_state_for(base[cid], now) == sla
    ]
    matched.sort(key=lambda r: r.created_at, reverse=True)
    total = len(matched)
    page_rows = matched[(page - 1) * page_size : page * page_size]
    return {
        "items": [report_out(db, r) for r in page_rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def report_out(
    db: Session, report: GovernanceReport, include_notes: bool = False
) -> dict:
    org = db.get(Organization, report.organization_id) if report.organization_id else None
    assigned = (
        db.get(User, report.assigned_moderator_id)
        if report.assigned_moderator_id
        else None
    )
    team = _team(db, report.team_id)
    escalated_team = _team(db, report.escalated_to_team_id)
    payload = {
        "id": str(report.id),
        "case_ref": _case_ref(report.id),
        "reporter_user_id": str(report.reporter_user_id),
        "target_type": report.target_type,
        "target_id": report.target_id,
        "organization_id": str(report.organization_id) if report.organization_id else None,
        "organization_name": org.name if org else None,
        "category": report.category,
        "severity": report.severity,
        "priority": report.priority,
        "status": report.status,
        "description": report.description,
        "evidence_refs": report.evidence_refs or [],
        "assigned_moderator_id": (
            str(report.assigned_moderator_id) if report.assigned_moderator_id else None
        ),
        "assigned_moderator_name": assigned.full_name if assigned else None,
        "team_id": str(report.team_id) if report.team_id else None,
        "team_name": team.name if team else None,
        "team_slug": team.slug if team else None,
        "escalated_at": report.escalated_at,
        "escalated_to_team_id": (
            str(report.escalated_to_team_id) if report.escalated_to_team_id else None
        ),
        "escalated_to_team_name": escalated_team.name if escalated_team else None,
        "first_responded_at": report.first_responded_at,
        "sla_response_due_at": report.sla_response_due_at,
        "sla_resolution_due_at": report.sla_resolution_due_at,
        "sla_state": sla_state_for(report),
        "resolution": report.resolution,
        "resolved_at": report.resolved_at,
        "reopened_count": report.reopened_count,
        "created_at": report.created_at,
        "updated_at": report.updated_at,
    }
    if include_notes:
        notes = db.scalars(
            select(GovernanceReportNote)
            .where(GovernanceReportNote.report_id == report.id)
            .order_by(GovernanceReportNote.created_at.asc())
        ).all()
        payload["notes"] = [
            {
                "id": str(n.id),
                "author_user_id": str(n.author_user_id),
                "body": n.body,
                "created_at": n.created_at,
            }
            for n in notes
        ]
    return payload


def get_report(db: Session, actor_id: uuid.UUID, report_id: uuid.UUID) -> dict:
    _require_platform(db, actor_id, PERMISSION_REPORTS_READ)
    report = _report(db, report_id)
    payload = report_out(db, report, include_notes=True)
    link_rows = db.scalars(
        select(GovernanceCaseLink).where(GovernanceCaseLink.case_id == report.id)
    ).all()
    payload["links"] = []
    for link in link_rows:
        linked = db.get(GovernanceReport, link.linked_report_id)
        if linked is None:
            continue
        payload["links"].append(
            {
                "link_id": str(link.id),
                "report_id": str(linked.id),
                "case_ref": _case_ref(linked.id),
                "category": linked.category,
                "severity": linked.severity,
                "status": linked.status,
                "created_at": link.created_at,
                "reason": link.reason,
            }
        )
    return payload


def _count(db: Session, *conditions) -> int:
    q = select(func.count()).select_from(GovernanceReport)
    if conditions:
        q = q.where(and_(*conditions))
    return db.scalar(q) or 0


def governance_dashboard(db: Session, actor_id: uuid.UUID) -> dict:
    _require_platform(db, actor_id, PERMISSION_REPORTS_READ)
    rows = db.execute(
        select(GovernanceReport.status, func.count())
        .group_by(GovernanceReport.status)
    ).all()
    severity_rows = db.execute(
        select(GovernanceReport.severity, func.count())
        .group_by(GovernanceReport.severity)
    ).all()
    priority_rows = db.execute(
        select(GovernanceReport.priority, func.count())
        .group_by(GovernanceReport.priority)
    ).all()
    category_rows = db.execute(
        select(GovernanceReport.category, func.count())
        .group_by(GovernanceReport.category)
    ).all()
    team_rows = db.execute(
        select(GovernanceReport.team_id, func.count())
        .where(GovernanceReport.status.in_(REPORT_OPEN_STATUSES))
        .group_by(GovernanceReport.team_id)
    ).all()
    now = utc_now_naive()
    open_count = sum(count for status, count in rows if status in REPORT_OPEN_STATUSES)
    breached_count = _count(db, _breached_filter(now))
    due_soon_count = sum(
        1 for r in _scan_open_for_sla(db) if sla_state_for(r, now) == SLA_STATE_DUE_SOON
    )
    return {
        "total": _count(db),
        "open": open_count,
        "urgent": _count(
            db,
            _open_filter(),
            GovernanceReport.priority.in_(["urgent", "critical"]),
        ),
        "critical": _count(db, _open_filter(), GovernanceReport.priority == "critical"),
        "unassigned": _count(
            db,
            _open_filter(),
            GovernanceReport.assigned_moderator_id.is_(None),
        ),
        "mine": _count(
            db,
            _open_filter(),
            GovernanceReport.assigned_moderator_id == actor_id,
        ),
        "escalated": _count(db, GovernanceReport.status == REPORT_STATUS_ESCALATED),
        "breached": breached_count,
        "due_soon": due_soon_count,
        "recently_resolved": _count(
            db,
            GovernanceReport.status == REPORT_STATUS_RESOLVED,
            GovernanceReport.resolved_at
            >= (now - timedelta(days=7)),
        ),
        "by_status": {status: count for status, count in rows},
        "by_severity": {severity: count for severity, count in severity_rows},
        "by_priority": {priority: count for priority, count in priority_rows},
        "by_category": {category: count for category, count in category_rows},
        "by_team": {
            str(team_id): count
            for team_id, count in team_rows
            if team_id is not None
        },
    }


# --- moderation actions -----------------------------------------------------------

def update_status(
    db: Session,
    actor_id: uuid.UUID,
    report_id: uuid.UUID,
    status: str,
) -> GovernanceReport:
    if status == REPORT_STATUS_ESCALATED:
        # Escalation is an explicit, audited act — never a bare status flip.
        raise InvalidInputError(
            "Escalation must go through the escalate action."
        )
    _require_platform(db, actor_id, PERMISSION_REPORTS_MANAGE)
    if status not in REPORT_STATUSES:
        raise InvalidInputError(f"Unknown status '{status}'.")
    report = _report(db, report_id)
    if report.status == "resolved" and status != "closed":
        raise InvalidInputError("Resolved reports must be reopened before rework.")
    report.status = status
    now = utc_now_naive()
    _mark_first_responded(report, now)
    if status == "assigned" and report.assigned_moderator_id is None:
        report.assigned_moderator_id = actor_id
    db.commit()
    db.refresh(report)
    return report


def assign_report(
    db: Session,
    actor_id: uuid.UUID,
    report_id: uuid.UUID,
    moderator_user_id: Optional[uuid.UUID] = None,
) -> GovernanceReport:
    _require_platform(db, actor_id, "reports.assign")
    report = _report(db, report_id)
    if moderator_user_id is None:
        moderator_user_id = actor_id
    else:
        # The assignee must be a platform governance actor (no arbitrary user).
        _require_platform(db, moderator_user_id, "reports.read")
        if report.team_id is not None:
            # Team-routed cases go to members of that team (routing sanity).
            membership = db.scalar(
                select(GovernanceTeamMember).where(
                    GovernanceTeamMember.team_id == report.team_id,
                    GovernanceTeamMember.user_id == moderator_user_id,
                )
            )
            if membership is None:
                raise InvalidInputError(
                    "The assignee is not a member of this case's team."
                )
    report.assigned_moderator_id = moderator_user_id
    if report.status in {"open", "in_review"}:
        report.status = "assigned"
    _mark_first_responded(report, utc_now_naive())
    db.commit()
    db.refresh(report)
    return report


def change_priority(
    db: Session,
    actor_id: uuid.UUID,
    report_id: uuid.UUID,
    priority: str,
) -> GovernanceReport:
    _require_platform(db, actor_id, PERMISSION_REPORTS_ESCALATE)
    if priority not in REPORT_PRIORITIES:
        raise InvalidInputError(f"priority must be one of {sorted(REPORT_PRIORITIES)}.")
    report = _report(db, report_id)
    if report.status in (REPORT_STATUS_RESOLVED, REPORT_STATUS_CLOSED):
        raise InvalidInputError("Resolved/closed cases cannot change priority.")
    report.priority = priority
    now = utc_now_naive()
    _apply_sla_deadlines(report, now)  # deterministic restart from the change
    db.commit()
    db.refresh(report)
    return report


def set_case_team(
    db: Session,
    actor_id: uuid.UUID,
    report_id: uuid.UUID,
    team_id: Optional[uuid.UUID],
) -> GovernanceReport:
    _require_platform(db, actor_id, PERMISSION_REPORTS_MANAGE)
    report = _report(db, report_id)
    if team_id is not None and db.get(GovernanceTeam, team_id) is None:
        raise InvalidInputError("team_id does not reference a governance team.")
    report.team_id = team_id
    db.commit()
    db.refresh(report)
    return report


def escalate_case(
    db: Session,
    actor_id: uuid.UUID,
    report_id: uuid.UUID,
    *,
    reason: str,
    to_priority: Optional[str] = None,
    to_severity: Optional[str] = None,
    to_team_id: Optional[uuid.UUID] = None,
) -> GovernanceReport:
    _require_platform(db, actor_id, PERMISSION_REPORTS_ESCALATE)
    reason = (reason or "").strip()
    if len(reason) < 10:
        raise InvalidInputError(
            "An escalation reason of at least 10 characters is required."
        )
    if to_priority is not None and to_priority not in REPORT_PRIORITIES:
        raise InvalidInputError(
            f"priority must be one of {sorted(REPORT_PRIORITIES)}."
        )
    if to_severity is not None and to_severity not in REPORT_SEVERITIES:
        raise InvalidInputError(
            f"severity must be one of {sorted(REPORT_SEVERITIES)}."
        )
    if to_team_id is not None and db.get(GovernanceTeam, to_team_id) is None:
        raise InvalidInputError("to_team_id does not reference a governance team.")
    report = _report(db, report_id)
    if report.status in (REPORT_STATUS_RESOLVED, REPORT_STATUS_CLOSED):
        raise InvalidInputError("Resolved/closed cases must be reopened before escalation.")
    now = utc_now_naive()
    if to_priority is not None:
        report.priority = to_priority
    if to_severity is not None:
        report.severity = to_severity
    if to_team_id is not None:
        report.team_id = to_team_id
        report.escalated_to_team_id = to_team_id
    report.escalated_at = now
    report.escalated_by = actor_id
    report.status = REPORT_STATUS_ESCALATED
    _mark_first_responded(report, now)
    _apply_sla_deadlines(report, now)
    db.commit()
    db.refresh(report)
    return report


def add_note(
    db: Session,
    actor_id: uuid.UUID,
    report_id: uuid.UUID,
    body: str,
) -> GovernanceReportNote:
    _require_platform(db, actor_id, PERMISSION_REPORTS_MANAGE)
    report = _report(db, report_id)
    if report.status == "closed":
        raise InvalidInputError("Closed reports cannot be annotated; reopen first.")
    note = GovernanceReportNote(
        report_id=report.id, author_user_id=actor_id, body=body.strip()
    )
    _mark_first_responded(report, utc_now_naive())
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


def resolve_report(
    db: Session,
    actor_id: uuid.UUID,
    report_id: uuid.UUID,
    resolution: str,
) -> GovernanceReport:
    _require_platform(db, actor_id, "reports.resolve")
    report = _report(db, report_id)
    if report.status in {"resolved", "closed"}:
        raise InvalidInputError("This report is already resolved/closed.")
    report.status = "resolved"
    report.resolution = resolution.strip()
    report.resolved_at = utc_now_naive()
    report.resolved_by = actor_id
    db.commit()
    db.refresh(report)
    return report


def reopen_report(
    db: Session,
    actor_id: uuid.UUID,
    report_id: uuid.UUID,
) -> GovernanceReport:
    _require_platform(db, actor_id, "reports.resolve")
    report = _report(db, report_id)
    if report.status not in {"resolved", "closed"}:
        raise InvalidInputError("Only resolved/closed reports can be reopened.")
    report.status = "in_review"
    report.reopened_count += 1
    report.resolved_at = None
    report.resolved_by = None
    _apply_sla_deadlines(report, utc_now_naive())
    db.commit()
    db.refresh(report)
    return report


# --- case links (Phase 10) -------------------------------------------------------

def link_report(
    db: Session,
    actor_id: uuid.UUID,
    report_id: uuid.UUID,
    linked_report_id: uuid.UUID,
    reason: Optional[str] = None,
) -> GovernanceCaseLink:
    _require_platform(db, actor_id, PERMISSION_REPORTS_MANAGE)
    if report_id == linked_report_id:
        raise InvalidInputError("A case cannot link to itself.")
    case = _report(db, report_id)
    linked = _report(db, linked_report_id)
    # Tenant boundary: linking across organizations is refused.
    if (
        case.organization_id is not None
        and linked.organization_id is not None
        and case.organization_id != linked.organization_id
    ):
        raise InvalidInputError(
            "Reports from different organizations cannot be linked."
        )
    existing = db.scalar(
        select(GovernanceCaseLink).where(
            GovernanceCaseLink.case_id == report_id,
            GovernanceCaseLink.linked_report_id == linked_report_id,
        )
    )
    if existing is not None:
        raise InvalidInputError("This report is already linked to the case.")
    link = GovernanceCaseLink(
        case_id=report_id,
        linked_report_id=linked_report_id,
        created_by=actor_id,
        reason=(reason or "").strip()[:300] or None,
    )
    db.add(link)
    db.commit()
    db.refresh(link)
    return link


def unlink_report(
    db: Session,
    actor_id: uuid.UUID,
    case_id: uuid.UUID,
    link_id: uuid.UUID,
) -> None:
    _require_platform(db, actor_id, PERMISSION_REPORTS_MANAGE)
    link = db.get(GovernanceCaseLink, link_id)
    if link is None or link.case_id != case_id:
        raise NotFoundError("Link not found.")
    db.delete(link)
    db.commit()


# --- governance teams (Phase 10) ---------------------------------------------------

def _governance_actor_user_ids(db: Session) -> list:
    """Distinct users holding a platform-scope governance role."""
    codes = list(_GOVERNANCE_ROLES)
    rows = db.execute(
        select(Membership.user_id).where(
            Membership.role_code.in_(codes),
            Membership.organization_id.in_(
                select(Organization.id).where(Organization.kind == "platform")
            ),
        )
    ).all()
    return list({row[0] for row in rows})


def list_moderators(db: Session, actor_id: uuid.UUID) -> list:
    """Governance actors available for assignment (id + name only)."""
    _require_platform(db, actor_id, PERMISSION_REPORTS_READ)
    user_ids = _governance_actor_user_ids(db)
    out = []
    for uid in user_ids:
        user = db.get(User, uid)
        if user is None:
            continue
        out.append(
            {
                "user_id": str(user.id),
                "full_name": user.full_name,
                "roles": list(
                    db.scalars(
                        select(Membership.role_code).where(
                            Membership.user_id == user.id,
                            Membership.role_code.in_(_GOVERNANCE_ROLES),
                        )
                    ).all()
                ),
            }
        )
    return out


def list_teams(db: Session, actor_id: uuid.UUID) -> dict:
    _require_platform(db, actor_id, PERMISSION_REPORTS_READ)
    teams = db.scalars(select(GovernanceTeam).order_by(GovernanceTeam.name)).all()
    items = []
    for team in teams:
        open_count = _count(
            db,
            GovernanceReport.team_id == team.id,
            GovernanceReport.status.in_(REPORT_OPEN_STATUSES),
        )
        members = db.scalars(
            select(GovernanceTeamMember.user_id).where(
                GovernanceTeamMember.team_id == team.id
            )
        ).all()
        items.append(
            {
                "id": str(team.id),
                "slug": team.slug,
                "name": team.name,
                "description": team.description,
                "member_count": len(members),
                "open_cases": open_count,
            }
        )
    return {"items": items, "total": len(items)}


def get_team(db: Session, actor_id: uuid.UUID, team_id: uuid.UUID) -> dict:
    _require_platform(db, actor_id, PERMISSION_REPORTS_READ)
    team = db.get(GovernanceTeam, team_id)
    if team is None:
        raise NotFoundError("Team not found.")
    members = []
    for row in db.execute(
        select(
            GovernanceTeamMember.user_id,
            GovernanceTeamMember.created_at,
            User.full_name,
        )
        .join(User, User.id == GovernanceTeamMember.user_id)
        .where(GovernanceTeamMember.team_id == team.id)
        .order_by(User.full_name)
    ).all():
        members.append(
            {
                "user_id": str(row.user_id),
                "full_name": row.full_name,
                "joined_at": row.created_at,
            }
        )
    now = utc_now_naive()
    return {
        "id": str(team.id),
        "slug": team.slug,
        "name": team.name,
        "description": team.description,
        "members": members,
        "counts": {
            "open": _count(
                db,
                GovernanceReport.team_id == team.id,
                GovernanceReport.status.in_(REPORT_OPEN_STATUSES),
            ),
            "urgent": _count(
                db,
                GovernanceReport.team_id == team.id,
                _open_filter(),
                GovernanceReport.priority.in_(["urgent", "critical"]),
            ),
            "breached": _count(
                db,
                GovernanceReport.team_id == team.id,
                _breached_filter(now),
            ),
            "unresolved": _count(
                db,
                GovernanceReport.team_id == team.id,
                ~GovernanceReport.status.in_(
                    [REPORT_STATUS_RESOLVED, REPORT_STATUS_CLOSED]
                ),
            ),
        },
    }


def add_team_member(
    db: Session,
    actor_id: uuid.UUID,
    team_id: uuid.UUID,
    user_id: uuid.UUID,
) -> GovernanceTeamMember:
    _require_platform(db, actor_id, PERMISSION_REPORTS_TEAMS)
    team = db.get(GovernanceTeam, team_id)
    if team is None:
        raise NotFoundError("Team not found.")
    if db.get(User, user_id) is None:
        raise InvalidInputError("user_id does not reference a user.")
    if user_id not in _governance_actor_user_ids(db):
        raise InvalidInputError("Only platform governance users can join teams.")
    existing = db.scalar(
        select(GovernanceTeamMember).where(
            GovernanceTeamMember.team_id == team_id,
            GovernanceTeamMember.user_id == user_id,
        )
    )
    if existing is not None:
        raise InvalidInputError("This user is already a team member.")
    member = GovernanceTeamMember(
        team_id=team_id, user_id=user_id, created_by=actor_id
    )
    db.add(member)
    db.commit()
    db.refresh(member)
    return member


def remove_team_member(
    db: Session,
    actor_id: uuid.UUID,
    team_id: uuid.UUID,
    user_id: uuid.UUID,
) -> None:
    _require_platform(db, actor_id, PERMISSION_REPORTS_TEAMS)
    member = db.scalar(
        select(GovernanceTeamMember).where(
            GovernanceTeamMember.team_id == team_id,
            GovernanceTeamMember.user_id == user_id,
        )
    )
    if member is None:
        raise NotFoundError("Membership not found.")
    db.delete(member)
    db.commit()


# --- platform audit review (Phase 10) ----------------------------------------------

def audit_review(
    db: Session,
    actor_id: uuid.UUID,
    *,
    action: Optional[str] = None,
    action_prefix: Optional[str] = None,
    actor: Optional[uuid.UUID] = None,
    organization_id: Optional[uuid.UUID] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    result: Optional[str] = None,
    request_id: Optional[str] = None,
    from_ts: Optional[datetime] = None,
    to_ts: Optional[datetime] = None,
    page: int = 1,
    page_size: int = 25,
) -> dict:
    _require_platform(db, actor_id, PERMISSION_PLATFORM_AUDIT_READ)
    query = select(AuditLogEntry)
    if action:
        query = query.where(AuditLogEntry.action == action)
    if action_prefix:
        query = query.where(AuditLogEntry.action.like(f"{action_prefix}%"))
    if actor:
        query = query.where(AuditLogEntry.actor_id == actor)
    if organization_id:
        query = query.where(AuditLogEntry.organization_id == organization_id)
    if resource_type:
        query = query.where(AuditLogEntry.resource_type == resource_type)
    if resource_id:
        query = query.where(AuditLogEntry.resource_id == str(resource_id)[:64])
    if result:
        query = query.where(AuditLogEntry.result == result)
    if request_id:
        query = query.where(AuditLogEntry.request_id == request_id)
    if from_ts:
        query = query.where(AuditLogEntry.created_at >= from_ts)
    if to_ts:
        query = query.where(AuditLogEntry.created_at <= to_ts)

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(
        query.order_by(AuditLogEntry.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    items = []
    for row in rows:
        actor_user = db.get(User, row.actor_id) if row.actor_id else None
        items.append(
            {
                "id": str(row.id),
                "action": row.action,
                "actor_id": str(row.actor_id) if row.actor_id else None,
                "actor_name": actor_user.full_name if actor_user else None,
                "resource_type": row.resource_type,
                "resource_id": row.resource_id,
                "organization_id": (
                    str(row.organization_id) if row.organization_id else None
                ),
                "result": row.result,
                "request_id": row.request_id,
                "created_at": row.created_at,
                "payload": _sanitize_payload(row.payload),
            }
        )
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


# --- integrity signals (Phase 10) ----------------------------------------------------

def compute_integrity_signals(db: Session, actor_id: uuid.UUID) -> list:
    """Deterministic, neutral activity signals computed from existing data.

    Signals mark REVIEW_REQUIRED / ACTIVITY_PATTERN only. They are never
    stored and never label a subject as fraudulent/deceptive/malicious —
    that remains a human finding recorded in a case resolution.
    """
    _require_platform(db, actor_id, PERMISSION_REPORTS_READ)
    now = utc_now_naive()
    cutoff_7d = now - timedelta(days=7)
    cutoff_30d = now - timedelta(days=30)
    signals: List[dict] = []

    # 1. Repeated reports by one reporter within 7 days.
    for reporter_id, count in db.execute(
        select(GovernanceReport.reporter_user_id, func.count())
        .where(GovernanceReport.created_at >= cutoff_7d)
        .group_by(GovernanceReport.reporter_user_id)
        .having(func.count() >= 5)
    ).all():
        signals.append(
            {
                "signal_type": "repeated_reports",
                "subject_type": "user",
                "subject_id": str(reporter_id),
                "count": int(count),
                "window_days": 7,
                "status": SIGNAL_STATUS_REVIEW_REQUIRED,
                "note": (
                    "Activity pattern — a high volume of reports from this "
                    "reporter within 7 days. Review required; not proof of "
                    "misconduct."
                ),
            }
        )

    # 2. Repeated outreach volume by one organization within 7 days.
    for org_id, count in db.execute(
        select(OutreachRequest.organization_id, func.count())
        .where(OutreachRequest.created_at >= cutoff_7d)
        .group_by(OutreachRequest.organization_id)
        .having(func.count() >= 25)
    ).all():
        org = db.get(Organization, org_id) if org_id else None
        signals.append(
            {
                "signal_type": "repeated_outreach",
                "subject_type": "organization",
                "subject_id": str(org_id),
                "subject_name": org.name if org else None,
                "count": int(count),
                "window_days": 7,
                "status": SIGNAL_STATUS_ACTIVITY_PATTERN,
                "note": (
                    "Activity pattern — high outreach volume within 7 days. "
                    "Review required; not proof of misconduct."
                ),
            }
        )

    # 3. Organizations frequently blocked by candidates within 30 days.
    for org_id, count in db.execute(
        select(OutreachBlock.organization_id, func.count())
        .where(OutreachBlock.created_at >= cutoff_30d)
        .group_by(OutreachBlock.organization_id)
        .having(func.count() >= 10)
    ).all():
        org = db.get(Organization, org_id) if org_id else None
        signals.append(
            {
                "signal_type": "repeated_blocks_received",
                "subject_type": "organization",
                "subject_id": str(org_id),
                "subject_name": org.name if org else None,
                "count": int(count),
                "window_days": 30,
                "status": SIGNAL_STATUS_POLICY_SIGNAL,
                "note": (
                    "Policy signal — many candidates blocked this "
                    "organization within 30 days. Review required; not proof "
                    "of misconduct."
                ),
            }
        )

    signals.sort(key=lambda s: (-s["count"], s["signal_type"]))
    return signals
