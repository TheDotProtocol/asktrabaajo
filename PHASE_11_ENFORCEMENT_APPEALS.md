# PHASE 11 — Moderator Enforcement, Appeals & Staging PostgreSQL Validation

## 1. Objective

Close the operational loop of AskTrabaajo governance:

```
REPORT → CASE → INVESTIGATION → DECISION → ENFORCEMENT
      → AUDIT → APPEAL → FINAL RESOLUTION
```

…while beginning **real PostgreSQL validation** of the canonical architecture
(migrations, constraints, tenant isolation, RLS semantics) on a scratch local
PostgreSQL instance. Nothing was applied to any shared or production database.

## 2. Starting state (verified)

- HEAD `a336c62` (Phase 10 complete); branch `main`.
- 143 canonical tests passing; 177 `/api/v1` routes; legacy backend imports at 107 routes.
- Migrations 0001–0008 validated only on scratch SQLite.
- The carried Phase 1 hygiene batch (63 entries) remained uncommitted and untouched.

## 3. Architecture impact

- **No redesign.** Enforcement and appeals are a new, additive domain **above**
  the Phase 9/10 governance cases and **beside** identity. Identity's
  `user.status` / `organization.status` (active | suspended) is the enforcement
  **effect**; enforcement actions never become a generic "admin can do
  anything" record.
- One governing principle implemented end-to-end: **a governance case is not
  an enforcement action** — a separate, audited decision step must create one.
- Enforcement correctness is **scheduler-free**: ACTIVE/EXPIRED derive from
  `effective_at`/`expires_at`; lazy reconciliation repairs identity state on the
  next gate/auth check.

## 4. Enforcement model

`enforcement_actions` (23 columns): controlled `action_type`, `scope`,
`reason_code`, lifecycle `status`, creator/approver/rejector/revoker actors,
bounded sanitized notes, deterministic `effective_at`/`expires_at` window,
`supersedes_id` for the appeal chain, timestamps. Never stores report bodies,
private communications or Work ID content.

Action types (controlled): `warning`, `content_restriction`,
`communication_restriction`, `account_restriction`, `organization_restriction`,
`suspension`, `reinstatement`.

## 5. Enforcement lifecycle

Stored transitions (each audited):

```
PROPOSED → APPROVED → ACTIVE → (derived) EXPIRED     [window open at approval]
PROPOSED → REJECTED
APPROVED/ACTIVE → REVOKED
APPROVED → (derived) EXPIRED                          [never activated]
```

- ACTIVE/EXPIRED are **derived** from the stored window — `derive_action_state`
  and `is_in_effect` are deterministic with no scheduler.
- Lazy reconciliation (`reconcile_user` / `reconcile_org`) runs on auth paths,
  product gates and `/enforcement/state/me`: a lapsed window releases the
  target and restores `user.status`; a just-opened window suspends and revokes
  sessions immediately.

## 6. Enforcement scopes

Scopes are granular by design: `account`, `communications`, `applications`,
`company_organization`, `governance_participation`, `platform_access`. A
communication restriction blocks messaging but **not** applications; an org
suspension never suspends individual member identities; a user restriction is
never an org restriction. Type↔scope guidance is validated server-side.

Product gates wired (all raise generic 403 `account_restricted`):
- communication gate → outreach creation, conversation messages (both sides)
- application gate → jobseeker apply
- org gate → employer outreach/messaging; org suspension flips `organization.status`

## 7. RBAC

New platform-scope permissions (seeded in catalog + migration 0009):
`enforcement.read/create/approve/revoke/reinstate`, `appeals.read/manage/decide`.

- **enforcement_manager** (new platform role): proposes, approves, revokes,
  and decides appeals.
- **moderator**: read-only `enforcement.read` + `appeals.read` — never powers.
- **governance_auditor**: unchanged (no enforcement surface).
- **super_admin**: all permissions (still platform-scoped, still audited).
- Employers, recruiters, candidates, government analysts: **403 on every
  enforcement/appeal surface** (tested).

## 8. Approval / separation of duties

`account_restriction`, `organization_restriction`, `suspension`,
`reinstatement` **require creator ≠ approver** (403 otherwise — tested).
Warning/content/communication restrictions may be approved by the proposing
manager. Appeal decisions create **rights-restoring** reinstatements that the
deciding manager may execute directly (the decision itself is the approval);
the risky direction (restrict/suspend) always needs a second approver.

