"""Controlled AskTrabaajo Communication channel service (Phase 8).

A conversation exists ONLY because of a legitimate relationship (accepted
outreach, a live application, interview/offer context). It is scoped to one
candidate person + one organization. Participants are structural:

- The candidate person owns their side.
- Any member of the owning organization holding ``communications.read`` may
  view the org's conversations; ``communications.send`` is required to post
  as the org.

Conversations never carry private contact details. Message bodies are the
communication; document sharing keeps using the Phase 4 request/consent
layer. No attachments exist here.
"""
from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import InvalidInputError, NotFoundError, PermissionDeniedError
from app.core.timeutil import utc_now_naive
from app.models.communication import (
    Conversation,
    ConversationMessage,
    ConversationReadState,
)
from app.models.enums import (
    CONVERSATION_STATUS_ACTIVE,
    CONVERSATION_STATUS_CLOSED,
    MESSAGE_SIDE_CANDIDATE,
    MESSAGE_SIDE_RECRUITER,
)
from app.models.identity import PersonProfile, User
from app.models.tenancy import Organization


# --- helpers ---------------------------------------------------------------

def _org(db: Session, organization_id: uuid.UUID) -> Organization:
    org = db.get(Organization, organization_id)
    if org is None:
        raise NotFoundError("Organization not found.")
    return org


def _person(db: Session, person_id: uuid.UUID) -> PersonProfile:
    person = db.get(PersonProfile, person_id)
    if person is None:
        raise NotFoundError("Candidate not found.")
    return person


def _require_member(db: Session, organization_id: uuid.UUID, actor_id: uuid.UUID) -> None:
    from app.services import authz

    if not authz.get_org_membership(db, actor_id, organization_id):
        raise PermissionDeniedError("You are not a member of this organization.")


def _display_name(db: Session, person: PersonProfile) -> Optional[str]:
    user = db.get(User, person.user_id) if person else None
    return person.preferred_name or (user.full_name if user else None)


def _candidate_user_id(db: Session, person_id: uuid.UUID) -> Optional[uuid.UUID]:
    person = db.get(PersonProfile, person_id)
    return person.user_id if person else None


def _candidate_owns(
    db: Session, person_id: uuid.UUID, conversation_id: uuid.UUID
) -> Conversation:
    conversation = db.get(Conversation, conversation_id)
    if conversation is None or conversation.person_id != person_id:
        raise NotFoundError("Conversation not found.")
    return conversation


def _org_owns(
    db: Session,
    organization_id: uuid.UUID,
    conversation_id: uuid.UUID,
    actor_id: uuid.UUID,
) -> Conversation:
    _require_member(db, organization_id, actor_id)
    conversation = db.get(Conversation, conversation_id)
    if conversation is None or conversation.organization_id != organization_id:
        raise NotFoundError("Conversation not found.")
    return conversation


def _message_out(db: Session, message: ConversationMessage) -> dict:
    sender_name = None
    if message.sender_side == MESSAGE_SIDE_CANDIDATE:
        conversation = db.get(Conversation, message.conversation_id)
        person = db.get(PersonProfile, conversation.person_id) if conversation else None
        sender_name = _display_name(db, person)
    else:
        sender = db.get(User, message.sender_user_id)
        sender_name = sender.full_name if sender else None
    return {
        "id": str(message.id),
        "conversation_id": str(message.conversation_id),
        "sender_user_id": str(message.sender_user_id),
        "sender_side": message.sender_side,
        "sender_name": sender_name,
        "body": message.body,
        "created_at": message.created_at,
    }


def _unread_for(db: Session, conversation: Conversation, viewer_user_id: uuid.UUID) -> int:
    state = db.scalar(
        select(ConversationReadState).where(
            ConversationReadState.conversation_id == conversation.id,
            ConversationReadState.user_id == viewer_user_id,
        ).limit(1)
    )
    query = select(ConversationMessage.id).where(
        ConversationMessage.conversation_id == conversation.id,
        ConversationMessage.sender_user_id != viewer_user_id,
    )
    if state is not None:
        query = query.where(
            ConversationMessage.created_at > state.last_read_at
        )
    return len(db.scalars(query).all())


