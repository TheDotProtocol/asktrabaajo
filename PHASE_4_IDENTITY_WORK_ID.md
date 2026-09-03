# AskTrabaajo — Phase 4 Report: Identity, Work ID & User Core

**Date:** 2026-09-03 · **Phase 4 of the v2.0 rebuild** · Scope: make the central human identity real on the Phase 3 foundation.

**Status:** complete per the Phase 4 definition of done. Careers platform + legacy backend untouched. No production database touched, no destructive migrations, no secrets introduced.

**Companion documents:** `AUDIT_REPORT.md` · `PHASE_1_REPORT.md` · `PHASE_2_ARCHITECTURE.md` · `PHASE_3_FOUNDATION.md`.

---

## 1. What was implemented

Identity spine on the canonical backend:

- **Auth hardened**: password change, forgot + reset password, single-use time-limited hashed tokens, session listing + revoke-all, email verification, MFA (TOTP) foundation, per-IP rate limiting on login/MFA/reset.
- **USER ≠ PERSON enforced**: `users` (account/sessions/security) and `person_profiles` (the human) remain separate; all Work ID data hangs off the person, never the account.
- **Work ID made first-class**: profile contact/identity fields, education levels, structured skills, employment history w/ explicit `unverified` verification state, credentials with restricted verification transitions, profile completion with configurable weighted criteria.
- **Consent + privacy foundations**: reusable person-owned consent records (who/to-whom/what/purpose/when/until/revoked) and per-section visibility (private/public/authorized_only, default private).
- **Email verification architecture**: token state machine (unverified → pending → verified) with a vendor-neutral sender (SMTP when the existing `SMTP_*` env config exists; console-deferred otherwise, tokens never logged).
- **Frontend identity proof flows** at `/id` and `/id/work-id` through the single API client (no scattered `fetch`), plus a shared session store.

## 2. Authentication architecture

Existing Phase 3 design retained (bcrypt, 15-min typed JWTs with `token_version`, opaque hashed refresh tokens with rotation + reuse-detection → family revocation). Added:

| Endpoint | Behavior |
|---|---|
| `POST /api/v1/auth/change-password` | verifies current password → new hash, bumps `token_version`, revokes all refresh sessions, returns a fresh pair (current client stays in) |
| `POST /api/v1/auth/forgot-password` | issues a hashed single-use reset token (60 min); **identical response for unknown emails** (no enumeration) |
| `POST /api/v1/auth/reset-password` | consumes token, sets new password, bumps version, revokes all sessions; replay → 401 |
| `POST /api/v1/auth/verify-email/send` | creates hashed single-use token (24 h) for the current user |
| `POST /api/v1/auth/verify-email` | consumes token → `email_verified_at` set; replay → 401 |
| `GET /api/v1/auth/sessions` | active refresh sessions (device/ip/created/expiry) |
| `POST /api/v1/auth/sessions/revoke-all` | kills every refresh session |
| `POST /api/v1/auth/mfa/enable|confirm|disable` | TOTP enable (confirm with a live code) / disable (requires current code) |
| Login flow | returns `mfa_required` + short-lived `mfa_token` when MFA enabled; `POST /auth/mfa/verify` completes login |

MFA is implemented with the standard library only (RFC 6238 TOTP, constant-time compare, ±1 window) — no new dependency. Secrets are stored base32 in `users.mfa_secret`; encryption-at-rest is tracked as follow-on (see §21).

**Rate limiting**: in-process sliding window (`app/core/ratelimit.py`), per-IP, attached to login (10/min), MFA verify (5/min), reset endpoints (5/min) → 429 envelope. Tested. Redis backing is a later-phase production concern (documented).

## 3. Account architecture

`users` = account: credentials (bcrypt), status, `token_version`, `email_verified_at`, MFA fields. Verification/reset tokens are **hashed at rest**, single-use (`used_at`), time-limited, and never exposed by any API — they travel only through the email transport (which never logs bodies).

## 4. Person architecture

`person_profiles` (1:1 user) now carries: preferred name, city, state/province, country code, phone, headline, summary, profile-photo key. Data minimization rule applied: only genuinely needed fields; DOB stays optional/unexposed. **Contact fields never appear on ordinary APIs** (`/auth/me` returns the public person summary only; full profile is owner-only via `/work-id`).

## 5. Work ID architecture

- `GET /work-id` returns the owner's complete identity spine (person + experience + education + skills + credentials + employment) — **no other user can read it** (404/existence hidden).
- Stable person-level ownership: every section references `person_profiles.id`, so future systems (applications, interviews, offers, employment, learning) attach to the person — never to a company→candidate ownership chain.
- `GET /work-id/completion`: percent + per-section met flags + missing list computed from **real structured data** with a configurable weight map in `services/person.py` (identity 10 / contact 5 / verified email 5 / education 15 / experience 25 / employment 15 / skills 15 / credentials 10). Verified: a fresh account = 0%; fully built but unverified email = 95%; verified email = 100%.