## 9. Account / organization state

No identity redesign. Enforcement writes identity effects:
- Suspension activation → `user.status = suspended`, `token_version += 1`,
  all refresh tokens revoked (sessions die immediately).
- Suspension (org scope) activation → `organization.status = suspended`.
- Revocation / reinstatement → status restored, sessions re-issued at login.
- Derived state endpoint `/enforcement/state/me` returns
  `active | restricted | suspended` for the caller only.

**Limited session design:** suspended users may authenticate and reach ONLY the
appeal surface (submit/withdraw/view their own appeal, own state) via a
dedicated `get_suspended_user` dependency. Every other route keeps the default
auth gate and rejects them (tested).

## 10. Appeal model

`appeals`: enforcement action, appellant, controlled `reason_code`, bounded
sanitized `statement`, lifecycle `status`, assigned reviewer, internal
`review_note` (never appellant-visible), decision + sanitized
appellant-visible `decision_note`, timestamps, and `superseding_action_id`
linking a granted appeal's replacement action.

## 11. Appeal lifecycle

```
SUBMITTED → ASSIGNED → UNDER_REVIEW → DECIDED      (accepted | partially_granted | rejected)
SUBMITTED/ASSIGNED/UNDER_REVIEW → WITHDRAWN         (appellant only)
```

- Eligible: the enforcement target, or an org-admin of the target org, within
  a 30-day window; no duplicate open appeal.
- Self-review impossible: the appellant cannot be assigned as reviewer (422),
  cannot decide their own appeal (default auth gate 401 / no `appeals.decide` 403),
  and the assigned reviewer alone may decide (others 403).
- **Decision effects never mutate silently**: accepted / partially-granted
  create a NEW superseding `reinstatement` (status active, `supersedes_id` →
  original), revoke the original with an explicit note, and restore the target.
  Rejected appeals leave enforcement standing. History is preserved end to end.

## 12. Appeal authorization

- Appellant self-view: no `review_note`, own statement only.
- Governance (`appeals.read`): queue + detail with internal note.
- Stranger, employer, government, other candidate: **403 even with a known UUID** (tested).
- A moderator may list appeals but **cannot decide** them (403, tested).

## 13. Audit model

Audited: `enforcement.action.proposed/approved/rejected/revoked`,
`appeal.submitted/assigned/decided/withdrawn`. Audit payloads are
**metadata-only** — no notes, no statements, no bodies, no secrets (enforced by
test asserting every audit row payload contains no `email`, `phone`,
`statement`, `message_body`, `note`, `approval_note`, `decision_note`, or
`review_note` keys). Events carry the same hygiene; in-app notifications are
generic ("A platform action has been applied to your account — sign in for
details"), never content.

## 14. API routes (+15 → 192 `/api/v1`)

`/api/v1/enforcement`:
- `GET /actions` (filters: case, status incl. derived `expired`, type, scope, target) · `POST /actions`
- `GET/POST /actions/{id}/approve|reject|revoke`
- `GET /state/me`
- `POST /appeals` (self) · `GET /appeals/me` (self) · `GET /appeals` (governance queue)
- `GET /appeals/{id}` (appellant view XOR governance view)
- `POST /appeals/{id}/withdraw|assign|review|decide`

## 15. Frontend routes

- `/admin/governance/enforcement` — queue (status filters, case filter)
- `/admin/governance/enforcement/[id]` — action detail: lifecycle actions (approve/reject/revoke), audit timeline
- `/admin/governance/appeals` — appeals queue
- `/admin/governance/appeals/[id]` — appeal review: assignment, review, decision, audit timeline
- Case detail now links into `Enforcement actions for this case` and the Appeals queue.
- Admin nav extended with Enforcement and Appeals.
- TypeScript contract extended (enforcement/appeal types). Typecheck clean,
  ESLint 0 errors (5 pre-existing warnings in untouched Phase-1 files),
  production build green with all four new routes.

## 16. Database migration

`0009_enforcement_appeals` — strictly additive: `enforcement_actions`,
`appeals` (+ indexes), plus the `enforcement_manager` role, 8 permissions and
role mappings. Table count **61 → 63**. Validated on scratch SQLite
(upgrade → downgrade to 0008 → re-upgrade) and on scratch PostgreSQL 16
(upgrade → downgrade → re-upgrade, transactional DDL). Applied nowhere.

## 17. PostgreSQL validation (scratch, local PG 16.14)

Scratch DB `asktrabaajo_p11_scratch` (created, validated, dropped — nothing
else touched):

- Migration 0001→0009 roundtrip on real PostgreSQL: clean.
- Full enforcement + appeal service flow on PG: propose → approve
  (separation enforced: creator-approval denied) → suspension active +
  `user.status=suspended` → appeal submit → assign → begin review → decide
  accepted → superseding reinstatement + original revoked + user restored.
- FK constraints enforced (phantom `created_by` rejected).
- Index inventory for both new tables present (10 indexes).
- UTC/timezone finding: PG `timestamptz` returns tz-aware datetimes; the
  enforcement module now normalizes stored timestamps to naive UTC for
  comparisons (`_coerce`) so lifecycle logic is dialect-safe. Deployment note:
  production sessions should run `SET TIME ZONE 'UTC'` and a future phase
  should move writes to tz-aware UTC — the rest of the codebase still writes
  naive UTC (pre-existing, documented in earlier reports).

## 18. RLS validation

Phase 9's RLS artifact was exercised against **real PostgreSQL** (scratch DB
only) on a genuine org-tenant table (`conversations`): `ALTER TABLE ...
ENABLE ROW LEVEL SECURITY` + the artifact's tenant policy; a non-owner app role
saw `1 / 1 / 2 / 0` rows for tenant-A / tenant-B / both / no session marker —
exactly the intended defense-in-depth semantics. Owner bypass was confirmed
(RLS does not apply to the table owner), validating the documented deployment
requirement that the application connection must be a non-owner role.

