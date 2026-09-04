"""Athena orchestration service (Phase 14).

Flow per user message:

  auth -> session -> context builder -> policy/tool-scope check ->
  provider (tools = registered registry only) -> per-tool authorization
  -> canonical application service -> result -> audit -> reply

The model output is NEVER treated as authorization. Tool selection is
validated against the registry; permissions are enforced in code;
high-risk tools execute only after an explicit, unexpired user
confirmation for the exact canonical scope.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core import context as request_context
from app.core.config import get_settings
from app.core.errors import AppError, InvalidInputError, NotFoundError, PermissionDeniedError
from app.core.timeutil import utc_now_naive
from app.models.athena import (
    AiUsageLog,
    AthenaActionConfirmation,
    AthenaMessage,
    AthenaSession,
)
from app.models.enums import (
    AI_ERROR_INTERNAL,
    AI_ERROR_RATE_LIMITED,
    AI_ERROR_TOOL_VALIDATION_FAILED,
    ATHENA_CONFIRMATION_STATUS_APPROVED,
    ATHENA_CONFIRMATION_STATUS_DENIED,
    ATHENA_CONFIRMATION_STATUS_EXPIRED,
    ATHENA_CONFIRMATION_STATUS_PENDING,
    ATHENA_MODE_EMPLOYER,
    ATHENA_MODE_GOVERNMENT,
    ATHENA_MODE_JOBSEEKER,
    ATHENA_MODE_PLATFORM_OPERATOR,
    ATHENA_MODE_RECRUITER,
    ATHENA_MODES,
    ATHENA_MESSAGE_ROLE_ASSISTANT,
    ATHENA_MESSAGE_ROLE_SYSTEM,
    ATHENA_MESSAGE_ROLE_TOOL,
    ATHENA_MESSAGE_ROLE_USER,
    ATHENA_RISK_HIGH_RISK_WRITE,
    ATHENA_SESSION_STATUS_ACTIVE,
    ATHENA_SESSION_STATUS_CLOSED,
    ATHENA_SESSION_STATUS_EXPIRED,
    AUDIT_ACTION_ATHENA_CONFIRMATION_DECIDED,
    AUDIT_ACTION_ATHENA_CONFIRMATION_EXPIRED,
    AUDIT_ACTION_ATHENA_CONFIRMATION_REQUESTED,
    AUDIT_ACTION_ATHENA_MESSAGE,
    AUDIT_ACTION_ATHENA_SESSION_CREATED,
    AUDIT_ACTION_ATHENA_TOOL_DENIED,
    AUDIT_ACTION_ATHENA_TOOL_EXECUTED,
)
from app.models.identity import PersonProfile, User
from app.models.tenancy import Membership
from app.services import athena_context
from app.services import authz
from app.services.ai_provider import AIProvider, get_provider, provider_unavailable
from app.services.athena_tools import AthenaTool, get_tool
from app.services.audit import record as audit_record


def _utcnow() -> datetime:
    """Naive UTC now — safe against naive values returned by SQLite."""
    return utc_now_naive()


def _coerce(dt: Optional[datetime]) -> Optional[datetime]:
    """Normalize a stored timestamp to naive UTC for comparisons.

    SQLite returns naive values; PostgreSQL (timestamptz) returns tz-aware
    values. Comparisons in this module always run in naive UTC."""
    if dt is None:
        return None
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def _scope_hash(args: Dict) -> str:
    canonical = json.dumps(args, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# --- Mode eligibility ----------------------------------------------------------

def available_modes(db: Session, user: User) -> List[str]:
    modes = []
    person = db.scalars(
        select(PersonProfile).where(PersonProfile.user_id == user.id)
    ).first()
    if person is not None:
        modes.append(ATHENA_MODE_JOBSEEKER)
    memberships = db.scalars(
        select(Membership).where(Membership.user_id == user.id)
    ).all()
    eligible_org_roles = {"recruiter", "hr", "hiring_manager", "org_admin"}
    for m in memberships:
        if m.role_code in eligible_org_roles:
            modes.append(ATHENA_MODE_EMPLOYER)
            modes.append(ATHENA_MODE_RECRUITER)
        if m.role_code in {"government_admin", "government_user"}:
            modes.append(ATHENA_MODE_GOVERNMENT)
    if authz.is_platform_super_admin(db, user.id):
        modes.append(ATHENA_MODE_PLATFORM_OPERATOR)
    # De-duplicate, preserve canonical order.
    return [m for m in ATHENA_MODES if m in modes]


def _eligible_org_for_mode(db: Session, user: User, mode: str) -> Optional[uuid.UUID]:
    """Org context required for employer/recruiter modes (first eligible)."""
    if mode not in (ATHENA_MODE_EMPLOYER, ATHENA_MODE_RECRUITER):
        return None
    eligible_org_roles = {"recruiter", "hr", "hiring_manager", "org_admin"}
    memberships = db.scalars(
        select(Membership).where(Membership.user_id == user.id)
    ).all()
    for m in memberships:
        if m.role_code in eligible_org_roles:
            return m.organization_id
    return None


def create_session(
    db: Session,
    user: User,
    mode: str,
    purpose: Optional[str] = None,
    organization_id: Optional[uuid.UUID] = None,
) -> AthenaSession:
    if mode not in ATHENA_MODES:
        raise InvalidInputError(f"Unknown Athena mode '{mode}'.")
    if mode not in available_modes(db, user):
        raise PermissionDeniedError("This Athena mode is not available to this account.")
    if mode in (ATHENA_MODE_EMPLOYER, ATHENA_MODE_RECRUITER):
        resolved_org = organization_id or _eligible_org_for_mode(db, user, mode)
        if resolved_org is None:
            raise PermissionDeniedError("An organization membership is required for this mode.")
        membership = db.scalars(
            select(Membership).where(
                Membership.user_id == user.id,
                Membership.organization_id == resolved_org,
            )
        ).first()
        if membership is None:
            raise PermissionDeniedError("This account is not a member of that organization.")
        organization_id = resolved_org

    settings = get_settings()
    session = AthenaSession(
        user_id=user.id,
        organization_id=organization_id,
        mode=mode,
        purpose=(purpose or "")[:240] or None,
        status=ATHENA_SESSION_STATUS_ACTIVE,
        correlation_id=request_context.request_meta().get("request_id"),
        expires_at=_utcnow() + timedelta(minutes=settings.athena_session_ttl_minutes),
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    audit_record(
        db,
        actor_id=user.id,
        action=AUDIT_ACTION_ATHENA_SESSION_CREATED,
        resource_type="athena_session",
        resource_id=str(session.id),
        organization_id=organization_id,
        metadata={"mode": mode},
    )
    db.commit()
    return session


def get_owned_session(db: Session, user: User, session_id: uuid.UUID) -> AthenaSession:
    session = db.get(AthenaSession, session_id)
    if session is None or session.user_id != user.id:
        raise NotFoundError("Athena session not found.")
    _expire_session_if_stale(db, session)
    return session


def _expire_session_if_stale(db: Session, session: AthenaSession) -> None:
    if session.status != ATHENA_SESSION_STATUS_ACTIVE:
        return
    settings = get_settings()
    if session.expires_at and _coerce(session.expires_at) < _utcnow():
        session.status = ATHENA_SESSION_STATUS_EXPIRED
        db.commit()


def close_session(db: Session, user: User, session_id: uuid.UUID) -> AthenaSession:
    session = get_owned_session(db, user, session_id)
    if session.status == ATHENA_SESSION_STATUS_ACTIVE:
        session.status = ATHENA_SESSION_STATUS_CLOSED
        session.closed_at = _utcnow()
        db.commit()
        db.refresh(session)
    return session


# --- Usage + rate limits -------------------------------------------------------

def _check_limiter(limiters, name: str, key: str) -> None:
    from app.core.config import get_settings as _settings

    if not _settings().rate_limits_enabled or not limiters:
        return
    limiter = limiters.get(name)
    if limiter is not None:
        limiter.check(key)


def _user_key(user: User) -> str:
    return f"user:{user.id}"


def _daily_budget(db: Session, user: User, feature_prefix: str, limit: int) -> None:
    """Per-user daily AI usage budget over ai_usage_log (deterministic)."""
    if limit <= 0:
        return
    start = _utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    count = db.scalar(
        select(func.count(AiUsageLog.id)).where(
            AiUsageLog.user_id == user.id,
            AiUsageLog.created_at >= start,
            AiUsageLog.feature.like(f"{feature_prefix}%"),
            AiUsageLog.status == "success",
        )
    )
    if (count or 0) >= limit:
        raise AppError(
            "Daily AI usage limit reached for this account.",
            status_code=429,
            code=AI_ERROR_RATE_LIMITED,
        )


def _record_usage(
    db: Session,
    *,
    user: Optional[User],
    session: Optional[AthenaSession],
    feature: str,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    latency_ms: Optional[int] = None,
    status: str = "success",
    error_code: Optional[str] = None,
) -> None:
    total = prompt_tokens + completion_tokens
    db.add(
        AiUsageLog(
            user_id=user.id if user else None,
            organization_id=session.organization_id if session else None,
            session_id=session.id if session else None,
            mode=session.mode if session else None,
            feature=feature,
            provider=provider,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total,
            latency_ms=latency_ms,
            status=status,
            error_code=error_code,
        )
    )
    db.commit()


# --- Tool authorization + execution --------------------------------------------

def _authorize_tool(db: Session, user: User, session: AthenaSession, tool: AthenaTool) -> None:
    """Authorization is enforced here, in application code — never by the model."""
    if session.status != ATHENA_SESSION_STATUS_ACTIVE:
        raise PermissionDeniedError("This Athena session is no longer active.")
    if session.mode not in tool.modes:
        raise PermissionDeniedError(
            f"Tool '{tool.name}' is not available in {session.mode} mode."
        )
    if tool.permission is not None:
        if session.organization_id is None:
            raise PermissionDeniedError("Organization context is required for this tool.")
        authz.require_permission(
            db, user.id, tool.permission, session.organization_id
        )


def _audit_tool(
    db: Session,
    user: User,
    session: AthenaSession,
    tool_name: str,
    action: str,
    result: str,
    details: Dict,
) -> None:
    audit_record(
        db,
        actor_id=user.id,
        action=action,
        resource_type="athena_tool",
        resource_id=tool_name,
        organization_id=session.organization_id,
        metadata=details,
        result=result,
    )
    db.commit()


def execute_tool(
    db: Session,
    user: User,
    session: AthenaSession,
    tool_name: str,
    args: Dict,
    *,
    limiters=None,
) -> Dict:
    """Authorize + execute one tool call. High-risk tools return a
    confirmation request instead of executing."""
    tool = get_tool(tool_name)
    if tool is None:
        _audit_tool(
            db, user, session, tool_name, AUDIT_ACTION_ATHENA_TOOL_DENIED, "denied",
            {"reason": "tool_not_registered"},
        )
        raise PermissionDeniedError(f"Tool '{tool_name}' is not registered.")
    # Structured-output validation: model arguments must satisfy the tool's
    # declared input schema before ANY authorization or execution.
    try:
        parsed = tool.input_model.model_validate(args or {})
    except Exception as exc:
        _audit_tool(
            db, user, session, tool.name, AUDIT_ACTION_ATHENA_TOOL_DENIED, "denied",
            {"reason": "tool_validation_failed"},
        )
        raise AppError(
            "Tool arguments failed validation.",
            status_code=422,
            code=AI_ERROR_TOOL_VALIDATION_FAILED,
        ) from exc
    args = parsed.model_dump()
    _authorize_tool(db, user, session, tool)

    if tool.risk == ATHENA_RISK_HIGH_RISK_WRITE:
        _check_limiter(limiters, "athena.high_risk", _user_key(user))
        return _handle_high_risk(db, user, session, tool, args, limiters=limiters)

    _check_limiter(limiters, "athena.tool", _user_key(user))
    result = tool.handler(db, user, session, session.organization_id, args)
    db.commit()
    _audit_tool(
        db, user, session, tool.name, AUDIT_ACTION_ATHENA_TOOL_EXECUTED, "success",
        {
            "mode": session.mode,
            "risk": tool.risk,
            "read_only": tool.read_only,
            "result_keys": sorted(result.keys()),
        },
    )
    _record_usage(
        db, user=user, session=session, feature=f"athena.tool.{tool.name}",
        status="success",
    )
    return {"status": "ok", "tool": tool.name, "result": result}


def _handle_high_risk(
    db: Session,
    user: User,
    session: AthenaSession,
    tool: AthenaTool,
    args: Dict,
    *,
    limiters,
) -> Dict:
    """High-risk write: execute only when an APPROVED, unexpired
    confirmation for the exact canonical scope exists; otherwise create a
    pending confirmation (or return the existing one)."""
    scope_hash = _scope_hash(args)
    settings = get_settings()

    # 1. Approved, unexpired confirmation for this exact scope?
    approved = db.scalars(
        select(AthenaActionConfirmation).where(
            AthenaActionConfirmation.session_id == session.id,
            AthenaActionConfirmation.tool_name == tool.name,
            AthenaActionConfirmation.scope_hash == scope_hash,
            AthenaActionConfirmation.status == ATHENA_CONFIRMATION_STATUS_APPROVED,
        )
    ).first()
    if approved is not None and (approved.expires_at is None or _coerce(approved.expires_at) > _utcnow()):
        result = tool.handler(db, user, session, session.organization_id, args)
        approved.result = {"status": "executed"}
        db.commit()
        _audit_tool(
            db, user, session, tool.name, AUDIT_ACTION_ATHENA_TOOL_EXECUTED, "success",
            {"mode": session.mode, "risk": tool.risk, "authorization": "approved_confirmation"},
        )
        _record_usage(
            db, user=user, session=session, feature=f"athena.tool.{tool.name}",
            status="success",
        )
        return {"status": "ok", "tool": tool.name, "result": result}

    # 2. Existing pending confirmation (do not duplicate).
    pending = db.scalars(
        select(AthenaActionConfirmation).where(
            AthenaActionConfirmation.session_id == session.id,
            AthenaActionConfirmation.tool_name == tool.name,
            AthenaActionConfirmation.scope_hash == scope_hash,
            AthenaActionConfirmation.status == ATHENA_CONFIRMATION_STATUS_PENDING,
        )
    ).first()
    if pending is not None:
        if pending.expires_at and _coerce(pending.expires_at) <= _utcnow():
            pending.status = ATHENA_CONFIRMATION_STATUS_EXPIRED
            db.commit()
        else:
            return {
                "status": "confirmation_required",
                "confirmation_id": str(pending.id),
                "tool": tool.name,
                "action_summary": pending.action_summary,
                "expires_at": pending.expires_at.isoformat() if pending.expires_at else None,
            }

    # 3. Create a new pending confirmation. The stored scope is JSON-safe
    # (UUIDs stringified) so the JSON column round-trips on every dialect;
    # confirm_action re-validates it through the tool schema before running.
    summary = (
        f"{tool.name}({', '.join(f'{k}={v}' for k, v in sorted(args.items()))})"
    )[:300]
    json_safe_args = json.loads(json.dumps(args, default=str))
    confirmation = AthenaActionConfirmation(
        session_id=session.id,
        user_id=user.id,
        organization_id=session.organization_id,
        tool_name=tool.name,
        action_summary=summary,
        scope=json_safe_args,
        scope_hash=scope_hash,
        risk_level=tool.risk,
        status=ATHENA_CONFIRMATION_STATUS_PENDING,
        expires_at=_utcnow() + timedelta(minutes=settings.athena_confirmation_ttl_minutes),
    )
    db.add(confirmation)
    db.commit()
    db.refresh(confirmation)
    _audit_tool(
        db, user, session, tool.name, AUDIT_ACTION_ATHENA_CONFIRMATION_REQUESTED, "success",
        {
            "mode": session.mode,
            "risk": tool.risk,
            "confirmation_id": str(confirmation.id),
            "scope_hash": scope_hash,
        },
    )
    _record_usage(
        db, user=user, session=session, feature=f"athena.tool.{tool.name}",
        status="success",
    )
    return {
        "status": "confirmation_required",
        "confirmation_id": str(confirmation.id),
        "tool": tool.name,
        "action_summary": summary,
        "expires_at": confirmation.expires_at.isoformat() if confirmation.expires_at else None,
    }


def confirm_action(
    db: Session,
    user: User,
    confirmation_id: uuid.UUID,
    approve: bool,
    *,
    limiters=None,
) -> Dict:
    """Approve/deny a pending high-risk tool confirmation.

    Approval is the execution trigger: the stored canonical scope is
    re-authorized and executed now. Denial only records the decision.
    """
    confirmation = db.get(AthenaActionConfirmation, confirmation_id)
    if confirmation is None or confirmation.user_id != user.id:
        raise NotFoundError("Confirmation not found.")
    session = db.get(AthenaSession, confirmation.session_id)
    if session is None or session.user_id != user.id:
        raise NotFoundError("Athena session not found.")
    _expire_session_if_stale(db, session)
    if session.status != ATHENA_SESSION_STATUS_ACTIVE:
        raise PermissionDeniedError("This Athena session is no longer active.")

    if confirmation.status != ATHENA_CONFIRMATION_STATUS_PENDING:
        raise InvalidInputError(
            f"Confirmation is already {confirmation.status} (stale)."
        )
    if confirmation.expires_at and _coerce(confirmation.expires_at) <= _utcnow():
        confirmation.status = ATHENA_CONFIRMATION_STATUS_EXPIRED
        confirmation.decided_at = _utcnow()
        db.commit()
        _audit_tool(
            db, user, session, confirmation.tool_name,
            AUDIT_ACTION_ATHENA_CONFIRMATION_EXPIRED, "denied",
            {"confirmation_id": str(confirmation.id)},
        )
        raise InvalidInputError("Confirmation has expired; please request the action again.")

    _check_limiter(limiters, "athena.high_risk", _user_key(user))

    confirmation.decided_by = user.id
    confirmation.decided_at = _utcnow()

    if not approve:
        confirmation.status = ATHENA_CONFIRMATION_STATUS_DENIED
        db.commit()
        _audit_tool(
            db, user, session, confirmation.tool_name,
            AUDIT_ACTION_ATHENA_CONFIRMATION_DECIDED, "denied",
            {"confirmation_id": str(confirmation.id), "decision": "denied"},
        )
        return {"status": "denied", "confirmation_id": str(confirmation.id)}

    # Approve: re-authorize, then execute the stored canonical scope.
    tool = get_tool(confirmation.tool_name)
    if tool is None:
        confirmation.status = ATHENA_CONFIRMATION_STATUS_CANCELLED
        db.commit()
        raise PermissionDeniedError("The underlying tool is no longer registered.")
    try:
        _authorize_tool(db, user, session, tool)
    except PermissionDeniedError:
        confirmation.status = ATHENA_CONFIRMATION_STATUS_DENIED
        db.commit()
        raise

    confirmation.status = ATHENA_CONFIRMATION_STATUS_APPROVED
    db.commit()
    # The stored scope round-tripped through JSON (strings) — re-validate it
    # through the tool's input schema so handlers always receive canonical
    # types (e.g. UUID) exactly as in the live tool-call path.
    try:
        parsed_scope = tool.input_model.model_validate(confirmation.scope)
    except Exception as exc:
        confirmation.status = ATHENA_CONFIRMATION_STATUS_DENIED
        db.commit()
        raise AppError(
            "Stored confirmation scope failed validation.",
            status_code=422,
            code=AI_ERROR_TOOL_VALIDATION_FAILED,
        ) from exc
    result = tool.handler(
        db, user, session, session.organization_id, parsed_scope.model_dump()
    )
    confirmation.result = {"status": "executed"}
    db.commit()
    _audit_tool(
        db, user, session, tool.name, AUDIT_ACTION_ATHENA_TOOL_EXECUTED, "success",
        {
            "mode": session.mode,
            "risk": tool.risk,
            "authorization": "user_confirmation",
            "confirmation_id": str(confirmation.id),
        },
    )
    _record_usage(
        db, user=user, session=session, feature=f"athena.tool.{tool.name}",
        status="success",
    )
    return {
        "status": "approved_and_executed",
        "confirmation_id": str(confirmation.id),
        "tool": tool.name,
        "result": result,
    }


# --- Chat orchestration --------------------------------------------------------

def _recent_messages(db: Session, session_id: uuid.UUID, limit: int = 30) -> List[Dict]:
    rows = db.scalars(
        select(AthenaMessage)
        .where(AthenaMessage.session_id == session_id)
        .order_by(AthenaMessage.created_at.desc())
        .limit(limit)
    ).all()
    out = []
    for row in reversed(rows):
        if row.role == ATHENA_MESSAGE_ROLE_SYSTEM:
            continue
        entry: Dict = {"role": row.role, "content": row.content or ""}
        if row.tool_calls:
            entry["tool_calls"] = row.tool_calls
        out.append(entry)
    return out


def chat(
    db: Session,
    user: User,
    session: AthenaSession,
    text: str,
    *,
    provider: Optional[AIProvider] = None,
    limiters=None,
) -> Dict:
    """One user message -> Athena reply (with bounded tool loop)."""
    session = get_owned_session(db, user, session.id)
    if session.status != ATHENA_SESSION_STATUS_ACTIVE:
        raise InvalidInputError("This Athena session is no longer active.")
    settings = get_settings()
    _check_limiter(limiters, "athena.chat", _user_key(user))
    _daily_budget(db, user, "athena.chat", settings.athena_daily_messages_per_user)

    provider = provider or get_provider()
    if provider is None:
        raise provider_unavailable()

    digest = (
        athena_context.build_profile_digest(db, user)
        if session.mode == ATHENA_MODE_JOBSEEKER
        else athena_context.build_org_digest(db, session.organization_id)
    )
    system_prompt = athena_context.build_system_prompt(session.mode, digest)
    db.add(
        AthenaMessage(
            session_id=session.id,
            role=ATHENA_MESSAGE_ROLE_SYSTEM,
            content=system_prompt,
        )
    )
    db.add(
        AthenaMessage(
            session_id=session.id,
            role=ATHENA_MESSAGE_ROLE_USER,
            content=text[:4000],
        )
    )
    db.commit()

    messages: List[Dict] = [{"role": "system", "content": system_prompt}]
    messages.extend(_recent_messages(db, session.id))
    tools_schemas = (
        _tool_schemas_for_mode(session.mode) if session.mode in {"jobseeker", "employer", "recruiter"} else []
    )

    tool_results: List[Dict] = []
    pending_confirmations: List[Dict] = []
    final_reply: Optional[str] = None

    for _turn in range(settings.ai_chat_max_turns):
        response = provider.chat(messages, tools=tools_schemas)
        _record_usage(
            db,
            user=user,
            session=session,
            feature="athena.chat",
            provider=getattr(provider, "name", None),
            model=response.model,
            prompt_tokens=response.usage.prompt_tokens,
            completion_tokens=response.usage.completion_tokens,
            latency_ms=None,
        )
        if not response.tool_calls:
            final_reply = response.content or ""
            db.add(
                AthenaMessage(
                    session_id=session.id,
                    role=ATHENA_MESSAGE_ROLE_ASSISTANT,
                    content=final_reply,
                    provider_model=response.model,
                )
            )
            db.commit()
            break

        # Persist the assistant tool-call envelope (structured, validated).
        envelope = [
            {"id": tc.id, "name": tc.name, "arguments": tc.arguments}
            for tc in response.tool_calls
        ]
        db.add(
            AthenaMessage(
                session_id=session.id,
                role=ATHENA_MESSAGE_ROLE_ASSISTANT,
                content=None,
                tool_calls=envelope,
                provider_model=response.model,
            )
        )
        db.commit()
        messages.append({"role": "assistant", "tool_calls": envelope})

        for tc in response.tool_calls:
            try:
                outcome = execute_tool(
                    db, user, session, tc.name, tc.arguments, limiters=limiters
                )
            except AppError as exc:
                outcome = {
                    "status": "error",
                    "tool": tc.name,
                    "error_code": getattr(exc, "code", AI_ERROR_INTERNAL),
                    "message": str(exc),
                }
            if outcome.get("status") == "confirmation_required":
                pending_confirmations.append(
                    {
                        "confirmation_id": outcome["confirmation_id"],
                        "tool": outcome["tool"],
                        "action_summary": outcome["action_summary"],
                        "expires_at": outcome.get("expires_at"),
                    }
                )
                messages.append(
                    {
                        "role": ATHENA_MESSAGE_ROLE_TOOL,
                        "tool_call_id": tc.id,
                        "content": json.dumps(
                            {"status": "confirmation_required", "confirmation_id": outcome["confirmation_id"]}
                        ),
                    }
                )
                continue
            tool_results.append(outcome)
            messages.append(
                {
                    "role": ATHENA_MESSAGE_ROLE_TOOL,
                    "tool_call_id": tc.id,
                    "content": json.dumps(outcome.get("result", outcome), default=str)[:4000],
                }
            )

        if pending_confirmations:
            # Stop the loop: a human decision is required before continuing.
            final_reply = (
                "I found an action that requires your explicit confirmation before it can "
                "proceed. Please review and confirm it in the platform."
            )
            db.add(
                AthenaMessage(
                    session_id=session.id,
                    role=ATHENA_MESSAGE_ROLE_ASSISTANT,
                    content=final_reply,
                    provider_model=response.model,
                )
            )
            db.commit()
            break

    if final_reply is None:
        final_reply = "I could not complete that request within the allowed steps. Please try again."

    session.last_active_at = _utcnow()
    db.commit()
    audit_record(
        db,
        actor_id=user.id,
        action=AUDIT_ACTION_ATHENA_MESSAGE,
        resource_type="athena_session",
        resource_id=str(session.id),
        organization_id=session.organization_id,
        metadata={
            "mode": session.mode,
            "tool_results": len(tool_results),
            "pending_confirmations": len(pending_confirmations),
        },
    )
    db.commit()

    return {
        "session_id": str(session.id),
        "reply": final_reply,
        "tool_results": tool_results,
        "pending_confirmations": pending_confirmations,
        "error": None,
    }


def _tool_schemas_for_mode(mode: str) -> List[Dict]:
    from app.services.athena_tools import tool_schemas

    return tool_schemas({mode})


def list_pending_confirmations(
    db: Session, user: User, session_id: uuid.UUID
) -> List[Dict]:
    session = get_owned_session(db, user, session_id)
    rows = db.scalars(
        select(AthenaActionConfirmation).where(
            AthenaActionConfirmation.session_id == session.id,
            AthenaActionConfirmation.user_id == user.id,
            AthenaActionConfirmation.status == ATHENA_CONFIRMATION_STATUS_PENDING,
        )
    ).all()
    return [
        {
            "confirmation_id": str(c.id),
            "tool": c.tool_name,
            "action_summary": c.action_summary,
            "expires_at": c.expires_at.isoformat() if c.expires_at else None,
        }
        for c in rows
    ]