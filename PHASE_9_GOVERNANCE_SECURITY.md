# PHASE 9 — PLATFORM GOVERNANCE, REALTIME HARDENING & SECURITY

**AskTrabaajo — The Operating System for Work**

Status: **COMPLETE (implementation phase).** No Phase 10 work started.

---

## 1. Executive summary

Phase 9 adds the governance and production-hardening layer that must exist
before Athena becomes deeply integrated into AskTrabaajo:

1. **Realtime hardening** — a canonical, authorization-aware event contract and
   server-side event log. Domain services emit whitelisted *metadata-only*
   events; the polling transport is the honest Phase 9 delivery while a
   WebSocket/SSE transport can replace it without touching domain code.
2. **Rate limiting / abuse protection** — a centralized policy registry
   (`app/core/ratelimit.py`) replacing scattered inline limits. Keys are the
   authenticated user when present, else client IP; errors are generic and
   never reveal whether an account exists. In-memory limiter for single-instance
   development; the store interface is shared with the DB-backed implementation.
3. **Platform governance + admin report queue** — a report/case domain
   (categories, severities, statuses, evidence *references* only), platform
   moderator/auditor RBAC, internal notes, assignment, resolution, reopen, and
   a full audit trail. Employers, recruiters, candidates and government roles
   are proven **403** before any governance data.
4. **PostgreSQL / RLS foundation** — a reviewable RLS policy artifact
   (`app/db/rls.py`) covering the tenant-scoped schema as defense in depth.
   Application-level authorization remains mandatory; nothing was applied to
   any shared/production database.
5. **Out-of-band notification foundation** — a provider-neutral channel
   abstraction over the existing notification model (email already provider
   neutral). No commercial provider was added.

Frontend proof: `/admin/governance` queue + `/admin/governance/[id]` detail,
and event-feed polling on both communications centers.

**Result:** canonical surface is **165 `/api/v1` routes** (172 total), **132
tests green** (119 prior + 13 new), migration head **0007**, legacy backend
untouched at 107 routes.

---

## 2. Starting state

- HEAD was `844eb6a` (Phase 8 report). Working tree carried the Phase 1
  hygiene batch (untouched, uncommitted) plus clean Phase 8 commit history.
- Canonical routes: 154 `/api/v1`. Tests: **119 passing**. Migration head:
  `0006`. Legacy backend: 107 routes, untouched.
- Realtime: Phase 8 was polling-only, no event abstraction.
- Rate limiting: an in-process, IP-keyed limiter existed for auth routes only
  (`app.core.ratelimit`), no registry, no per-user keys.
- Governance: none. Audit: centralized append-only `audit_log` + request
  context (already free of message bodies/secrets by call-site convention).
- Notifications: in-app `UserNotification` + provider-neutral email service.
- No RLS artifacts existed.

## 3. Objectives

1. Safe realtime foundation (events never become an authorization bypass).
2. Centralized rate limiting with a reusable policy layer.
3. Platform governance + admin report queue with least-privilege RBAC.
4. PostgreSQL/RLS defense-in-depth foundation.
5. Out-of-band notification abstraction (foundation only).

## 4. Architecture impact

- **New domain models:** `app/models/governance.py` (reports, notes) and
  `app/models/platform.py` (events, rate-limit hits, notification
  preferences). Registered in `app/models/__init__.py`.
- **New services:** `services/events.py`, `services/governance.py`,
  `services/ratelimit_store.py`; `core/ratelimit.py` rewritten into the
  policy-registry model; `services/notifications.py` extended with the channel
  abstraction; `services/authz.py` gained a platform-scope permission helper.
- **New routers:** `api/v1/governance.py` (platform queue), `api/v1/events.py`
  (event feed). Rate-limit dependencies wired on auth, outreach, message,
  document-request and discovery endpoints; event emissions wired into
  applications, interviews, offers, outreach and conversations.
- **No** changes to legacy `api/`, Careers, or any Phase 3–8 model contract.

## 5. Realtime architecture

