"""Company Employment OS — employer-side service operations (Phase 6).

Single-authority rules:
- Jobs: the only lifecycle writer. Publishing a job creates/updates ONE
  canonical Opportunity (the same catalogue jobseekers discover in Phase 5).
- Applications: all status changes go through the shared Phase 5 state
  machine (``applications.transition_to_status``). The employer advances the
  pipeline; the jobseeker applies/withdraws. One lifecycle, two sides.
- Offers: created here, decided by the candidate through the jobseeker Offer
  Center; acceptance flows back into the shared application state machine.
- Candidate data: employers see only minimum necessary, stage-appropriate
  information. Additional Work ID sections require explicit consent (Phase 4
  consent layer) and document access goes through requests -> grants.
- Every decision/transition is audited via the caller's route handlers.
"""
from __future__ import annotations

import uuid
from typing import Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import (
    ConflictError,
    InvalidInputError,
    NotFoundError,
    PermissionDeniedError,
)
from app.core.timeutil import utc_now_naive
from app.models.career import (
    ApplicationEvent,
    CareerGoal,
    Interview,
    JobApplication,
    Offer,
    Opportunity,
    UserNotification,
)
from app.models.company import (
    CompanyProfile,
    DocumentRequest,
    JobPosting,
)
from app.models.enums import (
    APPLICATION_STATUS_ACCEPTED,
    APPLICATION_STATUS_APPLICATION_RECEIVED,
    APPLICATION_STATUS_ASSESSMENT,
    APPLICATION_STATUS_INTERVIEW,
    APPLICATION_STATUS_OFFER,
    APPLICATION_STATUS_REJECTED,
    APPLICATION_STATUS_SCREENING,
    APPLICATION_STATUS_WITHDRAWN,
    DOC_REQUEST_STATUSES,
    JOB_STATUS_ARCHIVED,
    JOB_STATUS_CLOSED,
    JOB_STATUS_DRAFT,
    JOB_STATUS_PAUSED,
    JOB_STATUS_PENDING_REVIEW,
    JOB_STATUS_PUBLISHED,
    JOB_STATUSES,
    OFFER_STATUSES,
)
from app.models.identity import PersonProfile, User
from app.models.tenancy import Organization
from app.models.work import Skill, UserSkill
from app.services import audit as audit_service
from app.services import consent as consent_service
from app.services import notifications as notifications_service
from app.services.applications import transition_to_status
from app.services.auth_service import get_person_for_user

# Declarative transition table: current -> allowed employer outcomes.
# (The jobseeker self-service side of the same machine allows apply/withdraw.)
EMPLOYER_TRANSITIONS: Dict[str, set] = {
    "applied": {
        "application_received",
        "screening",
        "assessment",
        "rejected",
    },
    "application_received": {"screening", "assessment", "rejected"},
    "screening": {"assessment", "interview", "rejected", "on_hold"},
    "assessment": {"interview", "rejected", "on_hold"},
    "interview": {"offer", "rejected", "on_hold"},
    "on_hold": {"screening", "assessment", "interview", "offer", "rejected"},
}

# Decision actions exposed to recruiters -> mapped to statuses.
DECISION_ACTIONS = {
    "advance": {
        "applied": "application_received",
        "application_received": "screening",
        "screening": "assessment",
        "assessment": "interview",
        "interview": "offer",
        "on_hold": "interview",
    },
    "hold": {"screening": "on_hold", "assessment": "on_hold", "interview": "on_hold"},
    "reject": {},
}

# Application statuses a company considers "needs review".
REVIEW_STATUSES = {
    "applied",
    "application_received",
    "screening",
    "assessment",
    "on_hold",
}


# --- helpers -----------------------------------------------------------------


def slugify_title(title: str) -> str:
    return (
        title.lower()
        .strip()
        .replace(" ", "-")
        .replace("/", "-")
        .replace("&", "and")
    )


