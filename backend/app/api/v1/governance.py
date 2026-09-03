"""/api/v1/governance — the Platform Governance API (Phase 9).

Boundaries enforced here:

- FILING a report is open to any authenticated user (candidate, company,
  recruiter, government analyst...). The report references platform objects;
  it never carries private Work ID data or document contents.
- READING/MODIFYING the queue requires a PLATFORM-scope role with the
  specific ``reports.*`` permission. Employer, recruiter, candidate and
  government memberships can never satisfy it (``has_platform_permission``
  only counts memberships inside platform-kind organizations).
- Report detail returns the report + internal notes + audit history — never
  the target's private Work ID sections (least privilege).
- Every governance action is audited.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.errors import NotFoundError
from app.db.session import get_db
from app.models.audit import AuditLogEntry
from app.models.enums import (
    NOTIFICATION_KIND_GOVERNANCE,
    PERMISSION_REPORTS_READ,
    REPORT_CATEGORIES,
    REPORT_PRIORITIES,
    REPORT_SEVERITIES,
    REPORT_STATUSES,
    SLA_STATES,
)
from app.models.governance import GovernanceReport
from app.models.identity import User
from app.models.tenancy import Membership, Organization
from app.schemas.common import MessageResponse
from app.schemas.governance import (
    CaseLinkCreate,
    EscalateRequest,
    GovernanceDashboardOut,
    ReportAssign,
    ReportCreate,
    ReportListOut,
    ReportNoteCreate,
    ReportOut,
    ReportPriorityUpdate,
    ReportResolve,
    ReportStatusUpdate,
    ReportTeamUpdate,
    TeamMemberAdd,
)
from app.services import audit as audit_service
from app.services import events as events_service
from app.services import governance as governance_service
from app.services import notifications as notifications_service
from app.services.governance import sla_state_for

router = APIRouter(prefix="/governance", tags=["governance"])


def _emit_governance_event(
    db: Session,
    *,
    event_type: str,
    resource_type: str,
    resource_id,
    actor_user_id: uuid.UUID,
    payload: Optional[dict] = None,
) -> None:
    """Emit a governance event to the actor's platform org (org-scope) or,
    when the actor holds no platform membership, to the actor directly.
    Events carry metadata only — never descriptions or case content."""
    org_id = db.scalar(
        select(Membership.organization_id)
        .join(Organization, Organization.id == Membership.organization_id)
        .where(
            Membership.user_id == actor_user_id,
            Organization.kind == "platform",
        )
        .limit(1)
    )
    events_service.emit(
        db,
        event_type=event_type,
        resource_type=resource_type,
        resource_id=resource_id,
        organization_id=org_id,
        org_scope=org_id is not None,
        recipient_user_id=None if org_id else actor_user_id,
        actor_user_id=actor_user_id,
        payload=payload,
    )


def _notify_moderator(
    db: Session, user_id: uuid.UUID, title: str, message: str
) -> None:
    user = db.get(User, user_id)
    if user is None:
        return
    notifications_service.notify(
        db, user_id, title, message, kind=NOTIFICATION_KIND_GOVERNANCE
    )


def _audit(
    db: Session,
    actor_id: uuid.UUID,
    action: str,
    resource_id,
    organization_id=None,
    metadata: Optional[dict] = None,
) -> None:
    audit_service.record(
        db,
        actor_id=actor_id,
        action=action,
        resource_type="governance_report",
        resource_id=resource_id,
        organization_id=organization_id,
        metadata=metadata,
    )

router = APIRouter(prefix="/governance", tags=["governance"])


@router.post("/reports", response_model=ReportOut, status_code=201)
def file_report(
    body: ReportCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Any authenticated user may file a report (references only)."""
    report = governance_service.create_report(
        db,
        user.id,
        target_type=body.target_type,
        target_id=body.target_id,
        category=body.category,
        description=body.description,
        organization_id=body.organization_id,
        severity=body.severity,
        evidence_refs=body.evidence_refs,
    )
    audit_service.record(
        db,
        actor_id=user.id,
        action="governance.report.created",
        resource_type="governance_report",
        resource_id=report.id,
        organization_id=report.organization_id,
        metadata={
            "target_type": report.target_type,
            "category": report.category,
            "severity": report.severity,
        },
    )
    _emit_governance_event(
        db,
        event_type="governance.case.created",
        resource_type="governance_report",
        resource_id=report.id,
        actor_user_id=user.id,
        payload={"category": report.category, "severity": report.severity},
    )
    db.commit()
    return governance_service.report_out(db, report)