```
Domain service / route handler
        │  events_service.emit(db, event_type=…, recipient_user_id=… |
        │                      organization_id=…, org_scope=…, payload=…)
        ▼
platform_events (one row per event; caller owns the transaction)
        │
        ▼
GET /api/v1/events        ← polling transport (Phase 9)
   list_for_user(): the caller's direct events + org-scoped events of the
   organizations they belong to. No other rows are ever visible.
        │
        ▼  (future, unchanged contract)
WebSocket / SSE / managed realtime   ← reads the same table via the same
                                        list_for_user authorization filter
```

- **Addressing is the security boundary:** an event is addressed to *one user*
  or to an *organization* (visible to its members only). A stranger can never
  enumerate another tenant's events — even knowing event UUIDs (there is no
  single-event fetch endpoint).
- **Payloads are whitelisted metadata** — event type, resource reference,
  timestamps, sender side. Message bodies, document contents, private Work ID
  sections and audit contents are never stored in events (asserted by tests).
- **Emitted event types:** `outreach.created/accepted/declined/blocked/
  expired`, `conversation.opened`, `message.sent`, `message.read`,
  `application.updated`, `interview.updated`, `offer.updated`, `report.created`
  (controlled set in `EVENT_TYPES`; unknown types are rejected).
- **Emission sites:** outreach create/accept (candidate direct / org scope),
  recruiter message (candidate direct), candidate reply (org scope),
  application state transitions (both sides), interview schedule/complete/
  reschedule, offer send/decision.

## 6. Event model

`platform_events`: id, event_type (controlled), recipient_user_id (nullable),
organization_id (nullable), org_scope (bool), resource_type, resource_id,
actor_user_id, payload (JSON, metadata only), read_at, created_at. Indexed on
recipient, organization, and (org_scope, organization, created_at).

Read path: `list_for_user(db, user_id, after=<ISO cursor>, limit, unread_only)`
returns ascending rows for stable polling; `POST /api/v1/events/read` marks the
caller's own events read. `next_after` is the last row's timestamp.

**Transport honesty:** polling is the implemented delivery. A managed realtime
transport is *deferred infrastructure*, not implemented — documented here
rather than claimed.

## 7. Rate limiting architecture

- **Policy registry** (`RATE_LIMIT_POLICIES`) — one place per protected action:

  | Policy | Limit | Window | Key |
  |---|---|---|---|
  | login | 10 | 60 s | IP (pre-auth) |
  | mfa_verify | 5 | 60 s | IP (pre-auth) |
  | reset | 5 | 60 s | IP (pre-auth) |
  | register | 5 | 3600 s | IP (pre-auth) |
  | outreach.create | 30 | 60 s | user |
  | message.send | 60 | 60 s | user |
  | application.batch | 10 | 60 s | user |
  | document.request | 15 | 60 s | user |
  | candidates.search | 60 | 60 s | user |

- **Route declaration:** `_rl: None = Depends(rate_limit("policy.name"))` —
  no inline limit logic in handlers.
- **Keys:** authenticated actor id wins; otherwise client IP. This prevents
  cross-user scraping through a shared NAT IP and binds pre-auth actions to IP.
- **Errors:** `429 {error: {code: "rate_limited", message: "Too many
  requests…"}}` — identical regardless of the target account (tested).
- **Store:** `RateLimiter` (fixed window, in-process) is the development/test
  implementation and is safe single-instance. `RateLimitHit` +
  `DbRateLimitStore` provide a multi-instance-safe backend over the shared
  table; Redis can replace either later. **Production requirement:** a
  multi-instance deployment must back the same interface with the DB store or
  Redis — the in-process limiter alone is not production-safe (documented, not
  hidden).

## 8. Abuse protection

- Duplicate-live-request and cooldown guards on outreach (Phase 8) remain;
  Phase 9 adds per-user rate ceilings for outreach creation, message sending,
  application batch actions, document requests and discovery search.
- Generic rate-limit responses never disclose account existence or target
  details.
- Enforcement is disabled only under `settings.rate_limits_enabled=False`
  (test harness control).

## 9. Governance model

