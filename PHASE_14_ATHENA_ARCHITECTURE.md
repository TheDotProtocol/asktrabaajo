# PHASE 14 — ATHENA AI CORE: ARCHITECTURE

Status: IMPLEMENTED (backend/intelligence foundation — no UI consumed, no provider
credential required to run)

Companion documents:

- `PHASE_14_ATHENA_SECURITY.md` — threat model, adversarial tests, data rules
- `PHASE_14_ATHENA_TOOLS.md` — the full tool registry with permissions/risk
- `PHASE_14_ATHENA_DATA_POLICY.md` — data minimization, retention, privacy
- `PHASE_14_ATHENA_EVALUATION.md` — deterministic evaluation fixtures/results
- `PHASE_14_REPORT.md` — phase summary + status block

---

## 1. Position in the platform

Athena is the **controlled intelligence layer** above the canonical AskTrabaajo
platform (FastAPI modular monolith, PostgreSQL, migrations 0001–0011, 200
`/api/v1` routes, 66 canonical tables). It is NOT a database administrator, a
superuser, an unrestricted SQL agent, or an autonomous decision-maker. It is an
orchestration layer that can only request **explicitly registered tools**, each
of which calls the **same canonical application services the REST API uses**.

The model is never the security boundary. The model is never the authorization
authority. The model is never the final employment decision-maker.

## 2. Architecture diagram

```
CLIENT (authenticated user)
  │  POST /api/v1/athena/session | /message | /confirm | /tools | /usage
  ▼
AUTHENTICATION  (Bearer JWT → canonical user; suspended sessions already gated)
  ▼
ATHENA SESSION  (owned row: user, mode, org ctx, purpose, correlation_id, TTL)
  ▼
MODE POLICY     (jobseeker | employer | recruiter — server-derived eligibility)
  ▼
CONTEXT BUILDER (whitelist-only digest — MINIMUM NECESSARY DATA, never the row)
  ▼
PROVIDER        (AIProvider abstraction — 'none' default ⇒ safe AI error)
  │   tool_calls ▼            (bounded loop, max ai_chat_max_turns)
  ▼
TOOL REGISTRY   (fixed, declared registry — unknown names always refused)
  ▼
TOOL AUTHORIZATION  (mode ∩ permission ∩ org tenant ∩ risk — application code)
  ▼
HIGH-RISK GATE  (READ/WRITE split; HIGH_RISK_WRITE ⇒ explicit confirmation)
  ▼
CANONICAL APPLICATION SERVICE  (same services as the REST API)
  ▼
DATABASE / EXTERNAL SERVICES   (never reached by the model directly)
  ▼
RESULT FILTERING + AUDIT + USAGE LOG  (metadata only; no bodies/secrets)
```

What the model can NEVER do directly: reach the database, filesystem, shell,
private storage, admin functions, or arbitrary HTTP. The only surface exposed
to the model is the tool-call envelope of the current session's mode, and every
tool call is validated against the registry and authorized in code before any
handler runs.

## 3. Provider abstraction (`app/services/ai_provider.py`)

- `AIProvider` protocol with a `chat(messages, tools=...)` operation returning a
  validated `AIResponse` (content + typed `tool_calls` + `usage`).
- Capabilities declared per provider: `text_generation`, `structured_output`,
  `tool_calling` (only what is actually implemented).
- `OpenAIProvider` adapter (config-driven model `ai_openai_model`); provider
  credentials are read from `OPENAI_API_KEY` at runtime only — never logged,
  never stored, never sent to the frontend.
- Config `ai_provider` is `none` by default. With no provider configured the
  API returns a provider-neutral `ai.provider_unavailable` error (HTTP 502) —
  **it never fabricates an AI response pretending a provider is connected**.
- Business logic carries no provider-specific assumptions; future providers
  (Anthropic, local models, etc.) add an adapter behind the same interface.

## 4. Athena session (`app/models/athena.py`, `app/services/athena.py`)

`athena_sessions` rows carry: owner user, mode, organization context (for
employer/recruiter), purpose, status (`active`/`expired`/`closed`), correlation
id, `expires_at`, `last_active_at`. Server-side rules:

- Eligibility is **derived**, never client-declared: jobseeker requires a
  `PersonProfile`; employer/recruiter requires an org membership in an
  eligible role and an explicit org scope the user belongs to; government and
  platform-operator modes are architecture-only in this release (no tools).
- Ownership: every session access re-checks `session.user_id == user.id`.
- Lazy expiry: `expires_at` is compared on every access — no scheduler needed
  (naive-UTC comparison helpers keep SQLite and PostgreSQL identical; every PG
  connection is pinned to `SET TIME ZONE 'UTC'` in `app/db/session.py` so
  stored naive-UTC timestamps round-trip exactly on both dialects).

## 5. Modes