def _require_member(db: Session, organization_id: uuid.UUID, actor_id: uuid.UUID) -> None:
    """Non-members receive 403 (denied), not 404, for org-scoped operations.
    Existence of another org's rows is still hidden once membership is proven."""
    from app.services import authz

    if not authz.get_org_membership(db, actor_id, organization_id):
        raise PermissionDeniedError("You are not a member of this organization.")


def _job_owned(
    db: Session,
    organization_id: uuid.UUID,
    job_id: uuid.UUID,
    actor_id: Optional[uuid.UUID] = None,
) -> JobPosting:
    if actor_id is not None:
        _require_member(db, organization_id, actor_id)
    job = db.get(JobPosting, job_id)
    if job is None or job.organization_id != organization_id:
        raise NotFoundError("Job not found.")
    return job


def _application_owned(
    db: Session,
    organization_id: uuid.UUID,
    application_id: uuid.UUID,
    actor_id: Optional[uuid.UUID] = None,
) -> JobApplication:
    """Application belongs to this org when its opportunity is a job we own
    (or the application is linked to one of our job postings)."""
    if actor_id is not None:
        _require_member(db, organization_id, actor_id)
    app = db.get(JobApplication, application_id)
    if app is None:
        raise NotFoundError("Application not found.")
    if app.job_id is not None:
        job = db.get(JobPosting, app.job_id)
        if job is not None and job.organization_id == organization_id:
            return app
    # Fall back through the opportunity's company link.
    if app.opportunity_id is not None:
        opp = db.get(Opportunity, app.opportunity_id)
        if opp is not None and opp.company_id == organization_id:
            return app
    raise NotFoundError("Application not found.")


# --- jobs ---------------------------------------------------------------------


