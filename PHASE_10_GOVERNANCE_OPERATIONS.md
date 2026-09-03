# PHASE 10 — GOVERNANCE OPERATIONS & PLATFORM CONTROL ROOM

**AskTrabaajo — The Operating System for Work**

Status: **COMPLETE (implementation phase).** No Phase 11 work started.

---

## 1. Executive summary

Phase 10 turns the Phase 9 governance foundation into an operational
**Platform Control Room** — the internal nervous system for platform
integrity — while keeping the privacy architecture from Phases 3–9 intact:

- The governance report row is extended into the operational **case model**
  (no second moderation system): explicit **priority** (separate from
  severity), **governance-team routing**, **escalation markers**, **case
  links** for duplicate investigations, and a **deterministic, lazy SLA
  policy** derived from priority (no scheduler).
- **Governance teams** (8 seeded, idempotent) organise the queue; team-aware
  assignment routes cases to the right moderators.
- **Platform audit review** — a filtered, paginated operational interface over
  the canonical audit log with server-side payload sanitisation (no
  passwords/tokens/secrets/message bodies).
- **Neutral integrity signals** computed from existing data ("review
  required", never an accusation).
- Governance actions emit **metadata-only platform events** and **generic
  governance notifications** through the Phase 9 abstractions.
- Frontend proof: the **Control Room** (operational dashboard + queue views),
  **case detail** (SLA banner, priority, team, escalate, links, lifecycle),
  **team view**, and **audit review**.

**Result:** canonical surface is **177 `/api/v1` routes** (+12), **143 tests
green** (132 prior + 11 new), migration head **0008**, legacy backend
untouched at 107 routes.

## 2. Starting state

- HEAD `3daf2a7` (Phase 9). Working tree carried only the untouched Phase 1
  hygiene batch (63 entries).
- Routes: 165 `/api/v1`. Tests: **132 passing**. Migration head `0007`.
- Phase 9 governance: reports/notes, moderator + governance_auditor roles,
  queue/dashboard endpoints, audit trail, no priority/teams/SLA/escalation/
  links/signals/audit-review.
- Governance teams existed nowhere (models, migration or seeds).

## 3. Objectives

1. Operational case model on top of the existing governance report.
2. Lightweight governance teams (not an HR system).
3. Audited assignment / reassignment / team-aware routing.
4. Priority separate from severity + deterministic SLA + lazy state.
5. Controlled escalation.
6. Platform audit review UI/API.
7. Operational dashboard + case queue + case detail + team view + my work.
8. Linked reports, evidence references preserved, neutral integrity signals.
9. Governance event/notification integration; extended RBAC.
10. Security regression suite; additive migration 0008.

## 4. Governance architecture

```
Reports (any authenticated user)            Moderators (platform scope)
        │                                            │
        ▼                                            ▼
┌──────────────────────────────────────────────────────────────┐
│ governance_reports = the CASE (one authoritative row)         │
│  + priority      (low/normal/high/urgent/critical)            │
│  + team_id       → governance_teams (routing, not authz)      │
│  + escalation markers (escalated_at / by / to_team)           │
│  + first_responded_at                                         │
│  + sla_response_due_at / sla_resolution_due_at (deterministic)│
│  + evidence_refs (references only)                            │
│  + governance_case_links (same-tenant duplicate investigations)│
└───────────────────────────────────────────────────────────────┘
        │                                    │
        ▼                                    ▼
 audit_log (reference-only)          platform_events (metadata-only)
 notifications (generic, governance kind)
```

## 5. Team model

`governance_teams` (slug unique, name, description) + `governance_team_members`
(team, user, created_by, unique per pair). Eight seeded teams:
platform_safety, fraud, employer_integrity, candidate_integrity,
communications, document_trust, technical_abuse, general_support. Teams are
**operational grouping only** — authorization stays on platform-scope roles
and `reports.*` permissions.

## 6. Assignment model

- `POST /reports/{id}/assign` (assignee optional → self) — assign/reassign.
- **Team-aware:** a case routed to a team can only be assigned to a moderator
  who is a member of that team (prevents cross-team misrouting). Assigning a
  non-governance user is refused; the assignee must hold `reports.read`.
- Unassignment = `assign` with no moderator / assignee cleared by the UI.
- Every assignment is audited (`governance.report.assigned`), emits a
  `governance.case.assigned` event, and notifies the assignee (generic
  message, no case content) when the assignee is not the actor.
- `GET /governance/moderators` returns governance actors (id + name + roles)
  for the picker — no emails, no unnecessary PII.

## 7. Case lifecycle

Statuses (controlled): **open → in_review → assigned → escalated →
resolved → closed**; reopening returns a case to `in_review` with
`reopened_count += 1`. Escalation can only be reached through the explicit
escalate action (a bare status flip to `escalated` is refused — 422).
Resolved/closed cases cannot be reworked without reopening.

## 8. Priority model

Explicit operational priority (`low/normal/high/urgent/critical`) — a
separate axis from severity. Severity describes the intrinsic seriousness of
the incident; priority describes how urgently the platform must act (a
fraudulent job can be severity=high, priority=urgent; a minor complaint
severity=low, priority=normal). Priority change requires `reports.escalate`,
is audited (from→to), and restarts the SLA clock deterministically.

## 9. Severity model

Unchanged controlled set (low/medium/high/critical). Escalation may change
severity together with priority; both are audited with from/to metadata.

## 10. SLA model

Deterministic policy in `REPORT_SLA_HOURS[priority] = (response_hours,
resolution_hours)`:

| Priority | Response | Resolution |
|---|---|---|
| low | 72 h | 240 h |
| normal | 24 h | 120 h |
| high | 8 h | 48 h |
| urgent | 4 h | 24 h |
| critical | 1 h | 8 h |

- Deadlines are stored on the row (`sla_response_due_at`,
  `sla_resolution_due_at`) at creation and recomputed deterministically on
  priority change / escalation / reopen (documented restart semantics).
- State is evaluated **lazily** (no scheduler) by `sla_state_for`:
  `on_track` / `due_soon` / `breached`. Breach = an open deadline has
  passed. Due-soon = an open deadline has no more than 20% of **its own**
  window remaining (per-priority thresholds, so a fresh critical case is not
  immediately "due soon").
- Dashboard counts and `sla=` queue filters evaluate exactly in Python over a
  bounded window (newest 10 000 matching open cases) — documented limitation
  (no scheduler, no full-table scans).

## 11. Escalation

`POST /reports/{id}/escalate` requires `reports.escalate` + a reason (≥10
chars). It records `escalated_at/by`, optionally moves the case to a team
(`escalated_to_team_id`), sets status `escalated`, applies priority/severity
changes, and restarts the SLA clock. **The reason never enters audit or event
payloads** (metadata records `reason_present` and target values only — the
reference-only audit convention). The assignee is notified generically. A
bare `status=escalated` PATCH is refused. Future automated escalation
(Athena) will route through this same audited service operation.

## 12. Audit review

`GET /governance/audit` (permission `platform.audit.read`) — filters: action,
action_prefix, actor, organization_id, resource_type, resource_id, result,
request_id, from/to timestamps; paginated (bounded). Every returned payload is
sanitised server-side (`_sanitize_payload`) — keys containing password/token/
secret/body/authorization are stripped and long strings truncated. The screen
answers WHO / DID WHAT / TO WHAT / WHEN / CONTEXT / RESULT without exposing
secrets or message bodies (tested).

## 13. Integrity signals

`GET /governance/signals` computes **neutral, stateless** activity signals
from existing tables (nothing stored, nothing that ages into an accusation):
- `repeated_reports` — ≥5 reports from one reporter in 7 days.
- `repeated_outreach` — ≥25 outreach requests by one organization in 7 days.
- `repeated_blocks_received` — ≥10 candidates blocking one organization in 30
  days.

Labels are neutral (`review_required`, `activity_pattern`, `policy_signal`);
notes always state "not proof of misconduct". No AI scoring, no
fraudulent/deceptive/malicious labels (tested).

## 14. Evidence model

Evidence stays **references only** — `{type, id, note}` on the case. The
governance UI renders case metadata and references, never the target's full
Work ID, documents, contact details, private career goals or message bodies
(tested: `+971…` phone and private headline never appear in queue/detail/
signals payloads).

## 15. Linked reports

`governance_case_links` joins multiple reports into one investigation (unique
per pair, self-links refused). **Cross-tenant linking is refused** (reports
of different organizations cannot be linked). Linking/unlinking is audited;
case detail surfaces links as case references.

## 16. RBAC

Added to the existing registry (no "admin can do everything" shortcut):
- `reports.escalate` — priority/severity change + escalation.
- `reports.teams` — governance team membership management.

Granted to moderator + super_admin only; governance_auditor stays read-only
(can read cases, teams, audit review — cannot escalate/assign/resolve/manage
teams). Regression tests prove employers, recruiters, candidates and
government analysts are **403** on every Phase 10 surface (teams, audit,
signals, moderators, case ops).

## 17. Tenant isolation

Governance is platform-scope by construction; report→report linking is the
only cross-object join introduced and it is tenant-checked. Team memberships
and cases are organisation-neutral platform records; cross-tenant report
access remains 404/403 for non-governance roles (carried from Phase 9 and
re-tested for the new routes).

## 18. Notification integration

`notifications_service.notify(…, kind="governance")` (new controlled kind)
with generic bodies — "A governance case was assigned to you… no case content
is included". Used for assignment and escalation of owned cases. Channel
abstraction from Phase 9 applies (in-app now; email/push later without body
content).

## 19. Event integration

New controlled event types: `governance.case.created/assigned/
priority_changed/escalated/resolved/reopened`. Emitted through
`events_service.emit` with **metadata only** (category/severity/from-to/to
user/resolution-present flags — never descriptions, reasons, bodies or
secrets). Governance events are org-scoped to the actor's platform
organization when one exists, otherwise direct to the actor — the Phase 9
addressing model is reused unchanged.

## 20. Frontend control room

- `/admin/governance` — operational dashboard cards (open, urgent, critical,
  unassigned, mine, SLA breached, due soon, escalated), integrity-signals
  strip, queue views (All / My cases / Unassigned / Escalated / SLA breached /
  Due soon) + status/severity/priority filters + pagination. Case cards show
  case ref, status/severity/priority/SLA pills, team, assignee.
- `/admin/governance/[id]` — SLA banner, assignee/team/priority/status
  selects, escalate form, linked reports panel, internal notes, resolve/
  reopen, audit timeline.
- `/admin/governance/teams` — team cards (open cases, members, add member from
  moderator picker) + team detail (workload counts, member management).
- `/admin/governance/audit` — filtered, paginated audit review with sanitised
  payloads.
- Types extended for all new payloads. Visual language: premium enterprise,
  calm, density without clutter; responsive grid; 403-aware guards.

## 21. Security testing

New suite `test_governance_ops_phase10.py` (11 tests) covers the 22 mandated
targets with hostile calls:
- SLA state function determinism (fresh/breached/due-soon/resolved, window
  accuracy) and priority-restart semantics.
- Escalation is explicit (bare status flip refused), audited, reason-free in
  audit/events, and gated (auditor 403).
- Team membership management (non-governance users refused, auditors cannot
  manage), team-aware assignment (outsider 422, member 200), removal.
- Case links: same-tenant allowed, self/cross-tenant refused, audited,
  surfaced in detail, unlinkable.
- Queue views (mine/unassigned), dashboard operational keys, server-side
  sorting/filter bounds.
- Audit review: employer 403, auditor read, prefix/resource filters,
  sanitisation (no secrets/reason text anywhere).
- Integrity signals: employer 403; ≥5 reports → neutral repeated_reports
  signal; never an accusation.
- Reopen restarts SLA + audited + `governance.case.reopened` event.
- Governance surfaces never echo a candidate's private phone/headline.
- Every Phase 10 surface is 403 for employer/recruiter-candidate/government.

## 22. Test results

- Previous: **132** (Phases 3–9). New: **11**. Total: **143 passed, 0 failed**
  (`pytest tests_phase3/`).
- Canonical routes: **177 `/api/v1`** (+12). Legacy: 107, untouched.
- Frontend: `tsc --noEmit` clean; `next lint` 0 errors (only the 5
  pre-existing Phase-1 careers warnings); production build green including the
  four control-room routes.

## 23. Migration details

`0008_governance_operations.py` — strictly additive. Creates
`governance_teams` (seeded), `governance_team_members`, `governance_case_links`
(58 → 61 tables) and adds operational columns to `governance_reports`
(priority, team_id, escalation markers, first_responded_at, SLA deadline
columns) with indexes; seeds `reports.escalate` + `reports.teams` for
moderator/super_admin. Validated upgrade → downgrade → re-upgrade on scratch
SQLite. **Applied to nothing shared/production.**

## 24. Performance considerations

- Queue/dashboard use indexed, paginated queries; SLA-filtered views evaluate
  exactly over a bounded newest-10 000 window (documented) — no full-table
  scans and no scheduler.
- Audit review is paginated with bounded page size (≤100).
- No analytics warehouse, no naive client-side loading.

## 25. Production readiness

**READY:** canonical API (177 routes), additive migration 0008, ownership
model, deterministic SLA state, audited escalation/teams/links, audit review,
signals, tests (143), proof UI.
**NOT READY / REQUIRES EXTERNAL INFRASTRUCTURE:** SLA scheduling (none —
lazy by design, documented); managed realtime transport (polling is the
transport); Postgres RLS enablement + live-Postgres validation of 0008;
distributed rate-limit store; out-of-band notification providers. **UNKNOWN:**
behaviour at very large moderation volumes (postgres indexes exist but were
not load-tested).

## 26. Known limitations

- SLA "due soon" uses per-priority 20%-of-window thresholds evaluated exactly
  in Python; the `sla=` filters therefore scan a bounded newest-10 000
  candidate set (correct and deterministic, but not index-only).
- No escalation chain/history table — escalations are captured in audit +
  escalated_at/to-team markers (sufficient for this phase; a structured
  escalation history is deferred).
- Teams are seeded; there is no self-service "create team" API (fine for the
  fixed operational set).
- Signals are stateless and computed on read; no historical signal trend.
- The case-assignment picker lists governance actors by name only (no
  workload balancing yet).

## 27. Deferred work

- Managed realtime transport + client subscriptions (contract ready).
- Structured escalation history + SLA scheduler if ever needed.
- Team workload balancing/suggestions; case templates.
- Audit review export; request-id correlation drill-down.
- Postgres RLS enablement per table (artifact from Phase 9 + 0008 tables).
- Out-of-band notification providers.

## 28. Compatibility with Phases 3–9

All Phase 3–9 models, routes and tests pass unchanged (143 total). Matching,
applications, interviews, offers, outreach, communications, documents, Work
ID consent untouched. Governance entry points from Phase 9 keep their exact
signatures and response keys (priority/dashboard/team fields are additive).
Notification `kind` set extended additively; event-type set extended
additively. Careers and legacy trees untouched.

## 29. Athena readiness

Phase 10 makes the platform safe for Athena's eventual tools: every governance
capability is a permissioned service operation with audit + event + generic
notification. Athena could later be granted read tools on the queue/audit
review (respecting `reports.read` / `platform.audit.read`) and — after
explicit human policy — an escalate tool routed through `escalate_case`. The
SLA/escalation machinery is designed to be operated by tools without granting
the tool any bypass of identity, tenant, consent or document rules.

## 30. Decisions requiring approval

1. **Approve Phase 10.**
2. **Migration `0008` on a shared environment** — staging first; rollback =
   `alembic downgrade 0007`.
3. SLA target hours per priority (72/240, 24/120, 8/48, 4/24, 1/8) — confirm
   as the operational commitment, or adjust constants before any live queue.
4. Whether governance team membership should ever gate authorization (Phase
   10 keeps teams purely organisational — by design).
5. Athena governance-tool scope (Phase 12+ decision; recommended: read-only
   queue/audit first).
6. Carried items: Phase 1 hygiene batch (untouched, 63 entries) and external
   credential rotation.

## 31. Exact git/change summary

Phase 10 commits (see delivery message for SHAs), nothing pushed, Phase 1
hygiene batch untouched.

### Files created
- `backend/alembic/versions/0008_governance_operations.py`
- `backend/tests_phase3/test_governance_ops_phase10.py`
- `frontend/src/app/admin/governance/audit/page.tsx`
- `frontend/src/app/admin/governance/teams/page.tsx`

### Files modified
- `backend/app/models/{enums,governance,__init__,catalog}.py`
- `backend/app/services/governance.py`
- `backend/app/schemas/governance.py`
- `backend/app/api/v1/governance.py`
- `backend/tests_phase3/conftest.py` (governance-team seeding)
- `frontend/src/lib/api/types.ts`
- `frontend/src/app/admin/layout.tsx`
- `frontend/src/app/admin/governance/page.tsx`
- `frontend/src/app/admin/governance/[id]/page.tsx`