| Mode | Eligible when | Tools in this release | Notes |
|------|---------------|----------------------|-------|
| jobseeker | person profile exists | own-data + public discovery + low/high-risk writes | full tool set |
| employer | org membership (recruiter/hr/hiring_manager/org_admin) + org scope | org-scoped talent/applications/communications tools | permission-gated |
| recruiter | same as employer | same org tool set | permission-gated |
| government | government membership | none (architecture only) | no individual-level access |
| platform_operator | platform super-admin role | none (architecture only) | no auto-enforcement |

## 6. Context builder (`app/services/athena_context.py`)

Builds a digest of whitelisted, job-relevant fields — never the user's database
row. For a jobseeker: headline, summary, city/country, skills (name/level/years),
experience (role/company/dates/current), education, credential titles+status,
career goals, application-status counts. Excluded **by construction** (and
test-enforced): phone, email, date of birth, government/passport/tax IDs,
business license, addresses, KYC, document content, authentication credentials.

## 7. Chat orchestration

`POST /athena/message` → owned session check → chat rate limit + daily budget →
context digest → provider call with the mode's tool schemas → bounded tool loop
(`ai_chat_max_turns`, default 3):

- no tool calls → assistant reply persisted, return
- tool calls → each is validated against the registry, authorized, executed
  (or confirmation-requested); tool results feed the next provider turn
- a high-risk action request pauses the loop and returns a
  `pending_confirmations` list — the human decides via `/athena/confirm`

Provider failures mid-loop are converted to a safe error result; the loop never
"performs the action anyway" as a fallback.

## 8. Database changes

Migration `0011_athena_ai_core` (additive, 63 → 66 tables):

| Table | Purpose | Why existing tables are insufficient |
|---|---|---|
| `athena_sessions` | owned, mode-scoped session with org ctx + TTL | canonical session concept for AI; existing auth sessions are token-only |
| `athena_messages` | sanitized conversation (system/user/assistant/tool envelope) | no generic "chat dump"; explicitly scoped to Athena, retention-policy aware (`ai_message_retention_days`) |
| `athena_action_confirmations` | human authorization for high-risk tool calls (exact canonical scope, expiry, decision) | the confirmation/authorization record for tool actions |
| `ai_usage_log` | provider-neutral usage/cost/rate-limit accounting | per-user daily budgets + observability |

All four are user-owned rows (RLS stage-D in the Phase 13 matrix: owner + system
writer). No new identity/user/organization/communication/governance domains were
duplicated.

## 9. Configuration surface

| Setting | Default | Meaning |
|---|---|---|
| `AI_PROVIDER` | `none` | `none` (safe) or `openai` |
| `OPENAI_API_KEY` | — | server-side provider credential (env only) |
| `AI_OPENAI_MODEL` | `gpt-4o-mini` | model id for the OpenAI adapter |
| `AI_CHAT_MAX_TURNS` | 3 | bounded provider-tool loop |
| `AI_MESSAGE_RETENTION_DAYS` | 90 | sanitized message retention policy |
| `ATHENA_SESSION_TTL_MINUTES` | 60 | lazy session expiry |
| `ATHENA_CONFIRMATION_TTL_MINUTES` | 15 | confirmation window |
| `ATHENA_DAILY_MESSAGES_PER_USER` | 100 | per-user daily chat budget |
| `ATHENA_DAILY_TOOL_CALLS_PER_USER` | 200 | per-user daily tool budget |

Rate-limit policies (platform registry): `athena.chat`, `athena.tool`,
`athena.high_risk`.

## 8 (sec). Failure semantics

| Condition | Behavior |
|---|---|
| provider unavailable / no key | HTTP 502 `ai.provider_unavailable` — no fabricated reply |
| provider timeout/exception | tool-loop error result, message persisted, no side effects |
| unknown tool name | refused + audited `athena.tool.denied` |
| tool args invalid | refused (HTTP 422 `ai.tool_validation_failed`) before authorization/execution |
| authorization failure | refused + audited, nothing executed |
| rate limit / daily budget | HTTP 429 `ai.rate_limited` |
| session expired | HTTP 422 — session flipped to `expired` |

## 9. Production readiness

- **Ready (code-level):** provider-neutral orchestration, tool registry,
  authorization, confirmation gate, minimized context, audit/usage, rate
  limits, safe degradation, SQLite + PostgreSQL parity (UTC-pinned sessions).
- **Requires external infrastructure:** a real AI provider credential +
  `AI_PROVIDER=openai` (or another adapter); production RLS enablement for the
  new tables per the Phase 13 runbook; a retention purge job; streaming if the
  future UI needs token streaming.
- **Deferred (not in scope):** full Career Advisor (Phase 15), AI Interview,
  Government Athena tools, Platform-Operator Athena tools, embeddings/vector
  search, long-term memory, web access.
