# CURSOR WAVE 7 — LOCALHOST GUIDE

Three processes. Three ports. The public website is the front door.

## Ports

| Surface | URL |
|---|---|
| Backend | http://127.0.0.1:8000 |
| Canonical application | http://localhost:3000 |
| Public website | http://localhost:3001 |

## DEV account

Email: `akumartrabaajo@gmail.com`

Password: not in this file. Read `backend/.wave7-dev-account` (gitignored) or set `WAVE7_DEV_PASSWORD`.

Local / DEV database only. Not created on hosted Supabase.

## 1. Start the backend

```bash
# from the asktrabaajo repo
backend/.venv/bin/python scripts/wave7_local_bootstrap.py
./scripts/wave6_start_backend.sh
```

If the shebang on `uvicorn` is stale, start with:

```bash
cd backend
ENVIRONMENT=development \
DATABASE_URL="sqlite:///$PWD/asktrabaajo_wave6.db" \
SECRET_KEY="wave6-local-dev-only-not-for-hosted" \
AI_PROVIDER=none \
PAYMENT_PROVIDER=mock \
CORS_ORIGINS="http://localhost:3000,http://localhost:3001" \
.venv/bin/python -m uvicorn app.main:app --reload --port 8000 --host 127.0.0.1
```

Health: http://127.0.0.1:8000/health

After recreating the sqlite file, restart uvicorn so it opens the new file.

## 2. Start the canonical application

```bash
cd frontend
npm run dev -- --port 3000
```

App: http://localhost:3000

## 3. Start the public website

The website is a **separate repo** cloned next to this one: `../trabaajowebsite`

```bash
./scripts/wave7_start_website.sh
```

Website: http://localhost:3001

## 4. Open the public website

http://localhost:3001

Browse Home, About, Jobseekers, Employers, Government, Contact. This is the landing page. Do not start at the application dashboard.

## 5. Click Login

Nav **Login** opens the canonical app at http://localhost:3000/login

Register opens http://localhost:3000/register

## 6. Sign in

Use `akumartrabaajo@gmail.com` and the password from the gitignored file.

## 7. Inspect Jobseeker

After login you land on http://localhost:3000/portals. Open Jobseeker.

Useful routes: `/jobseeker`, `/id/work-id`, `/jobseeker/career`, `/jobseeker/opportunities`, `/jobseeker/applications`, `/jobseeker/athena`

## 8. Inspect Employer

Same login. Open Employer / Job Giver.

Useful routes: `/company`, `/company/jobs`, `/company/candidates`, `/company/pipeline`, `/company/interviews`, `/company/athena`

Billing is reached from company settings (`/company/settings` → `/employer/billing`). Mock provider — no real charges.

## 9. Inspect Government

`/government` is the honesty / foundation page. Aggregate intelligence APIs do not exist. No citizen records.

## 10. Logout and return

Sign out of the application, then open http://localhost:3001 again.

**Reset the local DEV database:** `backend/.venv/bin/python scripts/wave7_local_bootstrap.py`  
Hosted Supabase is never used.
