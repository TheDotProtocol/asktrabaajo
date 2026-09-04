# Phase 18 — Backup & Disaster Recovery

## Backup / PITR gate (BLOCKED — operator action)

Backup/PITR protection **cannot be verified over SQL** — it is a Supabase project-level setting visible in the dashboard (Project Settings → Backups / PITR). Per the phase hard-stop rule, **no live schema mutation may occur until the operator confirms** scheduled backups and/or point-in-time recovery are enabled for project `zrvrjqwboylvvzusorry`.

This document does not claim backup protection exists. Status: **UNKNOWN until operator confirmation**.

## Required retention / purge jobs (specification)

The platform has no background worker yet, so these are specified, not running:

| Data | Policy (documented) | Job |
|---|---|---|
| Athena sanitized messages | 90-day retention (`ai_message_retention_days`) | Lazy purge on read or scheduled delete beyond age |
| AI sessions / confirmations | TTL expiry (60/15 min) — lazy expiry implemented | Optional scheduled sweep |
| Interview sessions (completed) | Metadata retained per audit policy; raw answers never stored | None needed for answers |
| Transcripts / recordings | Feature does not exist; governed designs only | N/A |
| Commerce transactions/invoices | Kept per finance record-keeping | Archival job when defined |
| Audit log | Append-only; retention by future policy | Archival job when defined |

## Disaster recovery scenarios

| Failure | Mitigation | Status |
|---|---|---|
| Database failure / corruption | Supabase Restore (needs backup/PITR confirmed) | NOT DEFINED until gate |
| Accidental destructive SQL | App role is least privilege; no destructive path in migrations (asserted by tests); operator discipline | Controls in place |
| Canonical schema rollback | `alembic downgrade base` (verified 0013/0014 roundtrips SQLite + PG) | Defined |
| Reconciliation reversal | Rename is instantly reversible (see reconciliation doc) | Defined |
| Application failure | Health endpoints + redeploy from runbook | Defined |
| Frontend failure | Static/Next build reproducible from repo | Defined |
| AI provider failure | Provider abstraction, `none` safe-degraded, bounded loops/timeouts | Defined |
| Payment provider failure | Mock/sandbox only; provider-neutral interface; idempotency + webhook replay protection | Defined (no prod provider) |
| Email failure | Not applicable — no email provider configured | NOT CONFIGURED |
| Storage failure | Supabase storage managed; buckets private | Operator-managed |
| Key rotation | `backend/.env` single source; operator updates after rotation | Procedure documented |

**RTO/RPO: NOT DEFINED** — not formally established; requires operator decision once backup/PITR is confirmed.

## Protection principles

- Legacy data: preserved in place; reconciliation touches no legacy rows.
- Rollback honesty: only what is reversible is claimed reversible; a full restore path depends on the PITR gate.
- No credentials in docs/commits; secrets live only in `backend/.env` (ignored) and the operator's secret manager.
