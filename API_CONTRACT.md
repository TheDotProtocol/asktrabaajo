# API CONTRACT — Canonical Backend `/api/v1`

Generated from the actual implementation by importing `backend/app/main.py` (FastAPI). **246 routes.** Every route:

- requires a bearer token (`Authorization: Bearer <access_token>`) unless noted,
- resolves the actor's `User` (+ `PersonProfile` where applicable),
- enforces RBAC (`require_org_permission` / `require_super_admin` / self-scope),
- scopes queries to the actor's org/person (tenant isolation),
- returns errors as `{"error":{"code","message","details"}}`,
- audits meaningful actions.

**Global envelope:** success bodies are plain JSON; list endpoints return `{"items": [...]}` unless noted. Numeric money is Decimal. Times are ISO-8601 UTC.

**No citizen-lookup, facial-analysis, lie-detection, or autonomous-decision routes exist anywhere in this contract.**

---

## Auth — 16 routes

| Method | Path | Auth | Purpose / notes |
|---|---|---|---|
| POST | `/api/v1/auth/register` | public | Create user + person; returns `TokenPair` |
| POST | `/api/v1/auth/login` | public | Password login; optional MFA flow |
| POST | `/api/v1/auth/refresh` | refresh token | Rotate refresh token → new `TokenPair` |
| POST | `/api/v1/auth/logout` | token | Revoke current refresh token |
| POST | `/api/v1/auth/change-password` | token | Change own password |
| POST | `/api/v1/auth/forgot-password` | public | Request reset (email) |
| POST | `/api/v1/auth/reset-password` | reset token | Set new password |
| POST | `/api/v1/auth/verify-email` | token | Verify email with code |
| POST | `/api/v1/auth/verify-email/send` | token | Resend verification |
| POST | `/api/v1/auth/mfa/enable` | token | Enable MFA |
| POST | `/api/v1/auth/mfa/confirm` | token | Confirm MFA enrollment |
| POST | `/api/v1/auth/mfa/verify` | token | Verify MFA challenge |
| POST | `/api/v1/auth/mfa/disable` | token | Disable MFA |
| GET | `/api/v1/auth/me` | token | Current user + roles + person |
| GET | `/api/v1/auth/sessions` | token | List own sessions |
| POST | `/api/v1/auth/sessions/revoke-all` | token | Revoke all own sessions |

