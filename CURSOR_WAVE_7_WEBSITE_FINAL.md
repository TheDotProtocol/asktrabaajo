# CURSOR WAVE 7 — FINAL PUBLIC WEBSITE

The public website in **TheDotProtocol/trabaajowebsite** is the official AskTrabaajo front door.

Wave 8 was not started.

## Website repository

https://github.com/TheDotProtocol/trabaajowebsite

Local sibling clone:

`/Users/mac/Downloads/AR Holdings Dev Projects/trabaajowebsite`

Not merged into this Next.js application.

## Architecture

```
PUBLIC WEBSITE (CRA + Craco, this repo)
        ↓ Login / Register / Enter AskTrabaajo
CANONICAL APPLICATION (Next.js, this AskTrabaajo repo)
        ↓ FastAPI /api/v1
Jobseeker / Employer / Government / Admin
```

No second authentication system. No Supabase Auth on the website. No website-local login.

## Routes

| Path | Page |
|---|---|
| `/` | Immersive flagship home (WebGL globe preserved) |
| `/about` | What AskTrabaajo is; available now vs coming |
| `/jobseekers` | Jobseeker audience |
| `/companies` | Employer / job giver audience |
| `/recruiters` | Recruiter audience (COMING) |
| `/governments` | Government audience (OUR VISION) |
| `/institutions` | Partners / issuers (COMING) |
| `/contact` | Official emails + production-safe form |
| `/privacy` | Informational privacy / security / a11y / AI |
| `/terms` | Informational website terms |
| `*` | 404 (login/register are **not** website pages) |

## Public navigation

About · Jobseekers · Employers · Government · Work ID · Athena · Contact  
plus Login · Register · Enter AskTrabaajo

Footer legal links go to real pages. Careers goes to Contact (no invented jobs board). Social icons are present but not linked — profiles are not published.

## Contact implementation

Official addresses only:

- hello@asktrabaajo.com
- access@asktrabaajo.com
- partners@asktrabaajo.com
- gov@asktrabaajo.com
- press@asktrabaajo.com

No phone. No office. The Next.js `/contact` fake city numbers were **not** copied.

The form does **not** fake delivery.

**REQUIRES PRODUCTION EMAIL/FORM PROVIDER**

Until a provider exists, “Open in email app” (mailto) is the supported send path.

The unused website `backend/` Mongo stub is not a contact backend and must not be deployed.

## Login / Register / application integration

All CTAs resolve from `REACT_APP_CANONICAL_APP_URL` in `frontend/src/config/site.js`.

| CTA | Destination |
|---|---|
| Login | `{CANONICAL}/login` |
| Register | `{CANONICAL}/register` |
| Enter AskTrabaajo | `{CANONICAL}/portals` |
| Create Work ID | `{CANONICAL}/register?intent=jobseeker` |
| Start Hiring | `{CANONICAL}/register?intent=employer` |

## Production content audit

Corrected or left honest:

- Footer Privacy / Terms / Security / Accessibility / Responsible AI → real pages or in-page anchors
- Careers no longer points at the application portals
- Social `#` links removed (coming soon, not invented URLs)
- Jobseeker / Employer marked AVAILABLE NOW with expanding-capability language
- Recruiters COMING · Government OUR VISION · Institutions COMING
- Emergent builder script removed from `index.html`
- Tracked `frontend/.env` / `backend/.env` removed from git (builder preview URL and local Mongo)

Not invented: partners, customers, statistics, awards, offices, employees, testimonials, phone numbers.

## SEO

- Title, description, Open Graph, Twitter, JSON-LD Organization
- Favicon / apple-touch-icon from the approved logo
- `robots.txt`, `sitemap.xml`, `manifest.json`
- Per-page `document.title` via `usePageMeta`
- Canonical / sitemap hostname: `https://www.asktrabaajo.com/` (already present in the original repo)

If that hostname is not attached on Vercel: **PRODUCTION DOMAIN REQUIRED**. Do not invent another domain in code.

## Accessibility

Skip link, semantic headings, focus-visible gold ring, reduced-motion WebGL fallback (`hasWebGL` + `FallbackNetwork`), keyboard-usable nav and footer. No WCAG audit claimed.

## Responsive QA

Playwright viewports: 390×844, 768×1024, 1024×768, 1280×800, 1440×900.

The editorial marquee is intentionally wider than the viewport and is clipped (`overflow-x: hidden` on `html`/`body` and the marquee). Users do not get a page-level horizontal scrollbar.

## Performance

Production CRA build succeeded (mediapipe source-map warning only). WebGL remains lazy + Suspense + fallback. Immersive experience was not removed.

## Vercel configuration

`vercel.json` at repo root:

- Build: `yarn --cwd frontend install && yarn --cwd frontend build`
- Output: `frontend/build`
- Framework: none
- SPA rewrite to `index.html`
- Node 20 (`frontend/.nvmrc`)

## Environment variables

| Variable | Required | Notes |
|---|---|---|
| `REACT_APP_CANONICAL_APP_URL` | **Yes in production** | Canonical app origin, no trailing slash |
| `REACT_APP_PUBLIC_SITE_URL` | Optional | Public site origin once the domain is confirmed |
| `PORT` / `WDS_SOCKET_PORT` | Local only | `3001` so Next can keep `3000` |
| `ENABLE_HEALTH_CHECK` | No | `false` |

Never put the DEV password, API keys, or database URLs on Vercel for this website.

## Git

Website commits (this wave) then **push to `TheDotProtocol/trabaajowebsite`**.

AskTrabaajo application repo: local documentation/QA commits only. **Not pushed.**

## Deployment status

Ready for Vercel to build from `main` **if** `REACT_APP_CANONICAL_APP_URL` is set on the Vercel project.

Blockers that are operations, not code:

1. Confirm Vercel project is this website repo (not the canonical app)
2. Set `REACT_APP_CANONICAL_APP_URL` to the production application origin
3. Attach `www.asktrabaajo.com` if that is the intended domain — **PRODUCTION DOMAIN REQUIRED** until attached
4. Contact form still needs a production email provider
