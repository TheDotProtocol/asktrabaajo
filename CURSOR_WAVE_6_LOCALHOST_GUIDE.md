# CURSOR WAVE 6 — LOCALHOST GUIDE

Run AskTrabaajo locally **without** the hosted Supabase database.

## Requirements

- Node 20+ (repo uses Next 15)
- Python 3.9+ and `backend/.venv` (already created)
- Ports **3000** (frontend) and **8000** (API)

## Environment

Do **not** start the canonical API with `backend/.env` as-is. That file’s `DATABASE_URL` points at hosted Supabase. Wave 6 overrides it.

Frontend already defaults to `NEXT_PUBLIC_API_URL=http://localhost:8000` (see `frontend/.env.development`).

Canonical app does not use `NEXT_PUBLIC_SUPABASE_*` (legacy Careers only).

## Database

Isolated SQLite file: `backend/asktrabaajo_wave6.db`

```bash
# from repo root
backend/.venv/bin/python scripts/wave6_local_bootstrap.py
```

Creates schema (`create_all`), role catalog, governance teams, and DEV users. Deletes and recreates the file if it already exists.

**Reset:** run the bootstrap again.

## Backend

```bash
# from repo root
./scripts/wave6_start_backend.sh
```

Or:

```bash
cd backend
export ENVIRONMENT=development
export DATABASE_URL="sqlite:///$PWD/asktrabaajo_wave6.db"
export SECRET_KEY="wave6-local-dev-only-not-for-hosted"
export AI_PROVIDER=none
export PAYMENT_PROVIDER=mock
export CORS_ORIGINS="http://localhost:3000,http://localhost:3001"
.venv/bin/python -m uvicorn app.main:app --reload --port 8000 --host 127.0.0.1
```

Use `python -m uvicorn` (the venv `uvicorn` script may have a stale shebang).

Health: http://127.0.0.1:8000/health  
Docs: http://127.0.0.1:8000/api/docs

## Frontend

```bash
cd frontend
npm run dev -- --port 3000
```

Open http://localhost:3000 (prefer `localhost`, not `127.0.0.1`, for CORS).

## DEV accounts (not production)

| Role | Email | Password |
|---|---|---|
| Candidate | `dev+wave6.candidate@example.com` | `Wave6-dev-local!` |
| Employer (org_admin of DEV_WAVE6_ORG) | `dev+wave6.employer@example.com` | `Wave6-dev-local!` |
| Super Admin (platform) | `dev+wave6.admin@example.com` | `Wave6-dev-local!` |

Clearly DEV-prefixed. Empty Work ID / jobs / finance — honest empty states.

## Portals to open

1. http://localhost:3000/login · /register  
2. Candidate: /jobseeker · /id/work-id · Career · Opportunities · Athena  
3. Employer: /company · /company/jobs · /company/candidates · /company/athena  
4. Super Admin: /admin · /admin/governance · /admin/finance  
5. Government: **not implemented**

## Production build (optional)

Do not run `npm run build` against the same `.next` folder as a running `next dev`. Use an isolated output:

```bash
cd frontend
NEXT_DIST_DIR=.next-wave6-build npm run build
```

## Screenshots

```bash
# after npm install playwright in wave6-qa/ (gitignored)
node scripts/wave6_capture.mjs
```

Writes PNGs to `wave6-qa/localhost/` (gitignored).

## Reset development state

```bash
# from repo root — deletes and recreates the isolated SQLite file + DEV users
backend/.venv/bin/python scripts/wave6_local_bootstrap.py
```

Does not touch hosted Supabase.

## Known limitations

- `AI_PROVIDER=none` — Athena is degraded, not simulated  
- `PAYMENT_PROVIDER=mock` — no live processor  
- Hosted DB unused  
- Favicon conflict warning in Next.js (`/favicon.ico`) — does not block portals  
- Next.js dev “N” overlay may appear on screenshots  
- No Government portal  
- Figma People/Companies directories have no APIs
