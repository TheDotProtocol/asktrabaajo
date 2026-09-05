# CURSOR WAVE 9 — Vercel environment audit

Connected repository: **https://github.com/TheDotProtocol/asktrabaajo**

Vercel CLI was not available in this session, so Production / Preview / Development **values currently stored in the Vercel dashboard were not readable**. Names below are the **actual application variables**, not invented aliases.

Do **not** put secrets in `NEXT_PUBLIC_*`.

## DO I HAVE TO ADD ANYTHING TO VERCEL?

**YES** — before a production deployment can talk to the canonical API and providers.

After changing variables, **redeploy**. Variable edits do not affect an already-built deployment.

## Frontend (`frontend` Root Directory)

| VARIABLE | LOCAL | PREVIEW | PRODUCTION | REQUIRED | SECRET | STATUS |
|---|---|---|---|---|---|---|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Canonical API origin | Canonical API origin | YES | no | VALUE REQUIRED FROM OWNER for Preview/Production |
| `NEXT_PUBLIC_APP_URL` | empty (same origin) | empty or public origin | empty or public origin | no if same origin | no | Leave empty on the unified app |
| `NEXT_PUBLIC_SITE_URL` | empty | public site origin if used | public site origin if used | no | no | Optional |
| `NEXT_PUBLIC_SUPABASE_URL` | local `.env.local` only | not required for canonical auth | not required for canonical auth | no | no | Legacy Careers only |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | local `.env.local` only | do not add unless Careers is enabled | do not add unless Careers is enabled | no | public-ish | Do not treat as a server secret |
| `NEXT_PUBLIC_TEST_USER_PASSWORD` | must stay empty | must stay empty | must stay empty | no | YES if set | **Do not add** |

## Backend (not Vercel unless the API is also hosted there)

The canonical API is FastAPI on port 8000 locally. If the API is deployed elsewhere, set these on **that** host — not as `NEXT_PUBLIC_*`.

| VARIABLE | LOCAL | PREVIEW | PRODUCTION | REQUIRED | SECRET | STATUS |
|---|---|---|---|---|---|---|
| `DATABASE_URL` | isolated sqlite | hosted Postgres | hosted Postgres | YES in prod | YES | Already used by existing backend config. Do not invent a new database. |
| `SECRET_KEY` | local-only dummy | VALUE REQUIRED FROM OWNER | VALUE REQUIRED FROM OWNER | YES | YES | Fail-fast in staging/production |
| `CORS_ORIGINS` | `http://localhost:3000,http://localhost:3001` | Preview URL(s) | Production origin | YES | no | Must include the Vercel/app domain |
| `AI_PROVIDER` | `none` unless owner sets `openai` | `openai` or `none` | `openai` or `none` | YES | no | `none` is safe degraded |
| `OPENAI_API_KEY` | may exist locally | VALUE REQUIRED FROM OWNER | VALUE REQUIRED FROM OWNER | if `openai` | YES | Never send to the browser |
| `AI_OPENAI_MODEL` | `gpt-4o-mini` default | optional | optional | no | no | |
| `SMTP_HOST` / `SMTP_PORT` / `SMTP_USER` / `SMTP_PASSWORD` / `SMTP_FROM` | unset | VALUE REQUIRED FROM OWNER | VALUE REQUIRED FROM OWNER | for real email | YES | Contact/auth mail otherwise deferred |
| `PAYMENT_PROVIDER` | `mock` | `mock` until go-live | `mock` or `stripe` | YES | no | Do **not** switch live collection on just because a key exists |
| `STRIPE_SECRET_KEY` | unset | VALUE REQUIRED FROM OWNER | VALUE REQUIRED FROM OWNER | if stripe | YES | Not wired as live in this wave |
| `PAYMENT_WEBHOOK_SECRET` | unset | VALUE REQUIRED FROM OWNER | VALUE REQUIRED FROM OWNER | if stripe | YES | |
| `RATE_LIMIT_STORE` | `memory` | `db` recommended | `db` required for multi-instance | recommended | no | |
| `GOVERNMENT_MIN_COHORT_SIZE` | `10` | `10` | `10` | no | no | |
| `RLS_SESSION_CONTEXT` | false on sqlite | true only with `asktrabaajo_app` | true only with `asktrabaajo_app` | when RLS is on | no | |
| `AI_STT_PROVIDER` / `AI_TTS_PROVIDER` | `none` | `none` | `none` until provisioned | no | no | Voice/video BLOCKED |

## PRODUCTION DOMAIN (discovered, not invented)

The connected Vercel project already aliases:

- `https://www.asktrabaajo.com`
- `https://asktrabaajo.com`
- `https://asktrabaajo.vercel.app`

Add those origins to API `CORS_ORIGINS`. Set frontend `NEXT_PUBLIC_API_URL` to the public canonical API origin (VALUE REQUIRED FROM OWNER — the API host is not this Next.js deploy).

## Vercel project settings to verify in the dashboard

- Repository: `TheDotProtocol/asktrabaajo`
- Production branch: `main`
- Framework: Next.js
- **Root Directory: `frontend`**
- Build command: `npm run build` (or Vercel default)
- Install command: `npm install`
- Do not point Vercel at the separate `trabaajowebsite` repository
