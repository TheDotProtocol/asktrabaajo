# CURSOR WAVE 7 — DEV ACCOUNT

Local visual QA only. **Not** created on hosted Supabase.

## Email

`akumartrabaajo@gamail.com`

Spelling is intentional (`gamail.com`). Do not “correct” it.

## Password

Not stored in this file.

Read `backend/.wave7-dev-account` (gitignored) or set `WAVE7_DEV_PASSWORD` before bootstrap.

## How to authenticate locally

1. Bootstrap and start the isolated API (`scripts/wave7_local_bootstrap.py`, `scripts/wave6_start_backend.sh`).
2. Start the canonical app on port 3000.
3. Open http://localhost:3000/login **or** click Login on http://localhost:3001.
4. Use the email above and the password from the gitignored file.

## Available portals (same login)

| Portal | How | Backend basis |
|---|---|---|
| Jobseeker | `/jobseeker` | Person / Work ID on the user |
| Employer | `/company` | `org_admin` of **AskTrabaajo DEV Company** |
| Government | `/government` | `government_user` of **AskTrabaajo DEV Government** |

Not Super Admin. No `admin.manage`. No god-mode permission.

After login with multiple portal types, the app opens `/portals`. Switching is a link. Every API call is still authorized by the backend.

## DEV organization

- **AskTrabaajo DEV Company** (`employer`, slug `asktrabaajo-dev-company`)
- **AskTrabaajo DEV Government** (`government`, slug `asktrabaajo-dev-government`)

Wave 6 isolated users remain (`dev+wave6.*@example.com`).

## DEV fixtures

Minimum, labelled DEV:

- Work ID headline/summary/city, 3 skills, 1 experience, 1 education, 1 unverified credential, 1 career goal
- One published job: **DEV Inspector Role**

No fake labour-market statistics. No citizen records. No fabricated interviews/offers.

## Reset

```bash
backend/.venv/bin/python scripts/wave7_local_bootstrap.py
```

Deletes and recreates `backend/asktrabaajo_wave6.db`. Hosted database untouched.
