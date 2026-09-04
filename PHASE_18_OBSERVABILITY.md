# Phase 18 — Observability

## In-repository observability surface

- **Health:** canonical backend exposes `/health`; FastAPI `/docs`/`/openapi.json` for surface discovery (must be restricted or proxied in production).
- **Structured audit:** canonical audit trail records every meaningful action (recommendations, tool calls, career-plan mutations, applications, interview sessions/consent/questions/evaluations/reports/decisions, commerce transactions/refunds/webhooks, finance operations). Phases 14–17 adversarial tests assert audit rows land for the important paths.
- **AI usage:** per-user budgets over `ai_usage_log`; provider abstraction records per-call usage; rate-limit policy layer records hits (`rate_limit_hits` when `RATE_LIMIT_STORE=db`).
- **Commerce/payment:** transaction + refund + webhook-event tables carry provider references, statuses, failure reasons; webhook handling records signature/duplicate/replay outcomes.
- **Interview:** session state machine, consent snapshots, integrity signals, evaluation/report creation all audited; no raw answers/audio/video stored or logged.

## Never-log list (enforced by design, restated for ops)

Passwords, tokens, `DATABASE_URL`, AI/payment/webhook secrets, CVV/card data, raw private documents, unnecessary raw interview responses, raw audio/video.

## Missing infrastructure (launch items)

The repository has **no production monitoring stack** (metrics endpoint, log aggregation config, error tracker, uptime probes) and **no payment/AI provider dashboards** because no provider is configured. Required for production, not implemented here:

1. Structured log shipping (e.g. stdout JSON → aggregator).
2. Health-check probes wired into the load balancer / orchestrator.
3. Error-rate + latency dashboards for the canonical API.
4. Database monitoring: Supabase project metrics (connections, CPU, storage) via dashboard.
5. Payment-webhook monitoring + AI-provider monitoring once providers are configured.
6. Scheduled retention/purge jobs (AI messages, expired interview sessions, transaction/audit archival policy) — no background worker architecture exists yet; retention policies are documented in `app/core/config.py` and Phase docs, and the required purge job is specified in `PHASE_18_BACKUP_DISASTER_RECOVERY.md`.

## Database observability

Live Supabase extensions include `pg_stat_statements` (query stats available). `pg_stat_activity` gives connection visibility on demand. No long-term metrics collector is configured — operator item.

## Recommendation

Deploy the canonical API behind the runbook with stdout-JSON logging first; add an aggregator and dashboards before production traffic. Marking observability **PARTIAL** (audit complete in-app; external monitoring not provisioned).