## 6. Education

Levels constrained to a catalog (`school · higher_secondary · diploma · vocational · undergraduate · postgraduate · professional_qualification`), `verification_status` defaults to `unverified` and is never self-claimed as verified. Institution/degree/field/dates supported.

## 7. Skills

Structured `skills` catalog (case-insensitive dedupe) + `user_skills` with `level` + `years_experience`. Free text is normalized into catalog entries so a standardized taxonomy can be layered on later without a rewrite.

## 8. Employment

`employments` extended: department, location, skills used, employment type, and explicit `verification_status` (`unverified` default — no fake employer verification). DELETE endpoint added.

## 9. Credentials

Already stateful; Phase 4 adds: education/experience/employment default `unverified`; owner update schemas cannot set `verified`/`verified_at`/`verification_source` (only the future verification pipeline can); states VERIFIED/UNVERIFIED/PENDING/EXPIRED/REVOKED enforced via `CREDENTIAL_STATUSES`.

## 10. Documents

Phase 3 document ownership/grants retained unchanged (owner = person; orgs need explicit grants; denials audited). Phase 4 consent model generalizes future sharing; the doc-grant records already answer the consent questions for document access and remain the document-level mechanism (see §21 note on future unification).

## 11. Consent architecture

New table `consents` + one reusable service (`services/consent.py`) + `/api/v1/work-id/consents`:

- WHO consented = `person_id`; TO WHOM = `grantee_user_id` XOR `grantee_organization_id`; TO ACCESS WHAT = `resource_scope` from a closed set (`work_id:documents`, `work_id:credentials`, `work_id:profile`, `application`); WHY = purpose; WHEN/UNTIL = granted_at/expires_at; REVOKED = revoked_at/by.
- Only the person can create/list/revoke their consents; cross-user attempts → 404 and are audited.
- Enforcement hook `find_live_consent(...)` exists for future workflows (applications, Athena actions).

## 12. Privacy model

`person_visibility_settings` — per Work ID section visibility (private/public/authorized_only), **default private**. `GET/PUT /work-id/privacy` validates scopes and values. Enforcement posture: the Work ID is never a public dump — no endpoint returns another person's data at all in this phase; visibility drives future authorized/public views. Contact details are excluded from summary payloads by schema design.

## 13. API endpoints

New/changed in Phase 4 (all existing Phase 3 endpoints unchanged):

| Method | Path | Purpose |
|---|---|---|
| POST | `/auth/change-password` | password change (returns fresh pair) |
| POST | `/auth/forgot-password` | reset request (no enumeration) |
| POST | `/auth/reset-password` | consume reset token |
| POST | `/auth/verify-email/send` · `/auth/verify-email` | email verification |
| GET/POST | `/auth/sessions` · `/auth/sessions/revoke-all` | session management |
| POST | `/auth/mfa/enable|confirm|disable` · `/auth/mfa/verify` | MFA foundation |
| POST | `/auth/login` | now returns `LoginResult` (MFA-aware) |
| GET | `/work-id/completion` | profile completion |
| GET/PUT | `/work-id/privacy` | visibility settings |
| GET/POST/DELETE | `/work-id/consents` · `/work-id/consents/{id}` | consent lifecycle |
| DELETE | `/work-id/employments/{id}` | employment record delete |
| PUT/POST | `/work-id/profile`, `/educations`, `/experiences`, `/employments` | accept new identity/level/verification fields |

Route count: 63 registered routes on the canonical app.

## 14. Frontend flows

- `frontend/src/lib/api/session.ts` — token store (localStorage for the proof), refresh/logout helpers, authed client (`lib/api/session.api`) — one controlled boundary.
- `/id` — register / login (with MFA second step) / me (email verification trigger, change password, revoke-all sessions, logout).
- `/id/work-id` — profile editing + completion meter + add/remove for education/skills/experience/credentials/employment + document metadata create/archive.
- `client.ts` now exposes `createApiClient(tokenProvider)`; pages contain no `fetch` calls. Typecheck ✅, eslint 0 errors, production build ✅.

## 15. Database changes

Additive to canonical tables only (0001-created tables + 4 new):

- `users` + `mfa_secret`, `mfa_enabled`
- `person_profiles` + `preferred_name`, `city`, `state_province`, `phone`
- `work_experiences` + `department`, `skills_used` (JSON), `verification_status`
- `educations` + `level`, `verification_status`
- `employments` + `department`, `location`, `skills_used`, `verification_status`
- NEW: `email_verification_tokens`, `password_reset_tokens`, `consents`, `person_visibility_settings`

