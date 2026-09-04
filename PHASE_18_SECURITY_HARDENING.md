# Phase 18 — Security Hardening

## Secret safety (verified)

- `backend/.env` holds `DATABASE_URL` (operator-supplied). It is **gitignored** and **untracked** — confirmed by `git status` and `git check-ignore`.
- A tracked-repository secret scan (filenames + pattern match over tracked content) found **no committed credentials**: no passwords, API keys, JWT secrets, private keys, or database URLs in tracked files. Nothing was printed.
- This document and every Phase 18 document contain **no secret material**.

## Live domain findings

| Area | State | Action |
|---|---|---|
| Database connection | Session pooler, identity verified | Blocked from writes pending Backup/PITR gate |
| App role | Absent on live | Create only as part of the gated reconciliation |
| RLS (legacy) | All 21 tables enabled, 36 policies | Untouched |
| Storage buckets | 3 buckets, **all private** (`public=false`): `kyc-documents`, `kyc-selfies`, `user-documents` | Keep private; per-object policies must be dashboard-verified pre-launch |
| Legacy anon/service keys | Stored key is stale (401 on REST) | Operator rotates/re-supplies when legacy REST is re-enabled |

## Canonical security posture (carried from Phases 12–17, re-verified)

- **AuthN:** canonical `/api/v1/auth` (register/login/refresh/logout, short-lived access + refresh), fail-fast secret validation in staging/production.
- **RBAC:** centralized permission catalog; `billing.manage` (org) is separate from `finance.manage` (platform); support cannot refund; org admins cannot refund.
- **Tenant isolation:** all canonical queries scoped by org/person; adversarial suites (Phases 14–17) cover cross-user, cross-org, cross-company paths — all fail closed (403/404).
- **Athena:** provider abstraction (default `none` = safe degraded), 39 controlled tools, no SQL/filesystem/shell/HTTP tools, budgeted + rate-limited, audited, confirmation framework for high-risk actions. **Zero Athena billing-mutation tools** (no charge/refund/cancel path).
- **AI interview:** token-hash session entry (no existence oracle), consent-before-start, prohibited-topic gating, no raw answer persistence, no facial-emotion/lie/protected-inference logic anywhere, human decision only.
- **Commerce:** Decimal money, provider references only (no card data), HMAC-signed webhooks with replay protection, idempotent transactions/refunds bounded by paid balance, `payment_provider` validator (none|mock|stripe).
- **Rate limiting:** policy layer with `memory` (dev/test) and `db` (multi-instance) stores. **See production blocker below.**
- **CORS:** configurable allow-list (`cors_origins`); default is localhost dev origins, must be set to real origins for production.
- **Prompt injection:** external content (jobs, profiles, answers) treated as untrusted; adversarial Athena suites green.

## Production hardening findings

1. **Distributed rate limiting — PRODUCTION BLOCKER until configured.** Default store is in-process `memory`. For a multi-instance deployment, set `RATE_LIMIT_STORE=db` (multi-instance-safe over `rate_limit_hits`) or provision Redis-backed storage behind the same policy layer. Single-instance deployments are fine on either.
2. **Security headers:** canonical app does not yet set HSTS/CSP/`X-Content-Type-Options` etc. — verify against the frontend and add via middleware or the reverse proxy in the runbook (must not break the Next.js app).
3. **`RLS_SESSION_CONTEXT` must be `1`** in staging/production and the app must connect as `asktrabaajo_app`; the config guard already rejects sqlite + RLS in non-dev.
4. **Environment discipline:** `SECRET_KEY`, AI/payment/webhook keys are env-injected only; production must refuse insecure defaults (validators already do).
5. **Storage policies** for the three private buckets should be reviewed from the dashboard before canonical document flows attach; nothing public was found.

## Do-not list (live)

No live DDL, no legacy RLS edits, no storage-policy edits, no production payment activation, no key rotation performed from here. All are gated operator actions documented in the launch checklist.
