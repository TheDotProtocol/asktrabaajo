# CURSOR WAVE 9 — Owner commands

## What Cursor did

- Vendored the approved public website into the canonical Next.js app (`frontend/src/marketing`).
- Made **http://localhost:3001** the unified front door: website + `/login` + `/register` + portals.
- Login/Register stay on the same origin. They no longer send the browser to localhost:3000.
- Granted the **local** DEV inspector a Super Admin membership on **AskTrabaajo DEV Platform** (SQLite only).
- Production RBAC catalog was not weakened.
- Hosted Supabase was not touched. No `supabase db push`. No `supabase db reset`.
- Secret-scanned tracked files: no DEV password, no API keys, no JWT blobs.
- Prepared this repo to be the production GitHub repository.

## What the owner must do manually

### Local start

Backend (keep port 8000, isolated sqlite — do **not** start uvicorn with hosted `DATABASE_URL` from `backend/.env`):

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

To use the already-configured local OpenAI key without committing it:

```bash
# same as above, but AI_PROVIDER=openai
# OPENAI_API_KEY is read from backend/.env (gitignored)
```

One-time local Super Admin grant (already run in Wave 9; safe to repeat):

```bash
backend/.venv/bin/python scripts/wave9_local_admin.py
```

Frontend (unified app):

```bash
cd frontend
npm run dev
```

Opens **http://localhost:3001**

Health: http://127.0.0.1:8000/health

DEV login: `akumartrabaajo@gmail.com`  
Password: gitignored `backend/.wave7-dev-account` only. Do not put it in Vercel or Git.

Do **not** start the sibling `trabaajowebsite` CRA app on 3001 anymore. That repo is a visual reference only.

### Vercel

**YES — add environment variables, then redeploy.**

Frontend project Root Directory must be `frontend`.

Add at least:

- `NEXT_PUBLIC_API_URL` = the public canonical API origin  
  Production / Preview / Development as appropriate  
  VALUE REQUIRED FROM OWNER

On the **API host** (not as `NEXT_PUBLIC_*`):

- `SECRET_KEY` VALUE REQUIRED FROM OWNER
- `DATABASE_URL` (existing hosted URL — do not create a new database)
- `CORS_ORIGINS` including the Vercel/production origin
- `AI_PROVIDER` + `OPENAI_API_KEY` if Athena should be live
- SMTP_* if transactional email should send
- Leave `PAYMENT_PROVIDER=mock` until the owner explicitly enables live Stripe

### Supabase

**DO I HAVE TO RUN A SUPABASE PUSH?**  
**NO.**

Waves 6–8 added no Alembic revisions. Head remains `0014_commerce_billing_payments`.  
Backup/PITR is **not verified** — do not push or reset.

### GitHub

Cursor pushes `main` to `https://github.com/TheDotProtocol/asktrabaajo` when this wave’s validation is complete.

The sibling repo `TheDotProtocol/trabaajowebsite` remains a **reference** of the original CRA website. It is not the production deployment source.

## What does not need to be done

- Do not create a second production GitHub repository.
- Do not create a competing Vercel project for the marketing site.
- Do not `supabase db reset`.
- Do not `supabase db push` for Wave 9.
- Do not enable live Stripe merely because a key might exist later.
- Do not put the DEV password in Vercel, Git, or client bundles.
- Do not start Wave 10 unless a new wave is authorized.
