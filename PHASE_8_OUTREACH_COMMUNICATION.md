# PHASE 8 — Controlled Talent Outreach & Communication

Status: **COMPLETE** — implemented, tested, documented. No Phase 9 work started.

The full sequence now works end-to-end:

```
COMPANY → Discovers candidate → Explainable Talent Graph match
       → Request contact          CANDIDATE → Reviews company + opportunity + reason
       → Accepts                   ASKTRABAAJO → Creates a controlled conversation
       → Recruiter sends message   CANDIDATE → Replies → Application → Interview → Offer
```

Throughout the process **AskTrabaajo controls the relationship**. No private
contact information leaks; no tenant crosses into another tenant; every
sensitive action is audited.

---

## 1. Phase objective

Take AskTrabaajo from *"a company can discover relevant talent"* to *"a
company can safely request contact, the candidate controls whether contact
happens, and AskTrabaajo is the controlled communication layer between
them."*

Built foundations, not chat: **DISCOVER → REQUEST → CONSENT → CONNECT →
COMMUNICATE → APPLY**, with the Talent Graph / Opportunity / Company OS /
Work ID / Application architecture staying the single source of truth.

## 2. Existing system inspected (recon summary)

- **Existing communication-related infrastructure:** none — Phase 1–7 had no
  recruiter↔candidate channel. Document access was the closest concept
  (request → candidate approval → audited org grant).
- **Notifications:** `services/notifications.py` (user-owned feed, minimal,
  anti-spam by construction; kinds already modeled). Reused, extended with
  `outreach` and `communication` kinds.
- **Existing candidate/company relationships:** applications (shared state
  machine), interviews, offers, document requests, talent pools, saved
  candidates — all organization- or person-scoped.
- **Existing application states:** one canonical machine
  (`services/applications.py`) + Phase 6 employer transitions. Untouched.
- **Existing audit events:** append-only `AuditLogEntry` writer. Extended
  with Phase 8 actions.
- **Existing RBAC permissions:** role/permission catalog seeded in
  `models/catalog.py` and Alembic. Extended with six Phase 8 permissions.
- **Existing disclosure mechanisms:** Work ID privacy scopes + Phase 4
  consents + progressive disclosure in `services/talent.py`. Outreach reuses
  the same visibility rule (`person_visible_to_org`).
- **Existing frontend components:** `/company/candidates/[id]` profile +
  match panel, `/company` layout, `/jobseeker` layout, typed API client
  (`lib/api/session.ts` + `types.ts`). Extended with new centers.

## 3. Architecture decisions

1. **No participant tables.** A conversation's access is structural: the
   candidate person owns one side; any member of the owning organization
   with `communications.read` owns the other. Company A can never reach
   Company B rows because every query is tenant-scoped and permission-gated.
2. **One controlled conversation model**, reusable for outreach, application,
   interview and offer threads (later phases attach by `application_id` /
   `opportunity_id`).
3. **No attachments in messages.** Document sharing keeps the Phase 4
   request/consent layer; messages carry no private contact data at all.
4. **Realtime deferred** (see §22). Polling is the Phase 8 mechanism.
5. **Plain-UUID back-reference** from `outreach_requests.conversation_id`
   (no circular FK) — SQLite-safe, matching the `offer_document_id`
   precedent.
6. **Read state = per-user cursor** (`conversation_read_states`), so each org
   member's unread count is independent.

## 4. Outreach model

`OutreachRequest` (`models/communication.py`): organization, requesting
member, candidate person, optional opportunity + application, introduction
message, optional context, controlled status, expiry, viewed/responded
timestamps, optional note, conversation link.

States: **sent → viewed → accepted / declined / expired / cancelled /
blocked**. Only `sent`/`viewed` are actionable by the candidate or
cancellable by the org. Sending **never reveals** phone/email/address.

## 5. Communication model

`Conversation`, `ConversationMessage`, `ConversationReadState`:

- A conversation exists **only** because of a legitimate relationship:
  (a) the candidate **accepted** an outreach request, or (b) an organization
  member opened a thread on a live **application**.
- Messages carry `sender_side` (candidate | recruiter), body, timestamps.
  Sender names are resolved at read time from the canonical user/person
  records (never candidate emails/phones).