`governance_reports` — reporter_user_id, target_type (controlled set: user,
organization, opportunity, job_application, outreach_request, conversation,
message, document_request, person_profile), target_id, organization_id,
category (controlled: abuse, harassment, fraud, impersonation,
policy_violation, communication_dispute, document_misuse, recruiter_misconduct,
suspicious_activity, platform_integrity, other), severity (low/medium/high/
critical), status (open/in_review/assigned/resolved/closed), description,
evidence_refs (JSON — **references `{type,id,note}` only, contents never
accepted**), assigned_moderator_id, resolution, resolved_at, reopened_count,
timestamps.

`governance_report_notes` — internal moderator notes (author, body,
timestamps). Notes are a moderator-only surface.

## 10. Report model / 11. Admin queue

`POST /api/v1/governance/reports` — any authenticated user may file a report
against a platform object (references only). The queue:

- `GET /governance/reports` — filters: status, severity, category,
  assigned_to, organization_id; paginated (page/page_size).
- `GET /governance/dashboard` — totals by status and severity.
- `GET /governance/reports/{id}` — report + notes + audit history (audit
  timeline is read from the canonical `audit_log`).
- `PATCH /reports/{id}/status`, `POST /reports/{id}/assign`,
  `POST /reports/{id}/notes`, `POST /reports/{id}/resolve`,
  `POST /reports/{id}/reopen`.

**Least privilege:** queue/detail payloads carry report metadata and *evidence
references* — never the target's private Work ID sections or documents.
Inspecting a private Work ID requires a separate platform permission and a
legitimate governance purpose; the moderator privacy tests assert this holds.

## 12. Governance RBAC

Platform-scoped roles seeded into the catalog:
- **moderator** — reports.read/manage/assign/resolve/audit, moderation.read/
  manage, platform.audit.read.
- **governance_auditor** — read-only: reports.read/audit, moderation.read,
  platform.audit.read.
- **customer_support / finance / tech_support** — explicitly **without**
  governance permissions (tested).
- Platform scope is enforced through `authz.require_platform_permission`
  (platform-kind memberships only).

Regression-proven boundaries: employers, recruiters, candidates and
government analysts are 403 on every governance route; a platform role without
the permission cannot read or modify reports; auditors can read but cannot
resolve/assign.

## 13. Audit hardening

- No rewrite: the existing append-only `audit_log` (actor, action, resource,
  organization, request id, ip, user agent, result, payload) was extended by
  *call-site discipline* and tests.
- Governance actions (create/assign/status/notes/resolve/reopen) and the new
  communication/application/interview/offer events are recorded with
  references — never descriptions, message bodies, passwords, or tokens.
- **Tested:** every audit row in a full outreach+message+password-change
  scenario contains no `password`/`token`/`body`/`secret` keys and no raw
  message text or password values.

## 14. PostgreSQL / RLS strategy

- `app/db/rls.py` is a **policy artifact and review checklist**, not a
  runtime enabler: it enumerates the tenant-scoped tables (organizations,
  memberships, jobs, applications, interviews, offers, talent pools, saved
  candidates, outreach, conversations, messages, reports, documents, Work ID
  tables, audit log) and expresses the intended per-org/per-person policies as
  documented SQL templates (`org_tenant_id`, `person_user_id` patterns).
- Direct tenant-column coverage of the schema is verified by a self-test in
  the module (every tenant table carries its owning org/user id or is
  legitimately exempt — e.g., operational tables, catalog).
- Application-level authorization remains **mandatory**; RLS is defense in
  depth, never a replacement.
- **Not applied** to any Postgres/Supabase environment; a staged rollout under
  change control is a required decision. Policies were validated structurally
  against the schema only (no live Postgres available in this workspace).

## 15. Notification abstraction

- `notifications_service.notify(...)` now records the created entry and the
  notification model carries a `channel` dimension with a controlled set
  (in_app, email, push, sms).
- `notification_preferences` stores per-user channel preferences and consent;
  no delivery code path sends anything without consulting it.
- Email remains provider-neutral (existing `services/email.py`); **no
  provider is configured** — out-of-band delivery is foundation only.
- Safety rule enforced by convention and tests: notification text is generic
  ("A company sent you a message in AskTrabaajo"), never private Work ID data,
  documents, or message contents.

## 16. Frontend governance UI

