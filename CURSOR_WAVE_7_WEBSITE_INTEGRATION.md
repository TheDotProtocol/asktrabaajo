# CURSOR WAVE 7 — PUBLIC WEBSITE INTEGRATION

The public website remains a **separate repository**. It is not merged into this Next.js app.

## Repository

https://github.com/TheDotProtocol/trabaajowebsite

Local clone (sibling of this repo):

`/Users/mac/Downloads/AR Holdings Dev Projects/trabaajowebsite`

## Architecture

- Framework: Create React App + Craco + React 19 + React Router 7
- Package manager: Yarn 1.22
- Visual: Outfit / Inter / JetBrains Mono, gold-on-ink, WebGL globe (`@react-three/fiber`), Lenis, Framer Motion
- Routes: `/` flagship home; `/jobseekers` `/companies` `/recruiters` `/governments` `/institutions` audience pages
- `/app` `/login` `/register` were **reserved placeholders** inside the SPA

## Ports

| Surface | Port | URL |
|---|---|---|
| Public website | 3001 | http://localhost:3001 |
| Canonical application | 3000 | http://localhost:3000 |
| Canonical API | 8000 | http://127.0.0.1:8000 |

CRA defaults to 3000, so local development forces `PORT=3001`.

## CTA mappings

All destinations come from `frontend/src/config/site.js` and `REACT_APP_CANONICAL_APP_URL`.

| Website CTA | Destination |
|---|---|
| Login | `{CANONICAL}/login` |
| Register | `{CANONICAL}/register` |
| Enter AskTrabaajo | `{CANONICAL}/portals` |
| Create Work ID | `{CANONICAL}/register?intent=jobseeker` |
| Start Hiring | `{CANONICAL}/register?intent=employer` |
| Government enquiry | mailto (unchanged) |

If `REACT_APP_CANONICAL_APP_URL` is empty, paths stay relative (production must set the origin).

## Environment variables

Website (`.env.example` / `.env.local`, not hardcoded in production source):

- `PORT`
- `WDS_SOCKET_PORT`
- `REACT_APP_CANONICAL_APP_URL`
- `ENABLE_HEALTH_CHECK`

Canonical app:

- `NEXT_PUBLIC_API_URL` (already `http://localhost:8000` in `.env.development`)

API:

- `CORS_ORIGINS` includes `http://localhost:3000,http://localhost:3001`

## Integration decisions

- Do not merge the marketing SPA into Next.js.
- Do not add authentication to the website.
- Do not rebuild buttons or WebGL. Destinations only.
- Login/Register links were added to the existing nav using the same type styles.
- Canonical `/` marketing page inside Next.js is unchanged. The **front door for Wave 7 is localhost:3001**.

## Changed

- Website `site.js` (env-based canonical URLs)
- Website Nav Login/Register links
- Website `.env.example`, `.gitignore` for `.env*.local`
- Canonical `/portals` picker
- Canonical `/government` honesty foundation page
- Portal switch links in Candidate / Employer / Admin shells
- Local multi-portal DEV identity (isolated SQLite)

## Deliberately not changed

- Website visual design, WebGL, animations, copy
- Hosted Supabase
- Legacy Careers
- Canonical API contracts
- Production RBAC rules
- Government intelligence APIs (none exist)