## Work ID — 26 routes (self-scoped; owner only)

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/work-id` | Work ID profile overview |
| GET | `/api/v1/work-id/completion` | Profile completion score |
| GET/PUT | `/api/v1/work-id/profile` | Professional profile |
| GET/PUT | `/api/v1/work-id/skills`; DELETE `/api/v1/work-id/skills/{skill_id}` | Skills |
| GET/POST/DELETE/PATCH | `/api/v1/work-id/experiences/{id?}` | Experience records |
| GET/POST/DELETE | `/api/v1/work-id/employments/{id?}` | Employment records |
| GET/POST/DELETE/PATCH | `/api/v1/work-id/educations/{id?}` | Education records |
| GET/POST/DELETE/PATCH | `/api/v1/work-id/credentials/{id?}` | Credentials (verification states enforced) |
| GET/POST/DELETE | `/api/v1/work-id/consents/{id?}` | Candidate-controlled consents |
| GET/PUT | `/api/v1/work-id/privacy` | Visibility settings |

## Documents — 7 routes (owner + explicit grants)

| Method | Path | Purpose |
|---|---|---|
| GET/POST | `/api/v1/documents` | List/upload own documents |
| GET/DELETE | `/api/v1/documents/{document_id}` | View/delete (owner) |
| GET/POST | `/api/v1/documents/{document_id}/grants` | Grant controlled disclosure |
| DELETE | `/api/v1/documents/{document_id}/grants/{grant_id}` | Revoke grant |

Documents are never returned wholesale; disclosure requires an authorized grant.

## Jobseeker OS — 46 routes (self-scoped)

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/jobseeker/dashboard` | Jobseeker dashboard |
| GET | `/api/v1/jobseeker/opportunities`; `/{opportunity_id}` | Discover/view opportunities (matching) |
| POST | `/api/v1/jobseeker/opportunities/{id}/save` | Save opportunity |
| POST | `/api/v1/jobseeker/opportunities/{id}/dismiss` | Dismiss |
| GET/POST | `/api/v1/jobseeker/applications`; `/{application_id}` | Applications; POST requires consent-scope checks |
| POST | `/api/v1/jobseeker/applications/batch` | **Bulk apply — high-risk**: exact-ID confirmation required |
| POST | `/api/v1/jobseeker/applications/{id}/withdraw` | Withdraw |
| GET | `/api/v1/jobseeker/advisor` | Career Advisor chat (Athena) |
| GET | `/api/v1/jobseeker/career/intelligence` | Career intelligence |
| GET/POST | `/api/v1/jobseeker/goals`; PATCH/DELETE `/{goal_id}` | Career goals |
| GET/POST | `/api/v1/jobseeker/milestones`; DELETE `/{milestone_id}` | Milestones |
| GET | `/api/v1/jobseeker/interviews` | Interviews list |
| POST | `/api/v1/jobseeker/interviews/{id}/reschedule-request` | Reschedule (limit enforced) |
| GET/POST | `/api/v1/jobseeker/offers`; POST `/{offer_id}/decision` | Offers + candidate decision |
| GET | `/api/v1/jobseeker/work-dna`; GET `/questions`; POST `/assessments` | Adaptive assessment |
| GET | `/api/v1/jobseeker/notifications`; `/{id}/read`; `/read-all`; `/unread-count` | Notifications |
| GET | `/api/v1/jobseeker/communications`; `/{conversation_id}`; POST `/messages`; `/read`; `/close`; `/unread`; `/blocks`; POST/DELETE `/organizations/{org_id}/block` | Outreach conversations, messaging, blocking |
| GET | `/api/v1/jobseeker/outreach/{request_id}`; POST `/accept` `/decline` `/report` | Outreach responses |
| GET | `/api/v1/jobseeker/document-requests`; POST `/{request_id}/approve` `/decline` | Employer document requests (candidate controls) |

