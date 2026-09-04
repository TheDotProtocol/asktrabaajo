# PHASE 14 — ATHENA DATA POLICY

Status: PASS (data-minimization contract enforced by tests)

## 1. Principles

Athena follows the AskTrabaajo privacy model: **data minimization, purpose
limitation, least privilege, consent, auditability, retention control, user
control**. "AI needs everything" is never assumed.

## 2. What enters Athena context (whitelist)

For the owning jobseeker (`build_profile_digest`):

- headline, short summary (capped 2000 chars), city/country
- skills: canonical name, level, years experience
- experience: role, company, start/end dates, current flag
- education: degree, institution, field, level
- credentials: title, issuer, verification status (never document content)
- career goals: title, target role/industries, primary flag
- application status counts (aggregate only)

For an employer/recruiter session (`build_org_digest`): organization name, kind,
status — plus whatever the org-scoped tools return (the same authorized views
the REST API returns: discoverable candidates, org applications, org
conversations).

## 3. What never enters Athena context (deny-list, test-enforced)

`SENSITIVE_FIELD_NAMES` in `app/services/athena_context.py`:

phone, email, date_of_birth, government_id, passport, tax_id, business_license,
address, kyc, document_content, password, token, secret, mfa.

The digest is constructed from whitelisted model attributes — sensitive fields
are excluded by construction, and the tests assert the deny-list strings and
the actual sensitive values (`+27 …`, DOB year) never appear in the digest or
in stored messages.

## 4. What never gets stored

- `athena_messages` stores sanitized role/content/tool-call envelopes for the
  session (user-typed text is the conversation itself; the audit trail and
  usage log never duplicate it).
- `ai_usage_log` has **no content column** — counts, model, latency, status,
  error code only.
- Audit rows for Athena carry metadata (mode, tool, risk, result keys,
  confirmation id, decision) — never prompt text, message bodies, document
  contents, or secrets. This is asserted per-row in the audit-hygiene test.
- `athena_action_confirmations` stores the canonical scope JSON (object ids +
  bounded parameters) needed to re-execute safely — not raw investigation or
  message material.

## 5. Retention

- `ai_message_retention_days` (default 90) documents the retention policy for
  sanitized Athena messages. A purge job is a later operational concern — no
  scheduler exists yet; the setting is the policy anchor.
- Sessions expire after `athena_session_ttl_minutes` (lazy); confirmations
  after `athena_confirmation_ttl_minutes`.

## 6. Purpose limitation + consent

- Modes are derived from the authenticated identity and a declared purpose;
  the session records the purpose.
- High-risk actions (applying, sending messages/outreach) require explicit
  per-action human confirmation — the consent gate for consequential writes.
- Government and platform-operator modes expose no tools in this release;
  future capability must pass a separate authorization design before any
  data surface opens.

## 7. User control

- Users see their own sessions/messages via the session endpoints and their
  own usage via `GET /athena/usage` (own rows only).
- Confirmation requests are visible and decidable by the owning user only;
  sessions can be closed by their owner.
- No invisible long-term "memory": Athena context is rebuilt per request from
  platform state, never from an unbounded private memory store.

## 8. Future-facing rules (documented, not yet enabled)

- Embeddings/vector search will require provider-neutral abstraction, model
  version tracking, provenance, deletion/rebuild strategy, tenant isolation —
  and will NOT embed sensitive documents indiscriminately.
- Web access, if ever introduced, requires domain restriction, provenance,
  prompt-injection defense, rate limits, caching, and attribution — and is NOT
  part of this phase.