- Conversations are `active` → `closed`; closed conversations reject sends.

## 6. Candidate consent

Explicit and reversible:

- Accepting outreach is the candidate's own POST — nothing auto-accepts.
- A decline is a **generic** outcome for the company (no private data, no
  note content in the org payload).
- Report = decline **+ standing block** of the organization.
- Candidate can block/unblock an organization at any time
  (`/jobseeker/communications/organizations/{id}/block`).
- Even after acceptance, contact stays in-platform; the Phase 4
  consent/disclosure layer remains the only way to see private sections or
  documents.

## 7. Privacy model

- `discoverable ≠ contactable automatically`, `outreach ≠ contact
  exposure`, `accepted outreach ≠ private-data disclosure`.
- Candidate payloads show *who, why, which opportunity* — never their own
  private details echoed, never another person's data.
- Company payloads show the professional summary the org was already
  entitled to see under Phase 7 progressive disclosure.
- Tests assert phone numbers and emails never appear in any outreach or
  conversation payload or message thread.

## 8. RBAC

Six new catalog permissions (org-scoped):

| Permission | org_admin | hr | recruiter | hiring_manager |
|---|---|---|---|---|
| talent.outreach.create | ✓ | ✓ | ✓ | ✗ |
| talent.outreach.read | ✓ | ✓ | ✓ | ✗ |
| talent.outreach.manage | ✓ | ✓ | ✗ | ✗ |
| communications.read | ✓ | ✓ | ✓ | ✓ |
| communications.send | ✓ | ✓ | ✓ | ✗ |
| communications.manage | ✓ | ✓ | ✗ | ✗ |

`super_admin` receives everything (full-catalog role). A recruiter who is
not the requester cannot cancel another member's request (needs manage).
Company roles can never elevate to platform scope.

## 9. Tenant isolation