def create_job(
    db: Session,
    organization_id: uuid.UUID,
    actor_id: uuid.UUID,
    *,
    title: str,
    summary: Optional[str] = None,
    description: Optional[str] = None,
    department: Optional[str] = None,
    requirements: Optional[list] = None,
    skills_required: Optional[list] = None,
    preferred_skills: Optional[list] = None,
    experience_level: Optional[str] = None,
    location: Optional[str] = None,
    country: Optional[str] = None,
    city: Optional[str] = None,
    remote_eligible: bool = False,
    work_mode: Optional[str] = None,
    employment_type: Optional[str] = None,
    salary_min: Optional[float] = None,
    salary_max: Optional[float] = None,
    salary_currency: Optional[str] = "USD",
    seniority: Optional[str] = None,
    industry: Optional[str] = None,
    openings_count: int = 1,
    application_deadline=None,
    screening_questions: Optional[list] = None,
) -> JobPosting:
    slug = slugify_title(title)
    if db.scalar(
        select(JobPosting.id).where(
            JobPosting.organization_id == organization_id, JobPosting.slug == slug
        )
    ):
        slug = f"{slug}-{uuid.uuid4().hex[:6]}"
    job = JobPosting(
        organization_id=organization_id,
        title=title,
        slug=slug,
        summary=summary,
        description=description,
        department=department,
        requirements=requirements,
        skills_required=skills_required,
        preferred_skills=preferred_skills,
        experience_level=experience_level,
        location=location,
        country=country,
        city=city,
        remote_eligible=remote_eligible,
        work_mode=work_mode,
        employment_type=employment_type,
        salary_min=salary_min,
        salary_max=salary_max,
        salary_currency=salary_currency,
        seniority=seniority,
        industry=industry,
        openings_count=max(1, openings_count),
        application_deadline=application_deadline,
        screening_questions=screening_questions,
        status=JOB_STATUS_DRAFT,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def update_job(
    db: Session,
    organization_id: uuid.UUID,
    job_id: uuid.UUID,
    actor_id: uuid.UUID,
    values: dict,
) -> JobPosting:
    job = _job_owned(db, organization_id, job_id)
    editable = {
        "title", "summary", "description", "department", "requirements",
        "skills_required", "preferred_skills", "experience_level", "location",
        "country", "city", "remote_eligible", "work_mode", "employment_type",
        "salary_min", "salary_max", "salary_currency", "seniority", "industry",
        "openings_count", "application_deadline", "screening_questions",
    }
    unknown = set(values) - editable
    if unknown:
        raise InvalidInputError(f"Cannot edit fields: {sorted(unknown)}")
    for key, value in values.items():
        if key == "title" and value:
            job.title = value
            job.slug = slugify_title(value)
        elif value is not None:
            setattr(job, key, value)
    if job.status == JOB_STATUS_PUBLISHED:
        _sync_opportunity(db, job)
    db.commit()
    db.refresh(job)
    return job


def publish_job(db: Session, organization_id: uuid.UUID, job_id: uuid.UUID) -> JobPosting:
    job = _job_owned(db, organization_id, job_id)
    if job.status in {JOB_STATUS_PUBLISHED, JOB_STATUS_CLOSED, JOB_STATUS_ARCHIVED}:
        raise InvalidInputError(
            f"A job with status '{job.status}' cannot be published."
        )
    job.status = JOB_STATUS_PUBLISHED
    job.published_at = utc_now_naive()
    _sync_opportunity(db, job)
    db.commit()
    db.refresh(job)
    return job


def pause_job(db: Session, organization_id: uuid.UUID, job_id: uuid.UUID) -> JobPosting:
    job = _job_owned(db, organization_id, job_id)
    if job.status != JOB_STATUS_PUBLISHED:
        raise InvalidInputError("Only published jobs can be paused.")
    job.status = JOB_STATUS_PAUSED
    if job.opportunity_id:
        opp = db.get(Opportunity, job.opportunity_id)
        if opp is not None:
            opp.status = "paused"
    db.commit()
    db.refresh(job)
    return job


def close_job(db: Session, organization_id: uuid.UUID, job_id: uuid.UUID) -> JobPosting:
    job = _job_owned(db, organization_id, job_id)
    if job.status in {JOB_STATUS_CLOSED, JOB_STATUS_ARCHIVED}:
        raise InvalidInputError("This job is already closed.")
    job.status = JOB_STATUS_CLOSED
    job.closed_at = utc_now_naive()
    if job.opportunity_id:
        opp = db.get(Opportunity, job.opportunity_id)
        if opp is not None:
            opp.status = "closed"
    db.commit()
    db.refresh(job)
    return job


def _sync_opportunity(db: Session, job: JobPosting) -> Opportunity:
    """Map this published job into ONE canonical Opportunity (never a second
    universe). Idempotent: re-publishing updates the same opportunity row."""
    org = db.get(Organization, job.organization_id)
    company_name = org.name if org else job.organization_id.__str__()
    if job.opportunity_id:
        opp = db.get(Opportunity, job.opportunity_id)
        if opp is not None:
            _apply_job_to_opportunity(opp, job, company_name)
            db.commit()
            return opp
    opp = Opportunity(
        company_id=job.organization_id,
        company_name=company_name,
        title=job.title,
        slug=job.slug,
        summary=job.summary,
        description=job.description,
        location=job.location,
        country=job.country,
        city=job.city,
        remote_eligible=job.remote_eligible,
        work_mode=job.work_mode,
        employment_type=job.employment_type,
        experience_level=job.experience_level,
        seniority=job.seniority,
        industry=job.industry,
        skills_required=job.skills_required,
        min_salary=job.salary_min,
        max_salary=job.salary_max,
        salary_currency=job.salary_currency,
        source="platform",
        imported_from=f"job:{job.id}",
        status="active",
        is_approved=True,
    )
    db.add(opp)
    db.flush()
    job.opportunity_id = opp.id
    db.commit()
    db.refresh(opp)
    return opp


def _apply_job_to_opportunity(
    opp: Opportunity, job: JobPosting, company_name: str
) -> None:
    opp.company_id = job.organization_id
    opp.company_name = company_name
    opp.title = job.title
    opp.slug = job.slug
    opp.summary = job.summary
    opp.description = job.description
    opp.location = job.location
    opp.country = job.country
    opp.city = job.city
    opp.remote_eligible = job.remote_eligible
    opp.work_mode = job.work_mode
    opp.employment_type = job.employment_type
    opp.experience_level = job.experience_level
    opp.seniority = job.seniority
    opp.industry = job.industry
    opp.skills_required = job.skills_required
    opp.min_salary = job.salary_min
    opp.max_salary = job.salary_max
    opp.salary_currency = job.salary_currency


def list_org_jobs(
    db: Session, organization_id: uuid.UUID, status: Optional[str] = None
) -> list:
    query = select(JobPosting).where(JobPosting.organization_id == organization_id)
    if status:
        if status not in JOB_STATUSES:
            raise InvalidInputError(f"Unknown job status '{status}'.")
        query = query.where(JobPosting.status == status)
    return db.scalars(
        query.order_by(JobPosting.created_at.desc())
    ).all()


# --- pipeline -----------------------------------------------------------------


def org_opportunity_ids(db: Session, organization_id: uuid.UUID) -> List[uuid.UUID]:
    return list(
        db.scalars(
            select(Opportunity.id).where(Opportunity.company_id == organization_id)
        ).all()
    )


def list_org_applications(
    db: Session,
    organization_id: uuid.UUID,
    job_id: Optional[uuid.UUID] = None,
    status: Optional[str] = None,
) -> list:
    query = (
        select(JobApplication)
        .where(
            JobApplication.opportunity_id.in_(
                org_opportunity_ids(db, organization_id) or [uuid.uuid4()]
            )
        )
        .order_by(JobApplication.last_activity_at.desc())
    )
    if job_id:
        _job_owned(db, organization_id, job_id)
        query = query.where(
            (JobApplication.job_id == job_id)
            | (
                JobApplication.job_id.is_(None)
                & (
                    JobApplication.opportunity_id.in_(
                        select(Opportunity.id).where(
                            Opportunity.company_id == organization_id,
                            Opportunity.id.in_(
                                select(JobPosting.opportunity_id).where(
                                    JobPosting.id == job_id
                                )
                            ),
                        )
                    )
                )
            )
        )
    if status:
        query = query.where(JobApplication.status == status)
    return db.scalars(query).all()


def decision(
    db: Session,
    organization_id: uuid.UUID,
    application_id: uuid.UUID,
    actor_id: uuid.UUID,
    action: str,
    note: Optional[str] = None,
) -> JobApplication:
    """Explicit, audited hiring decision. One authoritative state machine.

    ``advance`` moves one stage; ``hold`` and ``reject`` move to their fixed
    outcomes. Rejecting records the rejection on the application; advancing
    from interview moves toward offer (offer creation is a separate explicit
    action guarded by offers.create).
    """
    app = _application_owned(db, organization_id, application_id, actor_id=actor_id)
    if action == "advance":
        target = DECISION_ACTIONS["advance"].get(app.status)
        if target is None:
            raise InvalidInputError(
                f"Cannot advance an application in status '{app.status}'."
            )
        if target == "offer":
            # Offer is created explicitly (offers.create); advancing past
            # interview only flags intent — the offer row is the real signal.
            app.status = APPLICATION_STATUS_OFFER
            db.commit()
            db.refresh(app)
            return app
        return transition_to_status(
            db, app, target, actor_user_id=actor_id, note=note or f"Advanced: {action}"
        )
    if action == "hold":
        if app.status not in EMPLOYER_TRANSITIONS or "on_hold" not in EMPLOYER_TRANSITIONS[app.status]:
            raise InvalidInputError(f"Cannot hold an application in '{app.status}'.")
        return transition_to_status(
            db, app, "on_hold", actor_user_id=actor_id, note=note or "Placed on hold"
        )
    if action == "reject":
        return transition_to_status(
            db, app, APPLICATION_STATUS_REJECTED, actor_user_id=actor_id,
            note=note or "Rejected",
        )
    raise InvalidInputError(f"Unknown decision action '{action}'.")


def _candidate_person(db: Session, application: JobApplication) -> Optional[PersonProfile]:
    return get_person_for_user(db, _candidate_user_id(db, application))


def _candidate_user_id(db: Session, application: JobApplication):
    # The person who owns the application: resolve via person_profiles.
    row = db.execute(
        select(PersonProfile.user_id).where(
            PersonProfile.id == application.person_id
        )
    ).first()
    return row[0] if row else None


def candidate_summary(
    db: Session,
    organization_id: uuid.UUID,
    application: JobApplication,
    viewer_user_id: uuid.UUID,
) -> Dict:
    """Minimum-necessary candidate view for a review context.

    Progressive disclosure: profile identity + headline + skills are shown
    because the person applied to the company's job (implied interest).
    Contact details are NEVER exposed here. Education/employment/credentials
    are only included per explicit visibility or a live consent from the
    candidate for this organization (Phase 4 consent scope).
    """
    from app.services.person import get_visibility_map

    person = get_person_for_user(db, _candidate_user_id(db, application))
    if person is None:
        return {"summary": {}, "reason": "Candidate profile unavailable."}
    visibility = get_visibility_map(db, person.id)
    live_consent = _has_live_consent(db, person.id, organization_id)

    skills = db.execute(
        select(UserSkill, Skill)
        .join(Skill, Skill.id == UserSkill.skill_id)
        .where(UserSkill.person_id == person.id)
    ).all()
    skills_out = [
        {
            "name": skill.name,
            "level": us.level,
            "years_experience": us.years_experience,
        }
        for us, skill in skills
    ]

    def _include(scope: str) -> bool:
        value = visibility.get(scope, "private")
        return value in {"public", "authorized_only"} and bool(live_consent or value == "public")

    return {
        "person": {
            "full_name": _candidate_display_name(db, person),
            "headline": person.headline,
            "location": person.location if _include("profile") else None,
        },
        "skills": skills_out[:12],
        "has_live_consent": bool(live_consent),
        "disclosure": {
            "contact_visible": False,
            "education_visible": _include("education"),
            "experience_visible": _include("experience"),
            "documents_visible": _include("documents"),
        },
        "application_events_count": _event_count(db, application.id),
        "events": _recent_events(db, application.id),
    }


def _recent_events(db: Session, application_id: uuid.UUID) -> list:
    events = db.scalars(
        select(ApplicationEvent)
        .where(ApplicationEvent.application_id == application_id)
        .order_by(ApplicationEvent.created_at.desc())
        .limit(10)
    ).all()
    return [
        {
            "id": str(e.id),
            "from_status": e.from_status,
            "to_status": e.to_status,
            "note": e.note,
            "created_at": e.created_at,
        }
        for e in events
    ]


def _has_live_consent(db: Session, person_id: uuid.UUID, organization_id: uuid.UUID) -> bool:
    """Candidate has granted this organization access to profile sections."""
    from app.models.enums import (
        CONSENT_SCOPE_WORK_ID_PROFILE,
        CONSENT_SCOPE_WORK_ID_DOCUMENTS,
    )

    return consent_service.find_live_consent(
        db,
        person_id=person_id,
        resource_scope=CONSENT_SCOPE_WORK_ID_PROFILE,
        grantee_organization_ids=[organization_id],
    ) is not None or consent_service.find_live_consent(
        db,
        person_id=person_id,
        resource_scope=CONSENT_SCOPE_WORK_ID_DOCUMENTS,
        grantee_organization_ids=[organization_id],
    ) is not None


def _candidate_display_name(db: Session, person: PersonProfile) -> Optional[str]:
    user = db.get(User, person.user_id)
    if user and person.preferred_name:
        return person.preferred_name
    return user.full_name if user else None


def _event_count(db: Session, application_id: uuid.UUID) -> int:
    return len(
        db.scalars(
            select(ApplicationEvent.id).where(
                ApplicationEvent.application_id == application_id
            )
        ).all()
    )


# --- offers ------------------------------------------------------------------


def create_offer(
    db: Session,
    organization_id: uuid.UUID,
    application_id: uuid.UUID,
    actor_id: uuid.UUID,
    *,
    salary_amount: Optional[float] = None,
    salary_currency: Optional[str] = "USD",
    equity: Optional[str] = None,
    benefits_summary: Optional[str] = None,
    start_date=None,
    location: Optional[str] = None,
    terms_summary: Optional[str] = None,
    expires_days: int = 7,
) -> Offer:
    app = _application_owned(db, organization_id, application_id, actor_id=actor_id)
    if app.status in {APPLICATION_STATUS_REJECTED, APPLICATION_STATUS_WITHDRAWN}:
        raise InvalidInputError(
            f"Cannot offer to an application in status '{app.status}'."
        )
    existing = db.scalar(
        select(Offer).where(Offer.application_id == app.id)
    )
    if existing is not None:
        raise ConflictError("An offer already exists for this application.")
    from datetime import timedelta

    offer = Offer(
        application_id=app.id,
        status="draft",
        salary_amount=salary_amount,
        salary_currency=salary_currency,
        equity=equity,
        benefits_summary=benefits_summary,
        start_date=start_date,
        location=location,
        terms_summary=terms_summary,
        expires_at=utc_now_naive() + timedelta(days=expires_days),
    )
    db.add(offer)
    db.flush()
    if app.status in {"applied", "application_received", "screening", "assessment", "interview", "on_hold"}:
        app.status = APPLICATION_STATUS_OFFER
        app.last_activity_at = utc_now_naive()
        db.add(
            ApplicationEvent(
                application_id=app.id,
                from_status=app.status,
                to_status=APPLICATION_STATUS_OFFER,
                note="Offer created.",
                actor_user_id=actor_id,
            )
        )
    db.commit()
    db.refresh(offer)
    # Notify the candidate through their notification feed.
    user_id = _candidate_user_id(db, app)
    if user_id:
        notifications_service.notify(
            db, user_id, "You have received an offer",
            "An offer is waiting for your decision in your Offer Center.",
            kind="offer",
        )
    _emit_offer_event(db, app, offer, "offer.updated")
    return offer


def _emit_offer_event(db: Session, app: JobApplication, offer: Offer, event_type: str) -> None:
    """Minimal offer realtime event (status + references, no terms dump)."""
    from app.models.identity import PersonProfile
    from app.services import events as events_service

    person = db.get(PersonProfile, app.person_id)
    payload = {"status": offer.status}
    if person is not None:
        events_service.emit(
            db, event_type=event_type, resource_type="offer", resource_id=offer.id,
            recipient_user_id=person.user_id, payload=payload,
        )
    opp = db.get(Opportunity, app.opportunity_id)
    if opp is not None and opp.company_id is not None:
        events_service.emit(
            db, event_type=event_type, resource_type="offer", resource_id=offer.id,
            organization_id=opp.company_id, org_scope=True, payload=payload,
        )


def send_offer(
    db: Session, organization_id: uuid.UUID, offer_id: uuid.UUID, actor_id: uuid.UUID
) -> Offer:
    offer = _owned_offer(db, organization_id, offer_id, actor_id=actor_id)
    if offer.status != "draft":
        raise InvalidInputError(f"Cannot send an offer with status '{offer.status}'.")
    offer.status = "sent"
    app = db.get(JobApplication, offer.application_id)
    if app is not None:
        _emit_offer_event(db, app, offer, "offer.updated")
    db.commit()
    db.refresh(offer)
    return offer


def withdraw_offer(
    db: Session, organization_id: uuid.UUID, offer_id: uuid.UUID, actor_id: uuid.UUID
) -> Offer:
    offer = _owned_offer(db, organization_id, offer_id, actor_id=actor_id)
    if offer.status in {"accepted", "declined"}:
        raise InvalidInputError(f"Cannot withdraw a '{offer.status}' offer.")
    offer.status = "withdrawn"
    db.commit()
    db.refresh(offer)
    return offer


def _owned_offer(
    db: Session,
    organization_id: uuid.UUID,
    offer_id: uuid.UUID,
    actor_id: Optional[uuid.UUID] = None,
) -> Offer:
    offer = db.get(Offer, offer_id)
    if offer is None:
        raise NotFoundError("Offer not found.")
    app = db.get(JobApplication, offer.application_id)
    if app is None:
        raise NotFoundError("Offer not found.")
    _application_owned(db, organization_id, app.id, actor_id=actor_id)
    return offer


# --- interviews --------------------------------------------------------------


def create_interview(
    db: Session,
    organization_id: uuid.UUID,
    application_id: uuid.UUID,
    actor_id: uuid.UUID,
    *,
    scheduled_at,
    duration_minutes: int = 45,
    mode: str = "video",
    interviewer_name: Optional[str] = None,
    meeting_link: Optional[str] = None,
    notes: Optional[str] = None,
) -> Interview:
    app = _application_owned(db, organization_id, application_id, actor_id=actor_id)
    if app.status in {APPLICATION_STATUS_REJECTED, APPLICATION_STATUS_WITHDRAWN}:
        raise InvalidInputError(
            f"Cannot schedule an interview for status '{app.status}'."
        )
    interview = Interview(
        application_id=app.id,
        scheduled_at=scheduled_at,
        duration_minutes=duration_minutes,
        mode=mode,
        meeting_link=meeting_link,
        interviewer_name=interviewer_name,
        notes=notes,
        status="scheduled",
    )
    db.add(interview)
    if app.status not in {APPLICATION_STATUS_INTERVIEW, APPLICATION_STATUS_OFFER, "accepted"}:
        transition_to_status(
            db, app, APPLICATION_STATUS_INTERVIEW,
            actor_user_id=actor_id, note="Interview scheduled.",
        )
    else:
        db.commit()
    db.refresh(interview)
    user_id = _candidate_user_id(db, app)
    if user_id:
        notifications_service.notify(
            db, user_id, "Interview scheduled",
            "An interview has been scheduled for your application.",
            kind="interview",
        )
    from app.services import events as events_service

    if user_id:
        events_service.emit(
            db,
            event_type="interview.updated",
            resource_type="interview",
            resource_id=interview.id,
            recipient_user_id=user_id,
            payload={"status": interview.status},
        )
    opp = db.get(Opportunity, app.opportunity_id)
    if opp is not None and opp.company_id is not None:
        events_service.emit(
            db,
            event_type="interview.updated",
            resource_type="interview",
            resource_id=interview.id,
            organization_id=opp.company_id,
            org_scope=True,
            payload={"status": interview.status},
        )
    db.commit()
    return interview


def mark_interview_completed(
    db: Session,
    organization_id: uuid.UUID,
    interview_id: uuid.UUID,
    actor_id: Optional[uuid.UUID] = None,
) -> Interview:
    interview = _owned_interview(db, organization_id, interview_id, actor_id=actor_id)
    interview.status = "completed"
    db.commit()
    db.refresh(interview)
    return interview


def confirm_reschedule(
    db: Session, organization_id: uuid.UUID, interview_id: uuid.UUID,
    actor_id: uuid.UUID,
) -> Interview:
    interview = _owned_interview(db, organization_id, interview_id, actor_id=actor_id)
    if interview.status != "reschedule_requested":
        raise InvalidInputError("No reschedule request is pending for this interview.")
    interview.status = "scheduled"
    interview.reschedule_count += 1
    interview.reschedule_requested_at = None
    db.commit()
    db.refresh(interview)
    return interview


def _owned_interview(
    db: Session,
    organization_id: uuid.UUID,
    interview_id: uuid.UUID,
    actor_id: Optional[uuid.UUID] = None,
) -> Interview:
    interview = db.get(Interview, interview_id)
    if interview is None:
        raise NotFoundError("Interview not found.")
    app = db.get(JobApplication, interview.application_id)
    if app is None:
        raise NotFoundError("Interview not found.")
    _application_owned(db, organization_id, app.id, actor_id=actor_id)
    return interview


# --- document requests --------------------------------------------------------


def request_document(
    db: Session,
    organization_id: uuid.UUID,
    application_id: uuid.UUID,
    actor_id: uuid.UUID,
    document_type: str,
    purpose: Optional[str] = None,
) -> DocumentRequest:
    app = _application_owned(db, organization_id, application_id, actor_id=actor_id)
    pending = db.scalar(
        select(DocumentRequest).where(
            DocumentRequest.application_id == app.id,
            DocumentRequest.document_type == document_type,
            DocumentRequest.status == "pending",
        )
    )
    if pending is not None:
        raise ConflictError("A pending request already exists for this document type.")
    request = DocumentRequest(
        application_id=app.id,
        organization_id=organization_id,
        requested_by=actor_id,
        document_type=document_type,
        purpose=purpose,
        status="pending",
    )
    db.add(request)
    db.commit()
    db.refresh(request)
    user_id = _candidate_user_id(db, app)
    if user_id:
        notifications_service.notify(
            db, user_id,
            f"The company requested: {document_type}",
            purpose or "Review the request in your Jobseeker center.",
            kind="document",
        )
    return request


def _owned_document_request(
    db: Session, organization_id: uuid.UUID, request_id: uuid.UUID
) -> DocumentRequest:
    request = db.get(DocumentRequest, request_id)
    if request is None or request.organization_id != organization_id:
        raise NotFoundError("Document request not found.")
    return request


# --- analytics (aggregate, no protected characteristics) ----------------------


def hiring_analytics(db: Session, organization_id: uuid.UUID) -> Dict:
    app_ids = org_opportunity_ids(db, organization_id)
    apps = (
        db.scalars(
            select(JobApplication).where(
                JobApplication.opportunity_id.in_(app_ids or [uuid.uuid4()])
            )
        ).all()
        if app_ids
        else []
    )
    jobs = list_org_jobs(db, organization_id)
    counts: Dict[str, int] = {}
    for app in apps:
        counts[app.status] = counts.get(app.status, 0) + 1
    open_jobs = [j for j in jobs if j.status == "published"]
    return {
        "open_jobs": len(open_jobs),
        "total_jobs": len(jobs),
        "applications_total": len(apps),
        "by_status": counts,
        "needs_review": sum(counts.get(s, 0) for s in REVIEW_STATUSES),
        "interviews_scheduled": len(
            db.scalars(
                select(Interview.id).where(
                    Interview.application_id.in_([a.id for a in apps] or [uuid.uuid4()]),
                    Interview.status == "scheduled",
                )
            ).all()
        ),
        "offers_pending": sum(
            1
            for a in apps
            if db.scalar(
                select(Offer.id).where(
                    Offer.application_id == a.id, Offer.status == "sent"
                )
            )
        ),
        "conversion": {
            "to_interview": round(
                counts.get("interview", 0) / apps.__len__() * 100, 1
            )
            if apps
            else 0.0,
            "to_offer": round(
                (counts.get("offer", 0) + counts.get("accepted", 0))
                / apps.__len__() * 100, 1
            )
            if apps
            else 0.0,
        },
    }