## Career Advisor — 6 routes (self-scoped)

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/career-advisor/digest` | Career Profile Digest (deterministic) |
| GET | `/api/v1/career-advisor/gaps` | Skill/experience gaps vs target |
| GET | `/api/v1/career-advisor/paths` | Career paths (DIRECT/ADJACENT/TRANSITION/EXPLORATORY) |
| GET | `/api/v1/career-advisor/opportunities` | Explained opportunity recommendations |
| GET | `/api/v1/career-advisor/applications` | Application-history analysis |
| GET | `/api/v1/career-advisor/action-plan` | Suggested actions (no guarantees) |

## Interview Prep — 7 routes (self-scoped; raw answers not persisted)

| Method | Path | Purpose |
|---|---|---|
| GET/POST | `/api/v1/interview-prep/sessions`; `/{session_id}`; DELETE | Mock interview sessions |
| POST | `/api/v1/interview-prep/sessions/{id}/questions` | Generate structured questions |
| POST | `/api/v1/interview-prep/sessions/{id}/answers` | Evaluate an answer (explainable dimensions) |
| POST | `/api/v1/interview-prep/sessions/{id}/complete` | Complete session |

## AI Interviews — 19 routes

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET/POST | `/api/v1/ai-interviews` | token, `interviews.manage` (org, via `organization_id` query) | List/configure interviews |
| POST | `/api/v1/ai-interviews/{id}/invite` | token, `interviews.manage` | Invite candidate |
| POST | `/api/v1/ai-interviews/{id}/cancel` | token, `interviews.manage` | Cancel |
| GET | `/api/v1/ai-interviews/{id}/report` | token, `interviews.manage` | Employer report (human-review required) |
| POST | `/api/v1/ai-interviews/{id}/decision` | token, `interviews.manage` | **Human decision** (advance/reject/hold/followup/human-interview) |
| POST | `/api/v1/ai-interviews/claim` | token (candidate) | Enter via one-time entry token (hashed at rest) |
| POST | `/api/v1/ai-interviews/{id}/consent`; `/consent/withdraw` | token + `X-Interview-Token` | Consent per mic/camera/recording; withdrawal stops |
| POST | `/api/v1/ai-interviews/{id}/start` | token + token | Start (requires consent) |
| GET | `/api/v1/ai-interviews/{id}/next-question` | token + token | Next validated question |
| POST | `/api/v1/ai-interviews/{id}/responses` | token + token | Submit response (never persisted raw) |
| POST | `/api/v1/ai-interviews/{id}/repeat` | token + token | Repeat/rephrase (never penalized) |
| POST | `/api/v1/ai-interviews/{id}/pause`; `/resume` | token + token | Pause/resume |
| POST | `/api/v1/ai-interviews/{id}/complete` | token + token | Complete |
| GET | `/api/v1/ai-interviews/{id}/feedback` | token + token | Candidate feedback |
| POST | `/api/v1/ai-interviews/{id}/integrity-signals` | token + token | Session-level signals (labeled review signals only) |

Wrong token/wrong person/replay → 403; no existence oracle.

## Athena — 8 routes

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/v1/athena/session` | Open Athena session |
| POST | `/api/v1/athena/message` | Send message (tool loop, budgets, rate limits) |
| POST | `/api/v1/athena/confirm` | Confirm high-risk action (exact scope, expiry) |
| GET | `/api/v1/athena/confirmations` | Pending confirmations |
| POST | `/api/v1/athena/session/{id}/close` | Close session |
| GET | `/api/v1/athena/tools` | Tool registry (39 tools) |
| GET | `/api/v1/athena/usage` | Own AI usage |
| GET | `/api/v1/athena/modes` | Supported modes |

## Organizations — 7 routes

| Method | Path | Purpose |
|---|---|---|
| GET/POST | `/api/v1/organizations` | List/create own orgs (platform/government kinds need super admin) |
| GET | `/api/v1/organizations/{organization_id}` | Org detail (membership) |
| GET/POST | `/api/v1/organizations/{id}/members`; PATCH/DELETE `/{member_user_id}` | Members (owner/admin) |

## Company / Employer OS — 25 routes (org-scoped via `{organization_id}`)

| Method | Path | Permissions |
|---|---|---|
| GET/PATCH | `/api/v1/company/{org}/profile` | `orgs.read`/`company.manage` |
| GET/POST | `/api/v1/company/{org}/jobs`; GET/PATCH `/{job_id}`; POST `/publish` `/pause` `/close` | `jobs.*` |
| GET | `/api/v1/company/{org}/applications`; `/{application_id}` | `applications.view` |
| POST | `/api/v1/company/{org}/applications/{id}/decision` | `applications.manage` |
| GET/POST | `/api/v1/company/{org}/interviews`; POST `/{interview_id}/confirm-reschedule` `/complete`; GET `/scorecards` | `interviews.*` |
| GET/POST | `/api/v1/company/{org}/offers`; POST `/{offer_id}/send` `/withdraw` | `offers.*` |
| GET/POST | `/api/v1/company/{org}/document-requests` | `documents.*`/org scope |
| GET | `/api/v1/company/{org}/dashboard` | org member |
| GET | `/api/v1/company/{org}/analytics` | `analytics.view` |

## Talent Graph — 27 routes (org-scoped)