## 16. Migrations

- `0002_identity_workid_core` — additive; validated locally (upgrade → downgrade → re-upgrade on scratch SQLite; 21 tables). **Not applied to any shared/production database.** ORM↔migration parity test still green.

## 17. Security controls

Hashed-at-rest single-use tokens · identical forgot-password responses · replay/expiry rejection on every token · MFA code verification with constant-time compare · per-IP auth rate limiting · password change revokes all sessions · token_version bump on password change/reset · contact/PII excluded from summary schemas · consent/document revocation ownership enforced · no secrets or plaintext passwords anywhere · email bodies never logged.

## 18. Audit events

New events: `auth.password_changed`, `auth.password_reset_requested`, `auth.password_reset`, `auth.email_verification_requested`, `auth.email_verified`, `auth.login.mfa_pending`, `auth.mfa_enabled`, `auth.mfa_disabled`, `auth.mfa.verify_failed`, `auth.sessions_revoked_all`, `consent.granted`, `consent.revoked`, `privacy.updated` (existing: register/login/refresh/logout, credential events, doc access, membership changes).

## 19. Tests (Phase 4 suites — all passing)

`test_account_phase4` — change-password rotation, forgot/reset (enumeration-safe, replay-safe), email verification lifecycle, sessions list/revoke-all, login rate limiting.
`test_mfa_phase4` — enable/confirm, MFA-gated login (mfa_token step, wrong code → 400), disable-with-code, TOTP unit tests (real logic).
`test_privacy_consent_phase4` — defaults private, update + validation, contact fields hidden from me, **user B cannot revoke/list user A's consents** (404), org consent, company membership never opens a person's Work ID (tamper → 404, HR sees only own empty Work ID).
`test_completion_workid_phase4` — completion 0→95→100 with real data criteria, new experience/education/employment fields, verification state never self-claimed verified, invalid education level → 422, employment delete.

**Full suite: 65 passed** (17 new). Tenant-isolation/ownership regressions from Phase 3 remain green.

## 20. Careers compatibility

Careers platform, its Supabase data, legacy backend, and existing frontend routes are untouched (legacy import verified). The `/id/*` proof pages are additive routes; nothing in the careers flow was modified.

## 21. Known limitations

- MFA secrets stored plaintext base32 in the DB (encryption-at-rest with the credential-protection work; a follow-on). TOTP only; no backup codes, no per-role enforcement yet (Phase 5).
- Email transport is SMTP-if-configured else console-deferred; no email vendor integration/deliverability tooling yet.
- Access tokens remain whole-session revocable only (per-token revocation not added).
- Rate limiters are in-process (single instance); Redis backing for multi-process deployments is a later-phase item.
- Document grants (`document_access_grants`) and general `consents` are not yet unified into one table — both answer the same consent questions; unification is a Phase 7 workflow concern.
- Person DOB is not exposed anywhere (field exists); policy on genuinely-required collection needs a product decision.
- Frontend tokens in localStorage (proof build); production auth storage redesign is a Phase 7 UI concern.

## 22. Production readiness (honest)

| Area | Verdict |
|---|---|
| Password hashing/storage | READY (bcrypt; Argon2id migration optional later) |
| Token handling (rotation, reuse, versioning, hashing-at-rest) | READY |
| Email verification / password reset mechanics | READY as architecture; transport depends on SMTP config |
| MFA | PARTIAL — foundation works; secrets-at-rest encryption + backup codes remain |
| Rate limiting | PARTIAL — in-process; Redis for multi-instance deployments |
| Person/Work ID ownership + isolation | READY (regression-tested) |
| Consent + privacy | READY foundation; enforcement in future workflows pending |
| RLS | UNKNOWN for canonical tables — Postgres RLS policies for canonical tables are a Phase-5 data-layer item (canonical tables are new; no live RLS yet) |
| Audit coverage | READY for the identity surface |
| Frontend flows | READY as functional proof only — not production UI |

**Not production-claimed** — tests passing ≠ production readiness for MFA-at-rest, multi-process rate limiting, email deliverability, and RLS on canonical tables.

## 23. Decisions requiring approval

1. MFA secrets-at-rest: accept plaintext base32 for now with encryption tracked, or bump encryption into an earlier phase?
2. MFA per-role enforcement timing (company/government/admin) — Phase 5 scope?
3. SMTP transport: keep console-deferred default or wire a specific email vendor (which one)?
4. Unify `document_access_grants` into `consents` during Phase 7 workflows, or keep both?
5. DOB collection policy (keep unexposed/optional vs remove).
6. Argon2id migration vs current bcrypt.

---

*End of Phase 4. No Phase 5 work has begun. Next: owner review, then Phase 5 (data layer / auth migration mechanics) per PHASE_2_ARCHITECTURE.md.*
