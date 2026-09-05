# CURSOR WAVE 9 — Production readiness

Local unified app: **http://localhost:3001**
Canonical API: **http://127.0.0.1:8000**
Hosted database: **UNTOUCHED**

| Category | Status | Reason |
|---|---|---|
| PUBLIC WEBSITE | **READY** (local) | Approved website is now the Next.js `/` and public routes. Visual source: `trabaajowebsite`. |
| AUTH | **READY** | Canonical `/login` `/register` on the same origin. No Supabase Auth. |
| DATABASE | **PARTIAL** | Local SQLite for DEV. Production still uses existing Supabase Postgres. No Wave 6–8 schema to apply. |
| SUPABASE | **PARTIAL** | Hosted project exists. No Wave 9 migration. Do not `db push` / `db reset`. |
| RLS | **PARTIAL** | Policies exist (Alembic 0010+). Local `p14_test` RLS suite still 11 skipped unless `TEST_PG_URL` is set. |
| RBAC | **READY** | Unchanged catalog. Local Super Admin is a DEV platform membership only. |
| STORAGE | **PARTIAL** | Canonical private documents + grants exist. Production bucket/signing env still required on the host. |
| AI | **PARTIAL** | Abstraction ready (`AI_PROVIDER=openai` + server `OPENAI_API_KEY`). Local API was running as `none` unless restarted. Never expose the key to the browser. |
| EMAIL | **PARTIAL** | SMTP abstraction exists. Local/prod SMTP not configured → messages deferred, no fake success. |
| PAYMENTS | **PARTIAL** | `PAYMENT_PROVIDER=mock` locally. `stripe` is allowed but **not** live-enabled. Do not collect real money. |
| VOICE/VIDEO | **BLOCKED** | `AI_STT_PROVIDER` / `AI_TTS_PROVIDER` default `none`. No provisioned WebRTC account. |
| SMS | **NOT REQUIRED** | Canonical auth is email/password + TOTP MFA foundation. No SMS/OTP provider required. |
| NOTIFICATIONS | **PARTIAL** | In-app notifications exist. Email notifications need SMTP. |
| MONITORING | **PARTIAL** | `/health` + structured request logs exist. No production uptime/error product configured. |
| RATE LIMITING | **PARTIAL** | Registry exists. Default store `memory`. Multi-instance must set `RATE_LIMIT_STORE=db` (or Redis later). |
| GITHUB | **READY** to push | Production repo is `TheDotProtocol/asktrabaajo`. |
| VERCEL | **PARTIAL** | Existing project is connected to this repo. Root directory must be `frontend`. Env audit is incomplete without dashboard access. |
| DOMAIN | **BLOCKED** | `PRODUCTION DOMAIN REQUIRED`. Website source mentions `www.asktrabaajo.com` as intended canonical; live DNS not verified here. |
| SSL | **PARTIAL** | Vercel provides TLS when a domain is attached. Not verified. |
| CORS | **READY** (local) | `CORS_ORIGINS` already includes `http://localhost:3001`. Production must add the real origin. |
| SECURITY | **PARTIAL** | Secret scan of tracked files: no API keys / JWT blobs / DEV password. Public repo — keep secrets in Vercel/host env only. |
| BACKUPS | **BLOCKED** | Hosted backup/PITR not verified. |
| PITR | **BLOCKED — BACKUP/PITR NOT VERIFIED** | No live database change performed. |
