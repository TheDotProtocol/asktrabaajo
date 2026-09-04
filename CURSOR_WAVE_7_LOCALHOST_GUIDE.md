# CURSOR WAVE 7 — LOCALHOST GUIDE

Three processes. Three ports. One product.

## 1. Start the backend

```bash
# from the asktrabaajo repo
backend/.venv/bin/python scripts/wave7_local_bootstrap.py
./scripts/wave6_start_backend.sh
```

API: http://127.0.0.1:8000/health

Requires `backend/.wave7-dev-account` (gitignored) or `WAVE7_DEV_PASSWORD`.

## 2. Start the canonical application

```bash
cd frontend
npm run dev -- --port 3000
```

App: http://localhost:3000

## 3. Start the public website

The website is a **separate repo** cloned next to this one:

`../trabaajowebsite`

```bash
./scripts/wave7_start_website.sh
```

Website: http://localhost:3001

## 4. Open the public website

http://localhost:3001

This is the landing page. Explore it. Do not start at the application dashboard.

## 5. Click Login

Nav **Login** opens the canonical app at http://localhost:3000/login

## 6. Sign in with the local DEV account

Email: `akumartrabaajo@gamail.com`

Password: see `backend/.wave7-dev-account` (not committed).

## 7. Choose a portal

After login you land on http://localhost:3000/portals

- Jobseeker
- Employer
- Government (foundation / honesty page)

Each link still goes through canonical RBAC.

## 8. Inspect the product

Jobseeker → Work ID → Employer → Government.

**Reset:** run `scripts/wave7_local_bootstrap.py` again. Hosted Supabase is never used.
