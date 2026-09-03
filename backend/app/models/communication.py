"""Controlled Talent Outreach & Communication — Phase 8 models.

The product principle this module exists to serve:

    Recruiters should NEVER receive a candidate's private contact details
    merely because the candidate is discoverable.

AskTrabaajo remains the intermediary between employers and people:

- ``OutreachRequest``  — "I would like to contact this candidate regarding
  this opportunity." Organization-scoped, with the requesting member, the
  candidate, the optional opportunity/application, an introduction message
  and a controlled lifecycle. Sending a request NEVER reveals private
  contact information.
- ``OutreachBlock``    — a candidate's standing "no contact" decision
  against an organization. It prevents future requests (abuse control).
- ``Conversation``     — a controlled AskTrabaajo channel. A conversation
  exists ONLY because of a legitimate relationship: an accepted outreach,
  or a live application with the organization (application, interview,
  offer and employment threads attach here later). It is scoped to one
  candidate person + one organization and optionally linked to the
  opportunity/application/outreach that created it.
- ``ConversationMessage`` — one message in a conversation. The sender is a
  user (org member or the candidate); ``sender_side`` marks the direction
  so read-state and notifications can be computed without joins.
- ``ConversationReadState`` — per-user read cursor (conversation_id,
  user_id). Unread = messages authored by the other side after the cursor.

No participant tables are needed: a member of the owning organization with
``communications.read`` may access the org's conversations, and the owning
person may access their own. Tenant isolation is enforced structurally at
the service/API layer (Company A can never reach Company B rows).
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from app.db.base import Base
from app.models.enums import (
    CONVERSATION_STATUS_ACTIVE,
    MESSAGE_SIDE_RECRUITER,
    OUTREACH_STATUS_SENT,
)
from app.models.identity import TimestampMixin

UUID = Uuid


class OutreachRequest(Base, TimestampMixin):
    """A company's request to contact a candidate about an opportunity.

    Ownership: ORGANIZATION requests, PERSON decides. The candidate never
    has private data exposed by the existence of a request — accepting only
    opens a controlled AskTrabaajo conversation (no phone/email/address).
    """

    __tablename__ = "outreach_requests"
    __table_args__ = (
        # One live request per (org, candidate, opportunity). Re-engaging a
        # candidate after a terminal outcome goes through a NEW request.
        UniqueConstraint(
            "organization_id", "person_id", "opportunity_id", "status",
            name="uq_outreach_org_person_opp_status",
        ),
        # One accepted outreach per conversation.
        UniqueConstraint(
            "conversation_id", name="uq_outreach_conversation"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    requester_id: Mapped[uuid.UUID] = mapped_column(
        UUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    person_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("person_profiles.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    opportunity_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID, ForeignKey("opportunities.id", ondelete="SET NULL"), index=True
    )
    application_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID, ForeignKey("job_applications.id", ondelete="SET NULL")
    )
    # Plain UUID (no FK): Conversations reference this request; pointing back
    # would create a circular FK that SQLite cannot enforce at create time.
    conversation_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID, index=True
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    context: Mapped[Optional[str]] = mapped_column(String(300))
    status: Mapped[str] = mapped_column(
        String(20), default=OUTREACH_STATUS_SENT, nullable=False
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    viewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    responded_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    note: Mapped[Optional[str]] = mapped_column(Text)


class OutreachBlock(Base, TimestampMixin):
    """A candidate's standing block against one organization's outreach."""

    __tablename__ = "outreach_blocks"
    __table_args__ = (
        UniqueConstraint(
            "person_id", "organization_id", name="uq_outreach_blocks_person_org"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    person_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("person_profiles.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    reason: Mapped[Optional[str]] = mapped_column(String(300))


class Conversation(Base, TimestampMixin):
    """A controlled AskTrabaajo conversation between an organization and a
    candidate person. Created only by a legitimate relationship."""

    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    person_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("person_profiles.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    opportunity_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID, ForeignKey("opportunities.id", ondelete="SET NULL")
    )
    application_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID, ForeignKey("job_applications.id", ondelete="SET NULL")
    )
    outreach_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID, ForeignKey("outreach_requests.id", ondelete="SET NULL")
    )
    opened_by: Mapped[uuid.UUID] = mapped_column(
        UUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(20), default=CONVERSATION_STATUS_ACTIVE, nullable=False
    )
    last_message_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), index=True
    )
    closed_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID, ForeignKey("users.id", ondelete="SET NULL")
    )
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class ConversationMessage(Base):
    """One message inside a controlled conversation."""

    __tablename__ = "conversation_messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("conversations.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    sender_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    sender_side: Mapped[str] = mapped_column(
        String(16), default=MESSAGE_SIDE_RECRUITER, nullable=False
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ConversationReadState(Base):
    """Per-user read cursor for a conversation."""

    __tablename__ = "conversation_read_states"
    __table_args__ = (
        UniqueConstraint(
            "conversation_id", "user_id", name="uq_conversation_read_state"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("conversations.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    last_read_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