| Method | Path | Permissions |
|---|---|---|
| GET | `/api/v1/talent/{org}/skills`; `/{skill_id}`; `/categories`; POST `/normalize` | `candidates.search` |
| GET/POST | `/api/v1/talent/{org}/pools`; `/{pool_id}`; POST/DELETE `/members/{person_id}` | `pools.manage` |
| GET | `/api/v1/talent/{org}/candidates/search`; `/{person_id}`; POST/DELETE `/{person_id}/saved`; GET `/saved` | `candidates.search` (opt-in/public visibility only) |
| GET | `/api/v1/talent/{org}/opportunities/{opp_id}/candidates`; `/requirements` | `candidates.view` |
| GET/POST | `/api/v1/talent/{org}/outreach`; `/{request_id}`; POST `/{request_id}/cancel` | `talent.outreach.*` (cooldown/expiry enforced) |
| GET/POST | `/api/v1/talent/{org}/communications`; `/{conversation_id}`; POST `/messages` `/read` `/close` | `communications.*` |

## Governance — 21 routes (platform moderator/admin)

| Method | Path | Purpose |
|---|---|---|
| GET/POST | `/api/v1/governance/reports`; `/{report_id}` | Cases |
| POST | `/api/v1/governance/reports/{id}/assign` `/priority` `/escalate` `/team` `/notes` `/links`; DELETE `/links/{link_id}`; PATCH `/status`; POST `/resolve` `/reopen` | Case workflow |
| GET/POST | `/api/v1/governance/teams`; `/{team_id}`; POST/DELETE `/members/{user_id}` | Moderation teams |
| GET | `/api/v1/governance/moderators`; `/dashboard`; `/signals`; `/audit` | Oversight |

## Enforcement — 15 routes (creator/approver separation)

| Method | Path | Purpose |
|---|---|---|
| GET/POST | `/api/v1/enforcement/actions`; `/{action_id}` | Actions (create ≠ approve) |
| POST | `/api/v1/enforcement/actions/{id}/approve` `/reject` `/revoke` | Approval workflow (separate actor) |
| GET/POST | `/api/v1/enforcement/appeals`; `/{appeal_id}`; POST `/assign` `/review` `/decide` `/withdraw`; GET `/me` | Appeals + reinstatement |
| GET | `/api/v1/enforcement/state/me` | Own enforcement state |

## Billing — 9 routes

| Method | Path | Auth / notes |
|---|---|---|
| GET | `/api/v1/billing/plans` | token (catalog; FREE plan seeded, no invented pricing) |
| GET | `/api/v1/billing/subscription` | token, `billing.read` (org) |
| POST | `/api/v1/billing/subscriptions` | token, `billing.manage` |
| POST | `/api/v1/billing/subscriptions/cancel` | token, `billing.manage` |
| GET | `/api/v1/billing/entitlements` | token, `billing.read` |
| GET | `/api/v1/billing/invoices`; `/{invoice_id}` | token, `billing.read` |
| GET | `/api/v1/billing/usage` | token, `billing.read` |
| POST | `/api/v1/billing/webhooks/{provider}` | **HMAC-signed webhook** (no bearer token; signature verified; replay/duplicate protected) |

## Finance — 5 routes (platform only)

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/finance/transactions` | `finance.read` |
| GET | `/api/v1/finance/invoices` | `finance.read` |
| GET/POST | `/api/v1/finance/refunds` | `finance.manage` (idempotent, bounded by paid balance) |
| GET | `/api/v1/finance/subscriptions` | `finance.read` |

Org users, recruiters, and support **cannot** reach finance routes (403 — tested).

## Events — 2 routes

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/events` | Notification feed |
| POST | `/api/v1/events/read` | Mark read |

---

## Cross-cutting notes for the UI

- **Organization context:** org-scoped routes take `organization_id` as a query param; the UI must pass the org the user selected (membership checked server-side).
- **Candidate-side interview calls** need `X-Interview-Token` header (the one-time entry token).
- **Confirmations:** `POST /athena/confirm` returns the outcome of an exact-scope, expiring confirmation. UI must render the scope and expiry; never auto-confirm.
- **Bulk actions:** `POST /jobseeker/applications/batch` requires a confirmation bound to the exact opportunity IDs.
- **Errors:** `{"error":{"code","message","details"}}`; 401 (token), 403 (permission/ownership), 404 (not found — no existence oracle on sensitive objects), 422 (validation), 429 (rate limit).
- **Webhooks** are server-to-server; never call them from the browser.