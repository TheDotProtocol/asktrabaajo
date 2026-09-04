# PHASE 14 — ATHENA SECURITY MODEL

Status: PASS (adversarial test suite green; see `PHASE_14_EVALUATION.md`)

## 1. Threat model

Athena is exposed to three hostile inputs simultaneously:

1. **The platform user** — may attempt tools/sessions/confirmations they do not
   own or are not entitled to (IDOR/BOLA, mode escalation).
2. **The model output** — may attempt unregistered tools (`run_sql`,
   `fetch_url`, `read_file`, `execute_shell`), wrong-object arguments, or
   malformed arguments; model output is **never** authorization.
3. **Untrusted content** (job descriptions, resumes, documents, messages,
   search results) — prompt-injection attempts to redefine instructions,
   reveal secrets, escalate privileges, or trigger actions.

The security boundary is **application code**, never the LLM.

## 2. Authorization chain (every tool call)

```
TOOL NAME from model
  → registry lookup (unknown ⇒ refused + audited)
  → input-schema validation (malformed ⇒ refused before anything else)
  → session active + owner + mode contains tool
  → org permission check (authz.require_permission on the org scope) when declared
  → risk class:
       READ_ONLY / LOW_RISK_WRITE ⇒ execute now
       HIGH_RISK_WRITE ⇒ execute only with an APPROVED, unexpired
                         confirmation whose stored canonical scope
                         (scope_hash over canonicalized args) matches exactly
```

Key invariants enforced in code:

- `session.mode not in tool.modes` ⇒ `PermissionDeniedError`.
- Org-scoped tools require `session.organization_id`; permission is checked
  against that org via the existing RBAC registry (e.g. `candidates.search`,
  `communications.send`, `talent.outreach.create`).
- Candidate-private tools (`get_my_*`, `get_application_status`, …) live only
  in the jobseeker mode with `data_scope="own"`; an employer session can never
  invoke them, and vice-versa for org tools in a jobseeker session.
- A confirmation is bound to: session, user, tool name, and a SHA-256 hash of
  the canonicalized argument JSON. An approved confirmation for opportunity A
  never authorizes opportunity B (different `scope_hash` ⇒ new confirmation).
- Confirmations carry a 15-minute TTL (lazy expiry), are single-use
  (status PENDING → APPROVED/DENIED), and the stored scope is re-validated
  through the tool schema and re-authorized at execution time.

## 3. No arbitrary code / SQL / HTTP / filesystem

There is no interpreter, SQL executor, shell, file reader, or HTTP client
registered as a tool. The model may only select from the fixed 26-tool registry
in `app/services/athena_tools.py`, and the adversarial suite proves attempts at
`run_sql`, `fetch_url`, `read_file`, and `execute_shell` are refused and
audited.

## 4. Data minimization

`athena_context.SENSITIVE_FIELD_NAMES` is a test-enforced contract listing
fields that must never enter Athena context (phone, email, date_of_birth,
government_id, passport, tax_id, business_license, address, kyc,
document_content, password, token, secret, mfa). The context builder emits only
a whitelisted digest; audit/usage/confirmation rows store metadata only — no
message bodies, no prompts, no report text, no document contents, no secrets
(asserted row-by-row in the audit-hygiene tests).

## 5. Prompt-injection defense

- The system prompt is the only instructions source; everything the user types
  or tool results return is framed as untrusted DATA.
- Injection cannot redefine tools (registry is fixed), permissions (checked in
  code), or identity (session ownership is server-side).
- High-risk execution cannot be triggered by language alone: a tool call still
  requires the human confirmation gate; the adversarial tests drive hostile
  "job descriptions" and "ignore your instructions" prompts through a fake
  provider and assert that (a) no application row was created without a
  confirmation, (b) sensitive values never appear in stored messages or the
  digest.

## 6. Employment-decision safety

Code + system prompt both forbid: protected-characteristic inference or
ranking, facial-emotion scoring, lie detection, medical/psychological
diagnosis, hidden personality inference, autonomous rejection, and opaque
"hireability" claims. Ranking tools call the existing explainable matching
service and return explainable signals. No tool in the registry performs an
employment decision; humans decide through existing product workflows.

## 7. Audit + observability

Every sensitive Athena event is audited through the canonical audit service:

- `athena.session.created`, `athena.message`, `athena.tool.executed`,
  `athena.tool.denied`, `athena.confirmation.requested`,
  `athena.confirmation.decided`, `athena.confirmation.expired`.

Audit metadata contains: actor, mode, tool, risk, read_only flag, result keys,
confirmation id, decision — never bodies or secrets. `ai_usage_log` records
user/org/session/mode/feature/provider/model/token counts/latency/status; the
schema has no content column by construction.

## 8. Provider/credential handling

- Keys live in server env only; never logged, committed, or in responses.
- Provider identity is configuration-driven (`AI_PROVIDER`); `none` default ⇒
  deterministic `ai.provider_unavailable`, never a fake reply.
- No provider internals leak to end users; errors are provider-neutral codes.

## 9. Confirmation/abuse controls

- `athena.chat` / `athena.tool` / `athena.high_risk` rate-limit policies.
- Per-user daily budgets over `ai_usage_log` (messages and tool calls).
- Sessions expire lazily; concurrent sessions are isolated by ownership +
  per-session persistence keys (cross-identity tests assert no leakage).

## 10. Non-negotiables honored

1. No universal admin shortcut — Athena tools carry explicit permissions.
2. No cross-tenant access — org checks at authorization + handler level.
3. No enforcement through client-side authorization — all server-side.
4. No raw secrets in source.
5. No sensitive report bodies in generic events.
6. No private Work ID disclosure — digests exclude sensitive fields.
7. No private documents exposed through Athena — no document-content tool.
8. No private communications in audit — audit carries keys, never bodies.
9. No AI self-authorization.
10. No autonomous high-impact employment action — confirmation gate + humans.
