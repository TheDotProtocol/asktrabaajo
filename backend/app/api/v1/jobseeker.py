"""/api/v1/jobseeker — the Jobseeker Career OS API.

Every career resource here is person-owned: the router resolves the caller's
PERSON record once and scopes every query to it. Another user asking for an
application/interview/offer/goal/milestone they do not own receives 404
(existence is hidden). Opportunities are the shared catalogue; a person's
private stance (save/dismiss/apply) still stays on their own rows.

Self-service status transitions go through the application state machine —
raw status writes from the jobseeker API are impossible by construction.
"""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user
from app.core.errors import InvalidInputError, NotFoundError
from app.core.ratelimit import rate_limit_dependency
from app.db.session import get_db
from app.models.career import (
    ApplicationEvent,
    CareerGoal,
    CareerMilestone,
    Interview,
    JobApplication,
    Offer,
    Opportunity,
    UserNotification,
    WorkDnaProfile,
)
from app.models.enums import (
    INTERVIEW_STATUS_SCHEDULED,
    OFFER_CANDIDATE_DECIDABLE,
    OFFER_STATUS_ACCEPTED,
    OFFER_STATUS_DECLINED,
    OFFER_STATUSES,
    OFFER_STATUS_PENDING,
    OFFER_STATUS_SENT,
)
from app.models.identity import PersonProfile, User
from app.models.work import UserSkill
from app.schemas.common import MessageResponse
from app.schemas.communication import (
    BlockRequest,
    ConversationOut,
    DeclineRequest,
    MessageOut,
    MessageSend,
    ReportRequest,
)
from app.schemas.jobseeker import (
    AdvisorSnapshotOut,
    ApplicationDetailOut,
    ApplicationEventOut,
    ApplicationOut,
    ApplyRequest,
    BatchApplyRequest,
    CareerGoalCreate,
    CareerGoalOut,
    CareerGoalUpdate,
    DashboardOut,
    DnaProfileOut,
    DnaQuestionOut,
    DnaSubmitRequest,
    InterviewOut,
    MilestoneCreate,
    MilestoneOut,
    NotificationOut,
    OfferDecisionRequest,
    OfferOut,
    OpportunityListOut,
    OpportunityMatchOut,
    OpportunityOut,
    RescheduleRequest,
)
from app.services import audit as audit_service
from app.services import applications as applications_service
from app.services import communications as communications_service
from app.services import enforcement as enforcement_service
from app.services import development as development_service
from app.services import events as events_service
from app.services import matching as matching_service
from app.services import notifications as notifications_service
from app.services import outreach as outreach_service
from app.services import person as person_service
from app.services import skills_registry
from app.services import talent as talent_service
from app.services import work_dna as dna_service
from app.services.auth_service import get_person_for_user
from app.core.timeutil import utc_now_naive

message_send_limit = rate_limit_dependency("message.send")
batch_limit = rate_limit_dependency("application.batch")

router = APIRouter(prefix="/jobseeker", tags=["jobseeker"])


# --- helpers -----------------------------------------------------------------

def _person(db: Session, user: User) -> PersonProfile:
    person = get_person_for_user(db, user.id)
    if person is None:
        raise NotFoundError("Person profile not found for this account.")
    return person


def _opportunity_out(opp: Opportunity) -> Optional[OpportunityOut]:
    if opp is None:
        return None
    return OpportunityOut.model_validate(opp)


def _owned_application(db: Session, person_id: uuid.UUID, application_id: uuid.UUID) -> JobApplication:
    app = db.get(JobApplication, application_id)
    if app is None or app.person_id != person_id:
        raise NotFoundError("Application not found.")
    return app


def _application_out(app: JobApplication) -> ApplicationOut:
    out = ApplicationOut.model_validate(app)
    return out


# --- Work DNA ----------------------------------------------------------------

@router.get("/work-dna/questions", response_model=list[DnaQuestionOut])
def dna_questions(
    _user: User = Depends(get_current_user),
    _db: Session = Depends(get_db),
) -> list:
    """Current versioned assessment question set (adaptive engines later)."""
    return dna_service.list_questions()