Enforced at the API (membership + org-scoped permission) **and** at the
service layer (every row lookup is scoped to the caller's organization).
Tests prove Company B receives **403 on every Company A outreach/
conversation/message route, even knowing the exact conversation UUID**, and
an unrelated candidate receives **404** for another person's conversation or
outreach.

## 10. Database changes

One additive migration **`0006_outreach_communication.py`** (48 → 53
tables):

- `outreach_requests` — org + person scoped, unique live-request guard,
  unique conversation back-reference, indexes on org/person/opportunity.
- `outreach_blocks` — candidate standing blocks (unique person+org).
- `conversations` — org + person + optional opportunity/application/
  outreach + opener + status + last-message time.
- `conversation_messages` — conversation + sender + side + body.
- `conversation_read_states` — per-user read cursors.

No names collide with the live Supabase careers schema.

## 11. API routes (23 new; canonical surface 138 → 154)

**Organization side (`/api/v1/talent/{org}/...`)**
- `POST /outreach` · `GET /outreach` · `GET /outreach/{id}` ·
  `POST /outreach/{id}/cancel`
- `GET /communications` · `POST /communications` (open from an application,
  idempotent) · `GET /communications/{id}` ·
  `POST /communications/{id}/messages` · `POST /communications/{id}/read` ·
  `POST /communications/{id}/close`

**Candidate side (`/api/v1/jobseeker/...`)**
- `GET /communications` (inbox: outreach + conversations + unread) ·
  `GET /communications/unread` · `GET /communications/blocks` ·
  `POST/DELETE /communications/organizations/{id}/block`
- `GET /communications/{id}` · `POST /communications/{id}/messages` ·
  `POST /communications/{id}/read` · `POST /communications/{id}/close`
- `GET /outreach/{id}` (marks viewed) · `POST /outreach/{id}/accept` ·
  `POST /outreach/{id}/decline` · `POST /outreach/{id}/report`

All endpoints require authentication; org routes additionally require the
membership + exact permission for the operation.

## 12. Frontend changes

- **`/company/communications`** — Employment Communication OS: outreach
  requests (status chips, cancel), conversations with per-conversation
  unread, a two-pane thread view (reply, mark read, close), and
  *“Open from an application…”* for application-attached threads.
- **`/jobseeker/communications`** — candidate center: “New opportunities”
  cards with Accept / Decline / **Block & report**, plus active
  conversations with unread badges and an in-platform reply composer.
- **`/company/candidates/[id]`** — new *Request contact* panel: choose a
  published job, write the introduction + context, send; shows the status
  chips of existing requests for that candidate.
- Nav entries added to both shells; ~200 lines of Phase 8 types in
  `lib/api/types.ts`. One pre-existing lint error in the Phase 5
  applications page (an `<a>` to an existing route) was fixed so the lint
  gate is green.

## 13. Notification integration

Via the existing feed, anti-spam by construction (no message bodies ever):
- Candidate: `outreach` kind on new request; `communication` kind on
  company messages and application-thread opens.
- Recruiter/opener: `communication` kind on acceptance, decline (generic),
  and candidate replies.
- Report/cancel create audit records, not spam notifications.

## 14. Application integration

- Outreach referencing an org-owned opportunity attaches the candidate's
  live application (`application_id`) when one exists.
- Accepting such an outreach opens the conversation linked to that
  application + opportunity (verified in tests: `conversation.application_id
  == app id`, and the application row/status is untouched — one lifecycle).
- Recruiters can also open an application thread directly (idempotent per
  application), giving interview/offer communication a future anchor.

## 15. Audit events

Append-only `audit_log` entries: `talent.outreach.created / viewed /
accepted / declined / cancelled / reported`,
`communications.conversation.opened / viewed / closed`,
`communications.message.sent`, `communications.org.blocked / unblocked`.
Records carry actor, organization, target resource and metadata; **message
bodies and candidate personal data are never written to the log**.

## 16. Abuse controls

- One live request per (organization, person) → duplicate pending refused.
- Cooldown: a new request to the same candidate is refused if any previous
  request (any outcome) was created within `outreach_cooldown_days` (7,
  configurable) — cannot re-contact moments after a decline.
- Expiry: actionable requests expire after `outreach_expiry_days` (30,
  configurable) and can no longer be accepted.
- Standing candidate blocks: blocked orgs are refused (403) until the
  candidate removes the block.
- Report = block + audited.

## 17. Security review

- Authorization: membership + org-scoped permission on every org route;
  person ownership (404-hides-existence) on every candidate route.
- Tenant isolation: tested cross-tenant (403) and cross-person (404).
- ID enumeration: knowing a conversation UUID without authorization gains
  nothing (403/404).
- Consent: acceptance is the only path to a conversation; documents still
  require Phase 4 requests/grants.
- Rate limiting: cooldown + duplicate + block controls server-side (API
  middleware-level rate limiting remains a Phase 9 item).
- Attachments: none exist in this layer.
- Sensitive-data exposure: no phones/emails in any payload; notifications
  carry no message bodies; audit carries no bodies.

## 18. Tests (11 new — Phase 8)

Full happy path (send → notify → view → accept → conversation → messages →
read-state → close), non-visible candidate 404, pipeline candidate with
application linkage, generic decline, duplicate + cooldown, report/block +
unblock, expiry, cross-tenant isolation, RBAC (hiring manager read-only;
non-requester recruiter cannot cancel), idempotent application thread +
tenant-safe open, per-user read state.

## 19. Validation

- Backend canonical suite: **119 passing** (108 Phase 3–7 + 11 Phase 8), 0
  failures.
- Legacy backend: imports cleanly, unchanged at **107 routes**.
- Careers platform: untouched; all `/careers` routes still compile in the
  production build.
- Frontend: TypeScript typecheck clean, ESLint **0 errors** (5 legacy
  warnings in untouched careers components), production build passes with
  both new `/company/communications` and `/jobseeker/communications` routes.
- Migration: upgrade (48 → 53 tables) → downgrade (→ 48) → re-upgrade
  verified on a scratch SQLite database.

## 20. Migration validation

`0006` validated roundtrip locally. **No migration was applied to any
shared/production database.** The migration is strictly additive; rollback
drops only the five tables it created plus its RBAC seeds.

## 21. Known limitations

- Realtime/push: polling only (see §22).
- No attachments/multimedia in messages (deliberate).
- Org inbox has no per-job filter UI yet (API supports status filter).
- No admin-level moderation console for reported outreach (audit + block
  exist; triage UI is a later-phase platform-admin concern).
- Expiry is enforced lazily on read paths (sweep on list/detail), not by a
  scheduler.
- Outreach "draft" state exists conceptually but the UI sends immediately —
  compose + send is one action, as designed for this phase.

## 22. Deferred work

- WebSocket/realtime hardening (polling is the Phase 8 mechanism).
- Admin moderation UI for outreach reports.
- Email out-of-band notifications (feed-only today).
- Attachments (tie into the Phase 4 document layer).
- Athena tool operations over these services (interfaces already clean:
  `create_outreach`, `accept_outreach`, `send_message`, … are
  permission-enforcing service functions).
- API-wide rate limiting middleware.

## 23. Production readiness

- READY: canonical API surface, additive migration, ownership/isolation
  model, tests, frontend proof pages, legacy compatibility.
- NOT READY: deployment to a shared Postgres (needs the migration applied
  under change control + RLS review), realtime, email channels.
- UNKNOWN: production-scale behavior of the org inbox under heavy load,
  real email deliverability.

## 24. Risks

- Lazy expiry depends on traffic touching the affected rows; an abandoned
  request could linger until then (low severity).
- Org-side "any member with communications.read can see all threads" is the
  intended HR-team model but should be revisited if per-recruiter privacy is
  ever required.
- A candidate who blocks an org then creates an application may still be
  contacted via the application thread (recruiter-opened); blocks apply to
  **outreach**, which is the correct boundary today.

## 25. Decisions required

1. Approve Phase 8 and the §30 recommendation before Phase 9.
2. Apply migration `0006` to a shared environment (staging first).
3. Whether outreach reports should also reach a platform-admin queue in
   Phase 9.
4. Carried items: the Phase 1 hygiene batch (deliberately untouched) and
   external credential rotation.

## 26. Files created

- `backend/app/models/communication.py`
- `backend/alembic/versions/0006_outreach_communication.py`
- `backend/app/services/outreach.py`
- `backend/app/services/communications.py`
- `backend/app/schemas/communication.py`
- `backend/tests_phase3/test_communication_phase8.py`
- `frontend/src/app/company/communications/page.tsx`
- `frontend/src/app/jobseeker/communications/page.tsx`
- `PHASE_8_OUTREACH_COMMUNICATION.md`

## 27. Files modified

- `backend/app/models/enums.py` (outreach/conversation/message enums +
  notification kinds + permission codes)
- `backend/app/models/catalog.py` (6 permissions + role mappings)
- `backend/app/models/__init__.py` (register communication models)
- `backend/app/core/config.py` (outreach expiry/cooldown policy)
- `backend/app/api/v1/talent.py` (org-side outreach/communications routes)
- `backend/app/api/v1/jobseeker.py` (candidate-side routes)
- `frontend/src/lib/api/types.ts` (Phase 8 contract types)
- `frontend/src/app/company/layout.tsx` · `jobseeker/layout.tsx` (nav)
- `frontend/src/app/company/candidates/[id]/page.tsx` (Request contact panel)
- `frontend/src/app/jobseeker/applications/page.tsx` (lint fix: `<a>` → `Link`)

No changes to the legacy `api/`/`backend/api/` trees or the Careers
implementation.

## 28. Git commits

Six logical commits on `main` (see final report for hashes); nothing pushed;
history untouched; `backup/pre-phase-1` intact; the unrelated Phase 1
hygiene batch remains uncommitted and untouched.

## 29. Rollback strategy

- Code: revert the six commits (each file group is self-contained).
- Schema: `alembic downgrade 0006` drops exactly the new tables and RBAC
  seeds; no pre-existing table or row is modified by the upgrade.
- Data: conversations/messages/outreach are Phase 8-only; nothing in the
  canonical Phase 1–7 tables is altered.

## 30. Phase 9 recommendation

Recommended Phase 9 scope, in order:
1. **Realtime hardening** (WebSockets/push over the polling surface) +
   API rate-limiting middleware.
2. **Platform governance layer**: admin queue for outreach reports/audit
   triage.
3. **Out-of-band notifications** (email) behind the existing feed
   architecture.
4. Postgres RLS/config hardening for the canonical backend before any shared
   deployment.

Then revisit Athena tool wiring once the platform governance layer exists.