def conversation_out(
    db: Session,
    conversation: Conversation,
    viewer_user_id: uuid.UUID,
    *,
    include_messages: bool = False,
) -> dict:
    org = db.get(Organization, conversation.organization_id)
    person = db.get(PersonProfile, conversation.person_id)
    candidate_user = _candidate_user_id(db, conversation.person_id)
    # If the viewer is the candidate, the counterpart is the org opener; if
    # the viewer is an org member, the counterpart is the candidate.
    counterpart_name = None
    if viewer_user_id == candidate_user:
        opener = db.get(User, conversation.opened_by)
        counterpart_name = opener.full_name if opener else None
    else:
        counterpart_name = _display_name(db, person)

    opp_title = None
    if conversation.opportunity_id:
        from app.models.career import Opportunity

        opp = db.get(Opportunity, conversation.opportunity_id)
        opp_title = opp.title if opp else None

    messages = None
    if include_messages:
        rows = db.scalars(
            select(ConversationMessage)
            .where(ConversationMessage.conversation_id == conversation.id)
            .order_by(ConversationMessage.created_at.asc())
        ).all()
        messages = [_message_out(db, m) for m in rows]

    return {
        "id": str(conversation.id),
        "organization": {
            "id": str(conversation.organization_id),
            "name": org.name if org else None,
        },
        "candidate": {
            "person_id": str(conversation.person_id),
            "name": _display_name(db, person),
        },
        "counterpart": counterpart_name,
        "opportunity_id": (
            str(conversation.opportunity_id) if conversation.opportunity_id else None
        ),
        "opportunity_title": opp_title,
        "application_id": (
            str(conversation.application_id) if conversation.application_id else None
        ),
        "outreach_id": str(conversation.outreach_id) if conversation.outreach_id else None,
        "status": conversation.status,
        "created_at": conversation.created_at,
        "last_message_at": conversation.last_message_at,
        "closed_at": conversation.closed_at,
        "unread_count": _unread_for(db, conversation, viewer_user_id),
        "messages": messages,
    }


def create_conversation(
    db: Session,
    *,
    organization_id: uuid.UUID,
    person_id: uuid.UUID,
    actor_id: uuid.UUID,
    opportunity_id: Optional[uuid.UUID] = None,
    application_id: Optional[uuid.UUID] = None,
    outreach_id: Optional[uuid.UUID] = None,
) -> Conversation:
    """Add (flush, do not commit) one conversation. Callers commit so the
    surrounding state change (e.g. outreach accept) is atomic."""
    if outreach_id is not None:
        existing = db.scalar(
            select(Conversation.id).where(
                Conversation.outreach_id == outreach_id
            ).limit(1)
        )
        if existing is not None:
            conversation = db.get(Conversation, existing)
            return conversation  # type: ignore[return-value]
    conversation = Conversation(
        organization_id=organization_id,
        person_id=person_id,
        opportunity_id=opportunity_id,
        application_id=application_id,
        outreach_id=outreach_id,
        opened_by=actor_id,
        status=CONVERSATION_STATUS_ACTIVE,
    )
    db.add(conversation)
    db.flush()
    return conversation


# --- company side -----------------------------------------------------------

def _order_conversations(conversations) -> list:
    """Active first, then most recently messaged (None-safe for sqlite)."""
    return sorted(
        conversations,
        key=lambda c: (
            c.status != CONVERSATION_STATUS_ACTIVE,
            c.last_message_at is None,
            -(c.last_message_at.timestamp() if c.last_message_at else 0),
            -(c.created_at.timestamp() if c.created_at else 0),
        ),
    )


def list_org_conversations(
    db: Session, organization_id: uuid.UUID, actor_id: uuid.UUID, status: Optional[str] = None
) -> list:
    _require_member(db, organization_id, actor_id)
    query = select(Conversation).where(
        Conversation.organization_id == organization_id
    )
    if status:
        if status not in {CONVERSATION_STATUS_ACTIVE, CONVERSATION_STATUS_CLOSED}:
            raise InvalidInputError(f"Unknown conversation status '{status}'.")
        query = query.where(Conversation.status == status)
    conversations = _order_conversations(db.scalars(query).all())
    return [conversation_out(db, c, actor_id) for c in conversations]