- `/admin/governance` — dashboard cards (total, open/in review, high+critical,
  resolved), status/severity filters, paginated queue, severity/status/category
  pills, 403-aware guard.
- `/admin/governance/[id]` — report metadata, evidence references, resolution,
  assign-to-me, mark-in-review, resolve/reopen, internal notes, audit timeline.
- Both communications centers (`/company/communications`,
  `/jobseeker/communications`) now poll `/api/v1/events` (metadata only) and
  refresh on new events with a live "Updated" pulse — the polling transport the
  future WebSocket/SSE layer replaces without UI changes.
- New types: `GovernanceReportRow`, `GovernanceQueue`, `GovernanceDashboard`,
  `PlatformEventRow`, `EventsFeed`.

## 17. Security model

- Events: authorization by addressing; no cross-tenant reads; no payload
  bodies; no single-event UUID endpoint to enumerate.
- Governance: platform scope + granular permissions; moderators never gain
  Work ID access as a side effect of moderation.
- Rate limits: generic 429s, user/IP-aware keys, no account-existence oracle.
- Audit: reference-only payloads; secrets and message bodies never stored.
- Notifications: channel/consent aware; generic text.
- Documents and private Work ID sections remain behind the Phase 4 consent
  layer — untouched by Phase 9.

## 18. Tenant isolation

New tests prove: Company B sees **zero** of Company A's events; org-scoped
events reach exactly the members of that org (a candidate who is not a member
does not receive the org's `outreach.accepted`/`message.sent` events even
though the conversation concerns them); cross-tenant conversation access by
known UUID is 403/404. Employer access to the governance queue is 403
regardless of tenant.

## 19. Test strategy

Two new suites:
- `test_governance_phase9.py` (8 tests): filing (references only), employer/
  recruiter/candidate and government access denial, platform-role-without-
  permission denial, auditor read-only, moderator full lifecycle + audit
  trail hygiene, moderator cannot read private Work ID, queue never echoes
  target documents.
- `test_security_phase9.py` (5 tests): event-feed tenant isolation +
  cross-tenant UUID access denial; events never leak message contents; audit
  rows contain no secrets/message bodies; login rate limit activates with
  identical generic 429 for existing vs non-existent accounts; outreach rate
  limit trips with a generic error.

Hostile paths assumed: tests act as attackers who know UUIDs and routes.

## 20. Test results

- Previous count: **119** (Phases 3–8). New: **13**. Total: **132 passed, 0
  failed** (`pytest tests_phase3/`, ~92 s).
- Canonical routes: **165 `/api/v1`** (+11: governance queue/detail/actions/
  dashboard + events feed + read) — 172 total including health/docs.
- Legacy backend: still imports, **107 routes**, untouched.
- Frontend: `tsc --noEmit` clean; `next lint` 0 errors (5 pre-existing
  warnings in untouched Phase-1 careers components); production build green
  including both `/admin/governance` routes.

## 21. Migration details

`0007_governance_security.py` — strictly additive. Creates 5 tables:
`governance_reports`, `governance_report_notes`, `platform_events`,
`rate_limit_hits`, `notification_preferences` (53 → 58 tables), plus indexes
and catalog seeds (moderator / governance_auditor roles and the reports.*,
moderation.*, platform.audit.read permissions).

Validated on scratch SQLite: `upgrade head` → `downgrade 0006` →
`re-upgrade head` — all clean. **Applied to nothing shared/production.**

## 22. Production readiness

**Ready:** canonical API, additive migration, ownership model, event contract,
policy-registry rate limiting, governance RBAC, tests, proof UI.

**Not ready (requires external infrastructure / change control):**
- Managed realtime transport (WebSocket/SSE) — event contract is ready.
- Distributed rate limiting (Redis or the DB store) — interface is ready.
- PostgreSQL RLS enforcement — artifact is ready; needs a Postgres review
  environment and staged rollout.
- Out-of-band notification providers (email/push/SMS) — abstraction is ready;
  no provider configured.
- Platform-admin *assignment workflow UX* beyond the proof screens (e.g.,
  moderator roster picker), report escalation SLAs.

## 23. Known limitations