@router.get("/work-dna", response_model=Optional[DnaProfileOut])
def get_work_dna(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Optional[WorkDnaProfile]:
    person = _person(db, user)
    return dna_service.get_current_profile(db, person.id)


@router.post("/work-dna/assessments", response_model=DnaProfileOut, status_code=201)
def submit_work_dna(
    body: DnaSubmitRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WorkDnaProfile:
    person = _person(db, user)
    profile = dna_service.submit_assessment(
        db, person.id, body.answers, user_id=user.id
    )
    audit_service.record(
        db,
        actor_id=user.id,
        action="workdna.assessment.submitted",
        resource_type="work_dna_profile",
        resource_id=profile.id,
    )
    notifications_service.notify(
        db,
        user.id,
        "Work DNA updated",
        "Your Work DNA profile has been refreshed from your latest assessment.",
        kind="career",
    )
    db.commit()
    db.refresh(profile)
    return profile


# --- Career goals ------------------------------------------------------------

@router.get("/goals", response_model=list[CareerGoalOut])
def list_goals(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list:
    person = _person(db, user)
    return db.scalars(
        select(CareerGoal)
        .where(CareerGoal.person_id == person.id)
        .order_by(CareerGoal.created_at.desc())
    ).all()


@router.post("/goals", response_model=CareerGoalOut, status_code=201)
def create_goal(
    body: CareerGoalCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CareerGoal:
    person = _person(db, user)
    goal = CareerGoal(person_id=person.id, **body.model_dump())
    db.add(goal)
    db.commit()
    db.refresh(goal)
    audit_service.record(
        db,
        actor_id=user.id,
        action="career_goal.created",
        resource_type="career_goal",
        resource_id=goal.id,
    )
    db.commit()
    return goal


@router.patch("/goals/{goal_id}", response_model=CareerGoalOut)
def update_goal(
    goal_id: uuid.UUID,
    body: CareerGoalUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CareerGoal:
    person = _person(db, user)
    goal = db.get(CareerGoal, goal_id)
    if goal is None or goal.person_id != person.id:
        raise NotFoundError("Career goal not found.")
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(goal, key, value)
    db.commit()
    db.refresh(goal)
    return goal


@router.delete("/goals/{goal_id}", response_model=MessageResponse)
def delete_goal(
    goal_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    person = _person(db, user)
    goal = db.get(CareerGoal, goal_id)
    if goal is None or goal.person_id != person.id:
        raise NotFoundError("Career goal not found.")
    db.delete(goal)
    db.commit()
    return MessageResponse(message="Career goal deleted.")


# --- Opportunities (shared catalogue + personal stance) ----------------------

@router.get("/opportunities", response_model=OpportunityListOut)
def list_opportunities(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    q: Optional[str] = Query(None, max_length=200),
    company: Optional[str] = Query(None, max_length=200),
    work_mode: Optional[str] = Query(None, max_length=20),
    industry: Optional[str] = Query(None, max_length=120),
    country: Optional[str] = Query(None, max_length=80),
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OpportunityListOut:
    person = _person(db, _user)
    query = select(Opportunity).where(
        Opportunity.status == "active", Opportunity.is_approved.is_(True)
    )
    if q:
        like = f"%{q}%"
        query = query.where(
            or_(
                Opportunity.title.ilike(like),
                Opportunity.company_name.ilike(like),
                Opportunity.summary.ilike(like),
            )
        )
    if company:
        query = query.where(Opportunity.company_name.ilike(f"%{company}%"))
    if work_mode:
        query = query.where(Opportunity.work_mode == work_mode)
    if industry:
        query = query.where(Opportunity.industry.ilike(f"%{industry}%"))
    if country:
        query = query.where(Opportunity.country == country)

    total = len(db.scalars(query).all()) if page == 1 else len(
        db.scalars(
            select(func.count()).select_from(query.subquery())
        ).all()
    )
    query = query.order_by(Opportunity.created_at.desc())
    opportunities = db.scalars(query.offset((page - 1) * page_size).limit(page_size)).all()

    saved_ids = set(
        db.scalars(
            select(JobApplication.opportunity_id).where(
                JobApplication.person_id == person.id,
                JobApplication.status.in_(["saved"]),
            )
        ).all()
    )
    applied_ids = set(
        db.scalars(
            select(JobApplication.opportunity_id).where(
                JobApplication.person_id == person.id,
                JobApplication.status.in_(
                    ["applied", "application_received", "screening", "assessment",
                     "interview", "offer", "accepted", "on_hold"]
                ),
            )
        ).all()
    )

    matches = matching_service.match_all(db, person.id, opportunities)
    match_by_id = {m["opportunity_id"]: m for m in matches}
    items = []
    for opp in opportunities:
        m = match_by_id.get(str(opp.id), {})
        components = m.get("components", {})
        enriched = {}
        for key, comp in components.items():
            enriched[key] = {
                "score": comp.get("score", 0.0),
                "reason": comp.get("reason", ""),
                "matched": comp.get("matched"),
                "missing": comp.get("missing"),
            }
        items.append(
            OpportunityMatchOut(
                opportunity_id=opp.id,
                percent=m.get("percent", 0),
                score=m.get("score", 0.0),
                components=enriched,
                strengths=m.get("strengths", []),
                gaps=m.get("gaps", []),
                missing_skills=m.get("missing_skills", []),
                opportunity=_opportunity_out(opp),
                saved=str(opp.id) in saved_ids,
                applied=str(opp.id) in applied_ids,
            )
        )
    return OpportunityListOut(
        items=items, total=total, page=page, page_size=page_size
    )


@router.get("/opportunities/{opportunity_id}", response_model=dict)
def opportunity_detail(
    opportunity_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Opportunity intelligence: the match, skill gaps with evidence, and
    structured requirements — computed for the caller's own Work ID."""
    person = _person(db, user)
    opp = db.get(Opportunity, opportunity_id)
    if opp is None or opp.status != "active" or not opp.is_approved:
        raise NotFoundError("Opportunity not found.")

    match = matching_service.match_all(db, person.id, [opp])
    match_payload = match[0] if match else {}
    gap = talent_service.own_skill_gap_analysis(db, person.id, opp.id)
    skills_registry.normalize_opportunity_requirements(db, opp)
    from app.models.talent import OpportunityRequirement

    req_rows = db.scalars(
        select(OpportunityRequirement)
        .where(OpportunityRequirement.opportunity_id == opp.id)
        .order_by(OpportunityRequirement.created_at.asc())
    ).all()
    from app.models.work import Skill as SkillModel

    my_stance = db.scalar(
        select(JobApplication.status).where(
            JobApplication.person_id == person.id,
            JobApplication.opportunity_id == opp.id,
        ).limit(1)
    )
    requirements = [
        {
            "id": str(r.id),
            "skill": db.get(SkillModel, r.skill_id).name if r.skill_id else None,
            "raw_text": r.raw_text,
            "requirement_kind": r.requirement_kind,
            "min_years": r.min_years,
        }
        for r in req_rows
    ]
    db.commit()
    return {
        "opportunity": _opportunity_out(opp),
        "match": match_payload,
        "gap_analysis": gap,
        "requirements": requirements,
        "saved": my_stance == "saved",
        "applied": my_stance in {
            "applied", "application_received", "screening", "assessment",
            "interview", "offer", "accepted", "on_hold",
        },
        "stance": my_stance,
    }


@router.get("/career/intelligence")
def career_intelligence(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Data-grounded career intelligence over the caller's own Work ID:
    roles within reach, roles to grow into, and skills to develop (tied to
    real active opportunities). Never promises outcomes."""
    person = _person(db, user)
    return talent_service.career_intelligence(db, person.id)


@router.post("/opportunities/{opportunity_id}/save", response_model=ApplicationOut)
def save_opportunity(
    opportunity_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JobApplication:
    person = _person(db, user)
    return applications_service.save_opportunity(db, person.id, opportunity_id)


@router.post("/opportunities/{opportunity_id}/dismiss", response_model=MessageResponse)
def dismiss_opportunity(
    opportunity_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    person = _person(db, user)
    from app.models.career import OpportunityInteraction

    existing = db.scalar(
        select(OpportunityInteraction).where(
            OpportunityInteraction.person_id == person.id,
            OpportunityInteraction.opportunity_id == opportunity_id,
        )
    )
    if existing is not None:
        existing.action = "dismissed"
    else:
        db.add(
            OpportunityInteraction(
                person_id=person.id,
                opportunity_id=opportunity_id,
                action="dismissed",
            )
        )
    db.commit()
    return MessageResponse(message="Opportunity dismissed.")


# --- Applications ------------------------------------------------------------

@router.get("/applications", response_model=list[ApplicationOut])
def list_applications(
    status: Optional[str] = Query(None, max_length=32),
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list:
    person = _person(db, _user)
    query = (
        select(JobApplication)
        .options(joinedload(JobApplication.opportunity))
        .where(JobApplication.person_id == person.id)
    )
    if status:
        query = query.where(JobApplication.status == status)
    apps = db.scalars(
        query.order_by(JobApplication.last_activity_at.desc())
    ).all()
    return [_application_out(a) for a in apps]


@router.get("/applications/{application_id}", response_model=ApplicationDetailOut)
def application_detail(
    application_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApplicationDetailOut:
    person = _person(db, user)
    app = _owned_application(db, person.id, application_id)
    events = db.scalars(
        select(ApplicationEvent)
        .where(ApplicationEvent.application_id == app.id)
        .order_by(ApplicationEvent.created_at.asc())
    ).all()
    has_interview = (
        db.scalar(
            select(Interview.id)
            .where(
                Interview.application_id == app.id,
                Interview.status.in_(["scheduled", "reschedule_requested", "completed"]),
            )
            .limit(1)
        )
        is not None
    )
    has_offer = (
        db.scalar(select(Offer.id).where(Offer.application_id == app.id).limit(1))
        is not None
    )
    return ApplicationDetailOut(
        application=_application_out(app),
        timeline=[ApplicationEventOut.model_validate(e) for e in events],
        opportunity=_opportunity_out(app.opportunity),
        has_interview=has_interview,
        has_offer=has_offer,
    )


@router.post("/applications", response_model=ApplicationOut, status_code=201)
def apply_to_opportunity(
    body: ApplyRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JobApplication:
    person = _person(db, user)
    enforcement_service.check_application_allowed(db, user.id)
    app = applications_service.apply(
        db,
        person.id,
        body.opportunity_id,
        actor_user_id=user.id,
        cover_note=body.cover_note,
    )
    opp = db.get(Opportunity, body.opportunity_id)
    audit_service.record(
        db,
        actor_id=user.id,
        action="application.submitted",
        resource_type="job_application",
        resource_id=app.id,
    )
    db.commit()
    db.refresh(app)
    if opp:
        notifications_service.notify(
            db,
            user.id,
            f"Application submitted to {opp.company_name}",
            f"You applied to {opp.title}.",
            kind="application",
        )
    return app


@router.post("/applications/batch", response_model=dict)
def batch_apply(
    body: BatchApplyRequest,
    user: User = Depends(get_current_user),
    _rl: None = Depends(batch_limit),
    db: Session = Depends(get_db),
) -> dict:
    """Explicit batch apply — the caller lists the exact opportunities.

    This is the building block Athena may one day trigger AFTER the user
    explicitly authorizes bulk applications. Consent stays at the boundary.
    """
    person = _person(db, user)
    result = applications_service.apply_to_matching(
        db, person.id, user.id, [str(o) for o in body.opportunity_ids]
    )
    audit_service.record(
        db,
        actor_id=user.id,
        action="application.batch_submitted",
        resource_type="job_application",
        metadata={"applied": len(result["applied"]), "failed": len(result["failed"])},
    )
    db.commit()
    return result


@router.post("/applications/{application_id}/withdraw", response_model=ApplicationOut)
def withdraw_application(
    application_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    reason: Optional[str] = Query(None, max_length=500),
) -> JobApplication:
    person = _person(db, user)
    app = applications_service.withdraw(
        db, person.id, application_id, actor_user_id=user.id, reason=reason
    )
    audit_service.record(
        db,
        actor_id=user.id,
        action="application.withdrawn",
        resource_type="job_application",
        resource_id=app.id,
    )
    db.commit()
    db.refresh(app)
    return app


# --- Interviews --------------------------------------------------------------

@router.get("/interviews", response_model=list[InterviewOut])
def list_interviews(
    upcoming: bool = False,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list:
    person = _person(db, user)
    app_ids = db.scalars(
        select(JobApplication.id).where(JobApplication.person_id == person.id)
    ).all()
    if not app_ids:
        return []
    query = select(Interview).where(Interview.application_id.in_(app_ids))
    if upcoming:
        query = query.where(
            Interview.status.in_(["scheduled", "reschedule_requested"]),
            Interview.scheduled_at >= utc_now_naive(),
        )
    return db.scalars(
        query.order_by(Interview.scheduled_at.desc())
    ).all()


@router.post("/interviews/{interview_id}/reschedule-request", response_model=InterviewOut)
def request_reschedule(
    interview_id: uuid.UUID,
    body: RescheduleRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Interview:
    """Request a reschedule — policy-controlled, not unlimited.

    Jobseekers get a small, configurable number of reschedules and must give
    a reason. Repeated requests without a valid reason are rejected by policy
    (the reason minimum length is enforced at the schema). The company side
    approves or counters in a later phase.
    """
    person = _person(db, user)
    interview = db.get(Interview, interview_id)
    if interview is None:
        raise NotFoundError("Interview not found.")
    app = db.get(JobApplication, interview.application_id)
    if app is None or app.person_id != person.id:
        raise NotFoundError("Interview not found.")
    from app.core.config import get_settings

    max_reschedules = get_settings().max_reschedules_per_interview
    if interview.reschedule_count >= max_reschedules:
        raise InvalidInputError(
            f"This interview has already been rescheduled "
            f"{interview.reschedule_count} time(s) (limit {max_reschedules}). "
            "Contact the company directly for further changes."
        )
    if body.proposed_at is None and not body.reason:
        raise InvalidInputError("Provide a proposed time or a clear reason.")
    interview.status = "reschedule_requested"
    interview.reschedule_reason = body.reason
    interview.reschedule_requested_at = utc_now_naive()
    if body.proposed_at is not None:
        interview.scheduled_at = body.proposed_at
    db.commit()
    db.refresh(interview)
    notifications_service.notify(
        db,
        user.id,
        "Reschedule requested",
        f"Your request to reschedule the interview on "
        f"{interview.scheduled_at.strftime('%Y-%m-%d %H:%M')} has been noted.",
        kind="interview",
    )
    return interview


# --- Offers ------------------------------------------------------------------

@router.get("/offers", response_model=list[OfferOut])
def list_offers(
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list:
    person = _person(db, _user)
    app_ids = db.scalars(
        select(JobApplication.id).where(JobApplication.person_id == person.id)
    ).all()
    if not app_ids:
        return []
    return db.scalars(
        select(Offer).where(Offer.application_id.in_(app_ids))
    ).all()


@router.post("/offers/{offer_id}/decision", response_model=OfferOut)
def decide_offer(
    offer_id: uuid.UUID,
    body: OfferDecisionRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Offer:
    """Explicit accept/decline — never auto-generated or binding documents."""
    person = _person(db, user)
    offer = db.get(Offer, offer_id)
    if offer is None:
        raise NotFoundError("Offer not found.")
    app = db.get(JobApplication, offer.application_id)
    if app is None or app.person_id != person.id:
        raise NotFoundError("Offer not found.")
    if offer.status not in OFFER_CANDIDATE_DECIDABLE:
        raise InvalidInputError(
            f"Cannot respond to an offer with status '{offer.status}'."
        )
    decision = body.decision
    if decision not in (OFFER_STATUS_ACCEPTED, OFFER_STATUS_DECLINED):
        raise InvalidInputError("decision must be 'accepted' or 'declined'.")
    offer.status = decision
    offer.responded_at = utc_now_naive()
    if decision == OFFER_STATUS_ACCEPTED:
        # Offer accepted: application reaches 'accepted' via the state machine.
        applications_service.transition_to_status(
            db, app, "accepted", actor_user_id=user.id,
            note="Offer accepted by candidate.",
        )
    db.commit()
    db.refresh(offer)
    audit_service.record(
        db,
        actor_id=user.id,
        action=f"offer.{decision}",
        resource_type="offer",
        resource_id=offer.id,
    )
    # Org-scope realtime event so the company sees the decision instantly.
    opp = db.get(Opportunity, app.opportunity_id)
    if opp is not None and opp.company_id is not None:
        events_service.emit(
            db,
            event_type="offer.updated",
            resource_type="offer",
            resource_id=offer.id,
            organization_id=opp.company_id,
            org_scope=True,
            actor_user_id=user.id,
            payload={"status": decision, "application_id": str(app.id)},
        )
    db.commit()
    return offer


# --- Advisor / milestones / dashboard ----------------------------------------

@router.get("/advisor", response_model=AdvisorSnapshotOut)
def advisor_snapshot(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    person = _person(db, user)
    return development_service.advisor_snapshot(db, person.id)


@router.get("/milestones", response_model=list[MilestoneOut])
def list_milestones(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list:
    person = _person(db, user)
    return db.scalars(
        select(CareerMilestone)
        .where(CareerMilestone.person_id == person.id)
        .order_by(CareerMilestone.occurred_on.desc())
    ).all()


@router.post("/milestones", response_model=MilestoneOut, status_code=201)
def create_milestone(
    body: MilestoneCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CareerMilestone:
    person = _person(db, user)
    milestone = CareerMilestone(person_id=person.id, **body.model_dump())
    db.add(milestone)
    db.commit()
    db.refresh(milestone)
    return milestone


@router.delete("/milestones/{milestone_id}", response_model=MessageResponse)
def delete_milestone(
    milestone_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    person = _person(db, user)
    milestone = db.get(CareerMilestone, milestone_id)
    if milestone is None or milestone.person_id != person.id:
        raise NotFoundError("Milestone not found.")
    db.delete(milestone)
    db.commit()
    return MessageResponse(message="Milestone deleted.")


@router.get("/dashboard", response_model=DashboardOut)
def jobseeker_dashboard(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DashboardOut:
    """The personal Career Command Center — aggregates owned data only."""
    person = _person(db, user)

    completion = person_service.profile_completion(db, person, user)

    dna = dna_service.get_current_profile(db, person.id)

    goal = matching_service.load_primary_goal(db, person.id)

    apps = db.scalars(
        select(JobApplication)
        .options(joinedload(JobApplication.opportunity))
        .where(JobApplication.person_id == person.id)
        .order_by(JobApplication.last_activity_at.desc())
        .limit(10)
    ).all()
    app_ids = db.scalars(
        select(JobApplication.id).where(JobApplication.person_id == person.id)
    ).all()
    live_ids = db.scalars(
        select(JobApplication.id).where(
            JobApplication.person_id == person.id,
            JobApplication.status.in_(
                ["saved", "applied", "application_received", "screening",
                 "assessment", "interview", "on_hold"]
            ),
        )
    ).all()

    interview_scope = app_ids or [uuid.uuid4()]
    upcoming_interviews = db.scalars(
        select(Interview)
        .where(
            Interview.application_id.in_(interview_scope),
            Interview.status.in_(["scheduled", "reschedule_requested"]),
            Interview.scheduled_at >= utc_now_naive(),
        )
        .order_by(Interview.scheduled_at.asc())
        .limit(5)
    ).all()

    pending_offers = db.scalars(
        select(Offer).where(
            Offer.application_id.in_(interview_scope),
            Offer.status.in_(OFFER_CANDIDATE_DECIDABLE),
        )
    ).all()

    opportunities = db.scalars(
        select(Opportunity)
        .where(Opportunity.status == "active", Opportunity.is_approved.is_(True))
        .limit(50)
    ).all()
    matches = matching_service.match_all(db, person.id, opportunities)[:5]

    stats = {
        "applications": len(app_ids),
        "live": len(live_ids),
        "upcoming_interviews": len(upcoming_interviews),
        "pending_offers": len(pending_offers),
        "career_milestones": len(
            db.scalars(
                select(CareerMilestone.id).where(
                    CareerMilestone.person_id == person.id
                )
            ).all()
        ),
    }

    return DashboardOut(
        profile_completion=completion,
        work_dna_status="completed" if dna else "incomplete",
        has_career_goal=goal is not None,
        stats=stats,
        upcoming_interviews=[InterviewOut.model_validate(i) for i in upcoming_interviews],
        recent_applications=[_application_out(a) for a in apps],
        recommended=matches,
        advisor=development_service.advisor_snapshot(db, person.id),
        unread_notifications=notifications_service.unread_count(db, user.id),
    )


# --- Notifications -----------------------------------------------------------


# --- Document requests (candidate responses) --------------------------------


@router.get("/document-requests", response_model=list)
def list_my_document_requests(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list:
    """Document requests companies have made on the candidate's applications."""
    person = _person(db, user)
    app_ids = db.scalars(
        select(JobApplication.id).where(JobApplication.person_id == person.id)
    ).all()
    if not app_ids:
        return []
    from app.models.company import DocumentRequest

    requests = db.scalars(
        select(DocumentRequest)
        .where(DocumentRequest.application_id.in_(app_ids))
        .order_by(DocumentRequest.created_at.desc())
    ).all()
    return [
        {
            "id": str(r.id),
            "application_id": str(r.application_id),
            "organization_id": str(r.organization_id),
            "organization_name": _org_name(db, r.organization_id),
            "document_type": r.document_type,
            "purpose": r.purpose,
            "status": r.status,
            "note": r.note,
            "created_at": r.created_at,
        }
        for r in requests
    ]


def _org_name(db: Session, organization_id) -> Optional[str]:
    from app.models.tenancy import Organization

    org = db.get(Organization, organization_id)
    return org.name if org else None


@router.post("/document-requests/{request_id}/approve", response_model=dict)
def approve_document_request(
    request_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Candidate approves -> create a live org grant for the chosen document.

    The candidate explicitly chooses WHICH document satisfies the request;
    nothing is exposed automatically.
    """
    from app.models.company import DocumentRequest
    from app.models.documents import PersonDocument
    from app.services import document_access as doc_service

    person = _person(db, user)
    request = db.get(DocumentRequest, request_id)
    if request is None:
        raise NotFoundError("Document request not found.")
    app = db.get(JobApplication, request.application_id)
    if app is None or app.person_id != person.id:
        raise NotFoundError("Document request not found.")
    if request.status != "pending":
        raise InvalidInputError(
            f"This request has already been {request.status}."
        )

    # Candidate picks a matching document of the requested type.
    documents = db.scalars(
        select(PersonDocument).where(
            PersonDocument.person_id == person.id,
            PersonDocument.doc_type == request.document_type,
            PersonDocument.is_archived.is_(False),
        )
    ).all()
    if not documents:
        raise InvalidInputError(
            f"No document of type '{request.document_type}' is on your Work ID. "
            "Add one first, then approve."
        )
    doc = documents[0]
    doc_service.grant_document_access(
        db,
        document=doc,
        grantee_user_id=None,
        grantee_organization_id=request.organization_id,
        actor_id=user.id,
        purpose=request.purpose or request.document_type,
    )
    request.status = "approved"
    request.responded_at = utc_now_naive()
    request.responded_by = user.id
    db.commit()
    audit_service.record(
        db,
        actor_id=user.id,
        action="document_request.approved",
        resource_type="document_request",
        resource_id=request.id,
        organization_id=request.organization_id,
    )
    db.commit()
    return {"id": str(request.id), "status": "approved", "document_id": str(doc.id)}


@router.post("/document-requests/{request_id}/decline", response_model=dict)
def decline_document_request(
    request_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    note: Optional[str] = Query(None, max_length=500),
) -> dict:
    person = _person(db, user)
    from app.models.company import DocumentRequest

    request = db.get(DocumentRequest, request_id)
    if request is None:
        raise NotFoundError("Document request not found.")
    app = db.get(JobApplication, request.application_id)
    if app is None or app.person_id != person.id:
        raise NotFoundError("Document request not found.")
    if request.status != "pending":
        raise InvalidInputError(
            f"This request has already been {request.status}."
        )
    request.status = "declined"
    request.responded_at = utc_now_naive()
    request.responded_by = user.id
    request.note = note
    db.commit()
    return {"id": str(request.id), "status": "declined"}


@router.get("/notifications", response_model=list[NotificationOut])
def list_notifications(
    unread_only: bool = False,
    limit: int = Query(30, ge=1, le=100),
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list:
    return notifications_service.list_for_user(
        db, _user.id, limit=limit, unread_only=unread_only
    )


@router.post("/notifications/{notification_id}/read", response_model=MessageResponse)
def mark_notification_read(
    notification_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    ok = notifications_service.mark_read(db, user.id, notification_id)
    if not ok:
        raise NotFoundError("Notification not found.")
    return MessageResponse(message="Notification marked as read.")


@router.post("/notifications/read-all", response_model=dict)
def mark_all_notifications_read(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    count = notifications_service.mark_all_read(db, user.id)
    return {"marked": count}


@router.get("/notifications/unread-count", response_model=dict)
def notification_unread_count(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    return {"unread": notifications_service.unread_count(db, user.id)}


# --- Outreach + controlled communications (Phase 8) ----------------------------


def _outreach_row(db: Session, request_id: uuid.UUID):
    from app.models.communication import OutreachRequest

    return db.get(OutreachRequest, request_id)


def _org_name(db: Session, organization_id) -> Optional[str]:
    from app.models.tenancy import Organization

    org = db.get(Organization, organization_id)
    return org.name if org else None


@router.get("/communications", response_model=dict)
def communications_inbox(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """The candidate's communication center: pending outreach, active
    conversations and unread counts — everything THEY own, nothing more."""
    person = _person(db, user)
    outreach = outreach_service.list_candidate_outreach(db, person.id)
    conversations = communications_service.list_candidate_conversations(
        db, person.id, user.id
    )
    unread = communications_service.unread_candidate_summary(db, person.id)
    return {
        "outreach": outreach,
        "conversations": conversations,
        "unread": unread,
    }


@router.get("/communications/blocks", response_model=list)
def list_blocks(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list:
    person = _person(db, user)
    return outreach_service.list_blocks(db, person.id)


@router.post("/communications/organizations/{organization_id}/block",
             response_model=dict, status_code=201)
def block_organization(
    organization_id: uuid.UUID,
    body: BlockRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Candidate asks this organization not to contact them again."""
    person = _person(db, user)
    outreach_service.block_organization(
        db, person.id, organization_id, user.id, reason=body.reason
    )
    audit_service.record(
        db,
        actor_id=user.id,
        action="communications.org.blocked",
        resource_type="outreach_block",
        organization_id=organization_id,
    )
    db.commit()
    return {"organization_id": str(organization_id), "blocked": True}


@router.delete("/communications/organizations/{organization_id}/block",
               response_model=MessageResponse)
def unblock_organization(
    organization_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    person = _person(db, user)
    outreach_service.unblock_organization(db, person.id, organization_id, user.id)
    audit_service.record(
        db,
        actor_id=user.id,
        action="communications.org.unblocked",
        resource_type="outreach_block",
        organization_id=organization_id,
    )
    db.commit()
    return MessageResponse(message="Block removed.")


@router.get("/communications/unread", response_model=dict)
def communications_unread(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    person = _person(db, user)
    return communications_service.unread_candidate_summary(db, person.id)


@router.get("/communications/{conversation_id}", response_model=ConversationOut)
def get_my_conversation(
    conversation_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    person = _person(db, user)
    return communications_service.get_candidate_conversation(
        db, person.id, conversation_id, user.id
    )


@router.post("/communications/{conversation_id}/messages", response_model=MessageOut,
             status_code=201)
def send_candidate_message(
    conversation_id: uuid.UUID,
    body: MessageSend,
    user: User = Depends(get_current_user),
    _rl: None = Depends(message_send_limit),
    db: Session = Depends(get_db),
) -> dict:
    person = _person(db, user)
    enforcement_service.check_communication_allowed(db, user.id)
    from app.services.communications import _candidate_owns

    conversation = _candidate_owns(db, person.id, conversation_id)
    message = communications_service.send_message(
        db, conversation, user.id, sender_side="candidate", body=body.body
    )
    audit_service.record(
        db,
        actor_id=user.id,
        action="communications.message.sent",
        resource_type="conversation_message",
        resource_id=message.id,
        organization_id=conversation.organization_id,
        metadata={"conversation_id": str(conversation_id)},
    )
    # Notify the company-side opener (never other candidates' data).
    opener = db.get(User, conversation.opened_by)
    if opener is not None and opener.id != user.id:
        notifications_service.notify(
            db,
            opener.id,
            "A candidate replied",
            "A candidate replied to your conversation in AskTrabaajo.",
            kind="communication",
        )
    # Org-scope realtime event for the conversation's company (no body).
    events_service.emit(
        db,
        event_type="message.sent",
        resource_type="conversation_message",
        resource_id=message.id,
        organization_id=conversation.organization_id,
        org_scope=True,
        actor_user_id=user.id,
        payload={"conversation_id": str(conversation_id), "sender_side": "candidate"},
    )
    db.commit()
    return communications_service._message_out(db, message)


@router.post("/communications/{conversation_id}/read", response_model=dict)
def mark_my_conversation_read(
    conversation_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    person = _person(db, user)
    from app.services.communications import _candidate_owns

    conversation = _candidate_owns(db, person.id, conversation_id)
    communications_service.mark_conversation_read(db, conversation, user.id)
    return {"conversation_id": str(conversation_id), "ok": True}


@router.post("/communications/{conversation_id}/close", response_model=ConversationOut)
def close_my_conversation(
    conversation_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    person = _person(db, user)
    from app.services.communications import _candidate_owns

    conversation = _candidate_owns(db, person.id, conversation_id)
    closed = communications_service.close_conversation(db, conversation, user.id)
    audit_service.record(
        db,
        actor_id=user.id,
        action="communications.conversation.closed",
        resource_type="conversation",
        resource_id=conversation_id,
    )
    db.commit()
    return communications_service.conversation_out(db, closed, user.id)


@router.get("/outreach/{request_id}", response_model=dict)
def view_my_outreach(
    request_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Candidate reads one outreach request (marks it viewed)."""
    person = _person(db, user)
    payload = outreach_service.get_candidate_outreach(
        db, person.id, request_id, user.id
    )
    request = _outreach_row(db, request_id)
    audit_service.record(
        db,
        actor_id=user.id,
        action="talent.outreach.viewed",
        resource_type="outreach_request",
        resource_id=request_id,
        organization_id=request.organization_id if request else None,
    )
    db.commit()
    return payload


@router.post("/outreach/{request_id}/accept", response_model=dict)
def accept_outreach(
    request_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Accept opens a controlled AskTrabaajo conversation. It never exposes
    private contact details — the employer still communicates in-platform."""
    person = _person(db, user)
    result = outreach_service.accept_outreach(db, person.id, request_id, user.id)
    request = _outreach_row(db, request_id)
    audit_service.record(
        db,
        actor_id=user.id,
        action="talent.outreach.accepted",
        resource_type="outreach_request",
        resource_id=request_id,
        organization_id=request.organization_id if request else None,
    )
    if request is not None:
        notifications_service.notify(
            db,
            request.requester_id,
            "Your outreach request was accepted",
            "The candidate accepted your request — a controlled conversation "
            "is now open in your communications center.",
            kind="communication",
        )
        events_service.emit(
            db,
            event_type="outreach.accepted",
            resource_type="outreach_request",
            resource_id=request_id,
            organization_id=request.organization_id,
            org_scope=True,
            actor_user_id=user.id,
            payload={"conversation_id": result.get("conversation_id")},
        )
    db.commit()
    return result


@router.post("/outreach/{request_id}/decline", response_model=dict)
def decline_outreach(
    request_id: uuid.UUID,
    body: DeclineRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    person = _person(db, user)
    result = outreach_service.decline_outreach(db, person.id, request_id, note=body.note)
    request = _outreach_row(db, request_id)
    audit_service.record(
        db,
        actor_id=user.id,
        action="talent.outreach.declined",
        resource_type="outreach_request",
        resource_id=request_id,
        organization_id=request.organization_id if request else None,
        metadata={"note_present": bool(body.note)},
    )
    # Company receives a GENERIC decline — no private information is shared.
    if request is not None:
        notifications_service.notify(
            db,
            request.requester_id,
            "Your outreach request was declined",
            "The candidate declined this outreach request.",
            kind="communication",
        )
        events_service.emit(
            db,
            event_type="outreach.declined",
            resource_type="outreach_request",
            resource_id=request_id,
            organization_id=request.organization_id,
            org_scope=True,
            actor_user_id=user.id,
        )
    db.commit()
    return result


@router.post("/outreach/{request_id}/report", response_model=dict)
def report_outreach(
    request_id: uuid.UUID,
    body: ReportRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Report an outreach: the request is blocked and the organization is
    added to the candidate's standing block list."""
    person = _person(db, user)
    result = outreach_service.report_outreach(
        db, person.id, request_id, user.id, note=body.note
    )
    request = _outreach_row(db, request_id)
    audit_service.record(
        db,
        actor_id=user.id,
        action="talent.outreach.reported",
        resource_type="outreach_request",
        resource_id=request_id,
        organization_id=request.organization_id if request else None,
        metadata={"note_present": bool(body.note)},
    )
    if request is not None:
        events_service.emit(
            db,
            event_type="outreach.blocked",
            resource_type="outreach_request",
            resource_id=request_id,
            organization_id=request.organization_id,
            org_scope=True,
            actor_user_id=user.id,
        )
    db.commit()
    return result