@router.get("/reports", response_model=ReportListOut)
def list_reports(
    status: Optional[str] = Query(None, max_length=20),
    severity: Optional[str] = Query(None, max_length=16),
    priority: Optional[str] = Query(None, max_length=16),
    category: Optional[str] = Query(None, max_length=40),
    team_id: Optional[uuid.UUID] = None,
    assigned_to: Optional[uuid.UUID] = None,
    unassigned: bool = False,
    mine: bool = False,
    escalated: bool = False,
    sla: Optional[str] = Query(None, max_length=12),
    organization_id: Optional[uuid.UUID] = None,
    sort: str = Query("created_at", max_length=20),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Platform governance case queue (moderator/super-admin only)."""
    return governance_service.list_reports(
        db,
        user.id,
        status=status,
        severity=severity,
        priority=priority,
        category=category,
        team_id=team_id,
        assigned_to=assigned_to,
        unassigned=unassigned,
        mine=mine,
        escalated=escalated,
        sla=sla,
        organization_id=organization_id,
        sort=sort,
        page=page,
        page_size=page_size,
    )


@router.get("/reports/{report_id}", response_model=ReportOut)
def get_report(
    report_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Report detail: fields + internal notes + audit history. Never the
    target's private Work ID sections (least privilege)."""
    payload = governance_service.get_report(db, user.id, report_id)
    audit_rows = db.scalars(
        select(AuditLogEntry)
        .where(
            AuditLogEntry.resource_type == "governance_report",
            AuditLogEntry.resource_id == str(report_id),
        )
        .order_by(AuditLogEntry.created_at.desc())
        .limit(50)
    ).all()
    payload["audit"] = [
        {
            "action": row.action,
            "actor_id": str(row.actor_id) if row.actor_id else None,
            "result": row.result,
            "created_at": row.created_at,
            "payload": row.payload or {},
        }
        for row in audit_rows
    ]
    return payload


@router.patch("/reports/{report_id}/status", response_model=ReportOut)
def update_report_status(
    report_id: uuid.UUID,
    body: ReportStatusUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    report = governance_service.update_status(db, user.id, report_id, body.status)
    audit_service.record(
        db,
        actor_id=user.id,
        action="governance.report.status_changed",
        resource_type="governance_report",
        resource_id=report.id,
        metadata={"to_status": body.status},
    )
    db.commit()
    return governance_service.report_out(db, report)


@router.post("/reports/{report_id}/assign", response_model=ReportOut)
def assign_report(
    report_id: uuid.UUID,
    body: ReportAssign,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    report = governance_service.assign_report(
        db, user.id, report_id, moderator_user_id=body.moderator_user_id
    )
    assignee_id = report.assigned_moderator_id
    audit_service.record(
        db,
        actor_id=user.id,
        action="governance.report.assigned",
        resource_type="governance_report",
        resource_id=report.id,
        metadata={"to_user_id": str(assignee_id)},
    )
    if assignee_id and assignee_id != user.id:
        _notify_moderator(
            db,
            assignee_id,
            "A governance case was assigned to you",
            "Open the case in the platform control room to review it. "
            "No case content is included in this notification.",
        )
    _emit_governance_event(
        db,
        event_type="governance.case.assigned",
        resource_type="governance_report",
        resource_id=report.id,
        actor_user_id=user.id,
        payload={"to_user_id": str(assignee_id)},
    )
    db.commit()
    return governance_service.report_out(db, report)


@router.post("/reports/{report_id}/notes", response_model=dict, status_code=201)
def add_report_note(
    report_id: uuid.UUID,
    body: ReportNoteCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    note = governance_service.add_note(db, user.id, report_id, body.body)
    audit_service.record(
        db,
        actor_id=user.id,
        action="governance.report.note_added",
        resource_type="governance_report",
        resource_id=report_id,
        metadata={"note_id": str(note.id)},
    )
    db.commit()
    return {
        "id": str(note.id),
        "report_id": str(note.report_id),
        "author_user_id": str(note.author_user_id),
        "body": note.body,
        "created_at": note.created_at,
    }


@router.post("/reports/{report_id}/resolve", response_model=ReportOut)
def resolve_report(
    report_id: uuid.UUID,
    body: ReportResolve,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    report = governance_service.resolve_report(db, user.id, report_id, body.resolution)
    audit_service.record(
        db,
        actor_id=user.id,
        action="governance.report.resolved",
        resource_type="governance_report",
        resource_id=report.id,
        metadata={"resolution_present": bool(body.resolution)},
    )
    _emit_governance_event(
        db,
        event_type="governance.case.resolved",
        resource_type="governance_report",
        resource_id=report.id,
        actor_user_id=user.id,
        payload={"resolution_present": bool(body.resolution)},
    )
    db.commit()
    return governance_service.report_out(db, report)


@router.post("/reports/{report_id}/reopen", response_model=ReportOut)
def reopen_report(
    report_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    report = governance_service.reopen_report(db, user.id, report_id)
    audit_service.record(
        db,
        actor_id=user.id,
        action="governance.report.reopened",
        resource_type="governance_report",
        resource_id=report.id,
        metadata={"reopened_count": report.reopened_count},
    )
    _emit_governance_event(
        db,
        event_type="governance.case.reopened",
        resource_type="governance_report",
        resource_id=report.id,
        actor_user_id=user.id,
        payload={"reopened_count": report.reopened_count},
    )
    db.commit()
    return governance_service.report_out(db, report)


@router.get("/dashboard", response_model=GovernanceDashboardOut)
def governance_dashboard(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    return governance_service.governance_dashboard(db, user.id)


# --- Phase 10: operational case actions ------------------------------------------

@router.post("/reports/{report_id}/priority", response_model=ReportOut)
def change_report_priority(
    report_id: uuid.UUID,
    body: ReportPriorityUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    existing = db.get(GovernanceReport, report_id)
    from_priority = existing.priority if existing is not None else None
    report = governance_service.change_priority(
        db, user.id, report_id, body.priority
    )
    audit_service.record(
        db,
        actor_id=user.id,
        action="governance.report.priority_changed",
        resource_type="governance_report",
        resource_id=report.id,
        metadata={
            "from_priority": from_priority,
            "to_priority": report.priority,
        },
    )
    _emit_governance_event(
        db,
        event_type="governance.case.priority_changed",
        resource_type="governance_report",
        resource_id=report.id,
        actor_user_id=user.id,
        payload={"from_priority": from_priority, "to_priority": report.priority},
    )
    db.commit()
    return governance_service.report_out(db, report)


@router.post("/reports/{report_id}/team", response_model=ReportOut)
def set_report_team(
    report_id: uuid.UUID,
    body: ReportTeamUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    report = governance_service.set_case_team(db, user.id, report_id, body.team_id)
    audit_service.record(
        db,
        actor_id=user.id,
        action="governance.report.team_changed",
        resource_type="governance_report",
        resource_id=report.id,
        metadata={
            "to_team_id": str(report.team_id) if report.team_id else None
        },
    )
    db.commit()
    return governance_service.report_out(db, report)


@router.post("/reports/{report_id}/escalate", response_model=ReportOut)
def escalate_report(
    report_id: uuid.UUID,
    body: EscalateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    report = governance_service.escalate_case(
        db,
        user.id,
        report_id,
        reason=body.reason,
        to_priority=body.priority,
        to_severity=body.severity,
        to_team_id=body.team_id,
    )
    # Audit metadata records the escalation context — never the reason body
    # itself (reference-only audit convention).
    audit_service.record(
        db,
        actor_id=user.id,
        action="governance.report.escalated",
        resource_type="governance_report",
        resource_id=report.id,
        metadata={
            "to_priority": report.priority,
            "to_severity": report.severity,
            "to_team_id": str(report.escalated_to_team_id)
            if report.escalated_to_team_id
            else None,
            "reason_present": bool(body.reason),
        },
    )
    if report.assigned_moderator_id and report.assigned_moderator_id != user.id:
        _notify_moderator(
            db,
            report.assigned_moderator_id,
            "A case you own was escalated",
            "Open the case in the platform control room. No case content is "
            "included in this notification.",
        )
    _emit_governance_event(
        db,
        event_type="governance.case.escalated",
        resource_type="governance_report",
        resource_id=report.id,
        actor_user_id=user.id,
        payload={"to_priority": report.priority},
    )
    db.commit()
    return governance_service.report_out(db, report)


@router.post("/reports/{report_id}/links", response_model=dict, status_code=201)
def link_report_to_case(
    report_id: uuid.UUID,
    body: CaseLinkCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    link = governance_service.link_report(
        db, user.id, report_id, body.report_id, reason=body.reason
    )
    audit_service.record(
        db,
        actor_id=user.id,
        action="governance.report.linked",
        resource_type="governance_report",
        resource_id=report_id,
        metadata={"linked_report_id": str(link.linked_report_id)},
    )
    db.commit()
    return {"id": str(link.id), "linked_report_id": str(link.linked_report_id)}


@router.delete("/reports/{report_id}/links/{link_id}", response_model=MessageResponse)
def unlink_report_from_case(
    report_id: uuid.UUID,
    link_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    governance_service.unlink_report(db, user.id, report_id, link_id)
    audit_service.record(
        db,
        actor_id=user.id,
        action="governance.report.unlinked",
        resource_type="governance_report",
        resource_id=report_id,
        metadata={"link_id": str(link_id)},
    )
    db.commit()
    return MessageResponse(message="Link removed.")


# --- Phase 10: teams + moderators --------------------------------------------------

@router.get("/teams", response_model=dict)
def list_governance_teams(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    return governance_service.list_teams(db, user.id)


@router.get("/teams/{team_id}", response_model=dict)
def get_governance_team(
    team_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    return governance_service.get_team(db, user.id, team_id)


@router.post("/teams/{team_id}/members", response_model=dict, status_code=201)
def add_team_member(
    team_id: uuid.UUID,
    body: TeamMemberAdd,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    member = governance_service.add_team_member(
        db, user.id, team_id, body.user_id
    )
    audit_service.record(
        db,
        actor_id=user.id,
        action="governance.team.member_added",
        resource_type="governance_team",
        resource_id=team_id,
        metadata={"user_id": str(body.user_id)},
    )
    db.commit()
    return {"team_id": str(member.team_id), "user_id": str(member.user_id)}


@router.delete(
    "/teams/{team_id}/members/{user_id}", response_model=MessageResponse
)
def remove_team_member(
    team_id: uuid.UUID,
    user_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    governance_service.remove_team_member(db, user.id, team_id, user_id)
    audit_service.record(
        db,
        actor_id=user.id,
        action="governance.team.member_removed",
        resource_type="governance_team",
        resource_id=team_id,
        metadata={"user_id": str(user_id)},
    )
    db.commit()
    return MessageResponse(message="Member removed.")


@router.get("/moderators", response_model=dict)
def list_moderators(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    items = governance_service.list_moderators(db, user.id)
    return {"items": items, "total": len(items)}


# --- Phase 10: platform audit review -----------------------------------------------

@router.get("/audit", response_model=dict)
def audit_review(
    action: Optional[str] = Query(None, max_length=120),
    action_prefix: Optional[str] = Query(None, max_length=120),
    actor: Optional[uuid.UUID] = None,
    organization_id: Optional[uuid.UUID] = None,
    resource_type: Optional[str] = Query(None, max_length=80),
    resource_id: Optional[str] = Query(None, max_length=64),
    result: Optional[str] = Query(None, max_length=20),
    request_id: Optional[str] = Query(None, max_length=40),
    from_ts: Optional[datetime] = Query(None),
    to_ts: Optional[datetime] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    return governance_service.audit_review(
        db,
        user.id,
        action=action,
        action_prefix=action_prefix,
        actor=actor,
        organization_id=organization_id,
        resource_type=resource_type,
        resource_id=resource_id,
        result=result,
        request_id=request_id,
        from_ts=from_ts,
        to_ts=to_ts,
        page=page,
        page_size=page_size,
    )


# --- Phase 10: integrity signals ------------------------------------------------------

@router.get("/signals", response_model=dict)
def integrity_signals(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    items = governance_service.compute_integrity_signals(db, user.id)
    return {"items": items, "count": len(items)}