- Events are delivered by polling (12 s UI interval); no push.
- No message attachments; no realtime presence; no read receipts beyond
  in-app unread counts.
- Lazy expiry — expired outreach/interview events depend on a future
  scheduler or on-demand checks.
- RLS artifact is validated structurally, not against a live Postgres.
- In-process rate limiter is single-instance only (documented production
  requirement above).
- Report filing has no per-category throttles beyond the generic rate limits.
- No admin moderation UI for *reporters'/targets'* full context (by design —
  least privilege).

## 24. Deferred work

- Managed realtime transport and client subscription layer.
- Redis-backed or DB-backed distributed rate limiting in a deployed
  environment.
- Live-Postgres RLS enablement + permission matrix review.
- Provider integration for email/push/SMS + preference UX.
- Governance SLA/priority engine, moderator teams, appeal flow.
- Platform audit *review* UI (the permission exists: platform.audit.read).

## 25. Compatibility with Phases 3–8

- All Phase 3–8 models, routes and tests pass unchanged (132 total).
- Matching, applications, interviews, offers, outreach, communications,
  documents, Work ID consent — untouched contracts; only additive event
  emissions and rate-limit dependencies were added.
- Notification/audit services extended additively.

## 26. Careers compatibility

Untouched. Legacy Careers corpus, frontend and Supabase-facing code were not
modified by Phase 9; the legacy backend still imports at its existing route
count.

## 27. Government privacy boundaries

Government roles are **403** on platform governance (tested). Governance data
(moderation) is deliberately distinct from government aggregate analytics and
individual Work ID data; no Phase 9 path mixes them. Individual-level
government access remains out of scope platform-wide.

## 28. Athena dependency/readiness

Athena integration is the *next* phase after governance because Athena's tools
must operate through exactly these controls: permissioned service operations
(gov queue reads only with reports.read; events only via list_for_user;
rate-limited actions returning the same generic errors). Phase 9 provides the
safe substrate: events it can subscribe to, a governance queue it can be
granted read tools on, and rate-limit/governance boundaries it cannot bypass.

## 29. Decisions requiring approval

1. **Approve Phase 9.**
2. **Migration `0007` on a shared environment** — staging-first rollout under
   change control; downgrade path is `alembic downgrade 0006`.
3. **Realtime transport choice** for Phase 10 — polling remains acceptable;
   WebSocket/SSE adoption is a product/deployment decision.
4. **Rate-limit store for multi-instance deployment** — Redis vs the DB store.
5. **Out-of-band notification provider** (email provider selection, consent
   UX) before any live delivery.
6. **Postgres RLS enablement scope** — which tables first, staged.
7. Carried items remain: the Phase 1 hygiene batch (untouched) and external
   credential rotation.

## 30. Exact git/change summary

Phase 9 commits (to be created; see below), nothing pushed. See the final
delivery message for exact commit SHAs, HEAD, working-tree state, and the
confirmation that the carried Phase 1 hygiene batch is untouched.

### Files created
- `backend/alembic/versions/0007_governance_security.py`
- `backend/app/api/v1/events.py`, `backend/app/api/v1/governance.py`
- `backend/app/db/rls.py`
- `backend/app/models/governance.py`, `backend/app/models/platform.py`
- `backend/app/schemas/governance.py`
- `backend/app/services/events.py`, `backend/app/services/governance.py`,
  `backend/app/services/ratelimit_store.py`
- `backend/tests_phase3/test_governance_phase9.py`,
  `backend/tests_phase3/test_security_phase9.py`
- `frontend/src/app/admin/layout.tsx`,
  `frontend/src/app/admin/governance/page.tsx`,
  `frontend/src/app/admin/governance/[id]/page.tsx`

### Files modified
- Backend: `api/v1/{company,jobseeker,router,talent}.py`,
  `core/{config,ratelimit}.py`, `main.py`,
  `models/{__init__,catalog,enums}.py`,
  `services/{applications,authz,company_os,notifications}.py`
- Frontend: `src/lib/api/types.ts`,
  `src/app/company/communications/page.tsx`,
  `src/app/jobseeker/communications/page.tsx`