**Enforcement/appeals tables are intentionally NOT org-tenant tables**: their
rows are platform-governance records readable only through platform-role
membership. Applying the current org-tenant policy shape would wrongly let
employer tenants read them. Correct RLS for these tables needs a
platform-role session marker (`app.current_is_moderator`) — the same Phase 9
gap, now explicitly documented for enforcement/appeals. Application-level
authorization remains mandatory and is the tested control.

## 19. Rate-limit validation

Phase 9's abstraction unchanged (no Redis provider is configured). The
Phase 11 flow reuses it at the message/outreach/apply boundaries where
enforcement gates also run. Production requirement (documented, not faked):
a distributed store for multi-instance deployments; key strategy and failure
behavior unchanged from Phase 9 §23.

## 20. Security tests

New suite `test_enforcement_phase11.py` (10 tests) proves, on the API with
hostile UUID/route knowledge:

- Moderators cannot propose enforcement (read-only) — 403.
- Approval separation: suspension creator cannot self-approve — 403.
- Suspension lifecycle: approve → `user.status=suspended` → limited session
  reaches only `/state/me` + appeals → default product route 401 → revoke →
  identity restored → product route 200.
- Expiry is deterministic without a scheduler (lapsed window releases on next
  gate; derived `status=expired` listing works).
- Granular scopes: communication restriction blocks messaging gate but not the
  application gate; identity stays active.
- Org suspension: org gate denies while member identity stays active; revoke
  reopens the org.
- Appeals: submit → duplicate refused (409) → self-assignment refused (422) →
  wrong reviewer cannot decide (403) → appellant cannot decide (401/403) →
  accepted decision creates superseding reinstatement + revokes original +
  restores user + audit rows clean.
- Rejected appeal upholds enforcement.
- Visibility/isolation: strangers, employers, government 403 with known UUIDs;
  moderator lists appeals but cannot decide; appellant self-view never shows
  internal notes.
- Withdrawal by appellant only; enforcement stands.
- Audit/event hygiene: no sensitive payload keys across every audit row.

## 21. Full test results

- Before: 143. After: **153 passed, 0 failed** (143 prior + 10 Phase 11).
- Route count: 177 → **192** `/api/v1`.
- Migration roundtrip: SQLite + PostgreSQL, both clean.
- Legacy backend imports at **107 routes**, untouched.
- Careers / Company OS / Jobseeker / Talent / Governance surfaces: all prior
  suites green (no regressions).

## 22. Legacy compatibility

No legacy file was modified. Legacy backend imports at 107 routes. Careers
untouched.

## 23. Known limitations

- Enforcement gates are wired at the highest-risk boundaries (outreach,
  messages, applications, org operations, auth); read-only browsing surfaces
  are not individually gated — the default auth dependency already rejects
  suspended identities there, and restriction-type actions only block the
  scoped activity by design.