def get_org_conversation(
    db: Session,
    organization_id: uuid.UUID,
    conversation_id: uuid.UUID,
    actor_id: uuid.UUID,
    include_messages: bool = True,
) -> dict:
    conversation = _org_owns(db, organization_id, conversation_id, actor_id)
    return conversation_out(
        db, conversation, actor_id, include_messages=include_messages
    )


# --- candidate side ---------------------------------------------------------

def list_candidate_conversations(
    db: Session, person_id: uuid.UUID, viewer_user_id: uuid.UUID, status: Optional[str] = None
) -> list:
    query = select(Conversation).where(Conversation.person_id == person_id)
    if status:
        if status not in {CONVERSATION_STATUS_ACTIVE, CONVERSATION_STATUS_CLOSED}:
            raise InvalidInputError(f"Unknown conversation status '{status}'.")
        query = query.where(Conversation.status == status)
    conversations = _order_conversations(db.scalars(query).all())
    return [conversation_out(db, c, viewer_user_id) for c in conversations]


def get_candidate_conversation(
    db: Session,
    person_id: uuid.UUID,
    conversation_id: uuid.UUID,
    viewer_user_id: uuid.UUID,
    include_messages: bool = True,
) -> dict:
    conversation = _candidate_owns(db, person_id, conversation_id)
    return conversation_out(
        db, conversation, viewer_user_id, include_messages=include_messages
    )


def unread_candidate_summary(db: Session, person_id: uuid.UUID) -> dict:
    conversations = db.scalars(
        select(Conversation).where(
            Conversation.person_id == person_id,
            Conversation.status == CONVERSATION_STATUS_ACTIVE,
        )
    ).all()
    candidate_user_id = _candidate_user_id(db, person_id)
    total = 0
    for conversation in conversations:
        total += _unread_for(db, conversation, candidate_user_id or uuid.uuid4())
    from app.models.communication import OutreachRequest

    pending = len(
        db.scalars(
            select(OutreachRequest.id).where(
                OutreachRequest.person_id == person_id,
                OutreachRequest.status.in_(["sent", "viewed"]),
            )
        ).all()
    )
    return {"unread_messages": total, "pending_outreach": pending}


# --- messages / read / close --------------------------------------------------

def send_message(
    db: Session,
    conversation: Conversation,
    sender_user_id: uuid.UUID,
    sender_side: str,
    body: str,
) -> ConversationMessage:
    if sender_side not in {MESSAGE_SIDE_CANDIDATE, MESSAGE_SIDE_RECRUITER}:
        raise InvalidInputError(f"Unknown sender side '{sender_side}'.")
    if conversation.status != CONVERSATION_STATUS_ACTIVE:
        raise InvalidInputError("This conversation is closed.")
    message = ConversationMessage(
        conversation_id=conversation.id,
        sender_user_id=sender_user_id,
        sender_side=sender_side,
        body=body.strip(),
    )
    db.add(message)
    db.flush()
    conversation.last_message_at = utc_now_naive()
    db.commit()
    db.refresh(message)
    return message


def mark_conversation_read(
    db: Session, conversation: Conversation, user_id: uuid.UUID
) -> None:
    state = db.scalar(
        select(ConversationReadState).where(
            ConversationReadState.conversation_id == conversation.id,
            ConversationReadState.user_id == user_id,
        ).limit(1)
    )
    now = utc_now_naive()
    if state is None:
        state = ConversationReadState(
            conversation_id=conversation.id, user_id=user_id, last_read_at=now
        )
        db.add(state)
    else:
        state.last_read_at = now
    db.commit()


def close_conversation(
    db: Session,
    conversation: Conversation,
    actor_id: uuid.UUID,
) -> Conversation:
    if conversation.status != CONVERSATION_STATUS_ACTIVE:
        raise InvalidInputError("This conversation is already closed.")
    conversation.status = CONVERSATION_STATUS_CLOSED
    conversation.closed_by = actor_id
    conversation.closed_at = utc_now_naive()
    db.commit()
    db.refresh(conversation)
    return conversation
