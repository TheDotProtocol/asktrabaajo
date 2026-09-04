# Phase 19 — Provider Validation

## Status

No production provider is configured; everything runs on the safe mock/degraded paths. This is by design and asserted by tests — nothing here claims production capability.

| Provider | Mode | Validation this phase |
|---|---|---|
| **AI (Athena)** | `none` (safe degraded) | Suite: provider-abstraction tests, budgets, tool authorization, prompt injection — all green with deterministic/mocked paths |
| **STT / TTS (voice)** | `none` (disabled) | Media calls fail with `ai.media_unavailable` — never fabricated (suite) |
| **Video / WebRTC** | not configured | Governed design documented (Phase 16); no provider wired |
| **Payments** | `mock` (sandbox) | Commerce suite green (Decimal money, webhooks, refunds, idempotency); billing self-service + finance boundary exercised in staging smoke; **no real-money path exists** |
| **Email / notifications** | not configured | In-app notification records only |
| **Storage** | Supabase, 3 private buckets | Read-only: all `public=false`; per-object policies need dashboard review |
| **Database** | Supabase session pooler | Identity verified read-only; live writes gated |

## Staging-mode integration proof

`P19_STAGING_SMOKE_PASS` booted the canonical app with `ENVIRONMENT=staging`, `AI_PROVIDER=none`, `PAYMENT_PROVIDER=mock` against scratch PG 16 and ran auth → AI interview → report → human decision → billing → RBAC/cross-tenant denials. This proves the provider-neutral seams (AI/voice/payment) work end-to-end in staging configuration without any real provider.

## To reach staging with real providers (operator + runbook)

1. Provision and set `AI_PROVIDER`/keys; verify budgets + rate limits + tool registry.
2. Keep `PAYMENT_PROVIDER=mock` (or a sandbox provider) until a production provider is approved; then wire webhooks behind TLS + verify signatures end-to-end.
3. Provision voice/video only via the Phase 16 media abstraction; verify STT/TTS/transport with consent + no-recording-by-default.
4. Re-verify storage policies for the 3 private buckets.