- A suspension approved with a future `effective_at` while the target is
  logged in takes effect at the next gate/auth check (scheduler-free by
  design, no push).
- Appeals require an authenticated session; a suspended user obtains a limited
  session at login (deliberate, tested).
- Partially-granted appeals currently produce the same reinstatement as
  accepted (documented in the decision note); expiry shortening is future work.
- No frontend for the appellant-side appeal submission yet (API + governance
  screens complete; candidate UI belongs to a product phase).
- Timezone discipline across the whole codebase (naive-UTC writes) is
  pre-existing; PG sessions must run in UTC until a dedicated pass moves
  writes to tz-aware timestamps.

## 24. Production-readiness status

| Area | Status |
|---|---|
| Canonical API + enforcement/appeals domain | READY (tested, audited, reversible) |
| Migration 0009 (SQLite + PG roundtrips) | READY for change-controlled staging |
| RLS artifact semantics | VALIDATED on scratch PG; ENABLEMENT requires non-owner app role + platform-role session marker |
| Multi-instance rate limiting | REQUIRES EXTERNAL INFRASTRUCTURE (Redis or equivalent) |
| Realtime transport | NOT READY (polling; documented Phase 9/10 deferral) |
| Live/shared Postgres deployment | NOT STARTED (nothing applied; Supabase `.env` untouched) |

## 25. External infrastructure requirements

- Staging PostgreSQL with a non-owner application role (RLS enablement,
  per-table staged order, starting with conversations/messages/applications).
- A distributed rate-limit store before multi-instance deployment.
- Timezone/UTC session configuration on the production connection.

## 26. Decisions requiring approval

1. Approve Phase 11.
2. Authorize applying migrations 0001–0009 to a **staging** PostgreSQL and
   enabling RLS per table in staged order (change-controlled, non-owner role).
3. Whether the appellant-facing appeal submission UI ships in a product phase
   or Phase 12.
4. Carried items remain: the Phase 1 hygiene batch (63 entries, untouched)
   and external credential rotation.

## 27. Git commits (Phase 11 — six logical commits on `main`, nothing pushed)

1. Enforcement + appeals models, RBAC and migration 0009
2. Enforcement service (lifecycle, gates, deterministic state)
3. Appeals service + API routes + auth/deps gate wiring
4. Phase 11 security tests
5. Phase 11 frontend control-room screens
6. Phase 11 report (+ PostgreSQL/RLS validation notes)

## 28. Files created

- `backend/alembic/versions/0009_enforcement_appeals.py`
- `backend/app/models/enforcement.py`
- `backend/app/services/enforcement.py`
- `backend/app/schemas/enforcement.py`
- `backend/app/api/v1/enforcement.py`
- `backend/tests_phase3/test_enforcement_phase11.py`
- `frontend/src/app/admin/governance/enforcement/page.tsx`
- `frontend/src/app/admin/governance/enforcement/[id]/page.tsx`
- `frontend/src/app/admin/governance/appeals/page.tsx`
- `frontend/src/app/admin/governance/appeals/[id]/page.tsx`
- `PHASE_11_ENFORCEMENT_APPEALS.md`

## 29. Files modified

- `backend/app/models/enums.py` (enforcement/appeal constants, permission codes, event types)
- `backend/app/models/__init__.py`, `backend/app/models/catalog.py` (role + permissions)
- `backend/app/services/auth_service.py` (suspended limited-session login policy)
- `backend/app/api/deps.py` (`get_suspended_user`, lazy reconciliation)
- `backend/app/api/v1/router.py`, `backend/app/api/v1/talent.py` (gates),
  `backend/app/api/v1/jobseeker.py` (gates)
- `frontend/src/lib/api/types.ts`, `frontend/src/app/admin/layout.tsx`,
  `frontend/src/app/admin/governance/[id]/page.tsx` (case → enforcement links)

## 30. Confirmation

**Phase 12 was NOT started.** No Athena, no AI interview engine, no career
advisor, no government portal, no payments, no blockchain. No production or
shared database was touched. The carried Phase 1 hygiene batch remains
uncommitted and untouched. Recommend Phase 12 based on what now exists:
apply migrations to a staging PostgreSQL with a non-owner role and enable RLS
per table in staged order, then build the moderator enforcement *operations*
surface (action templates, case→action workflow, escalation views) — realtime
transport and Athena tool wiring remain behind the governance layer.
