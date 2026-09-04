# CURSOR WAVE 7 CLOSURE — Public website + local multi-portal demo

**Status:** IMPLEMENTED (local, unpushed)  
**Wave 8:** not started  
**Hosted database:** **UNTOUCHED**  
**Pixel-perfect:** **not claimed**

## 1. Website repository inspected

https://github.com/TheDotProtocol/trabaajowebsite cloned to a **sibling** directory. CRA + Craco + Yarn, WebGL globe, Lenis, gold-on-ink. Not merged into this Next.js app.

## 2. Website running locally

**IMPLEMENTED + VISUALLY VERIFIED.** http://localhost:3001 returned 200. Playwright captured the landing page.

## 3. Canonical application running

**IMPLEMENTED + VISUALLY VERIFIED.** http://localhost:3000 and API http://127.0.0.1:8000. Isolated SQLite `backend/asktrabaajo_wave6.db`.

## 4. CTA integration

**IMPLEMENTED + VISUALLY VERIFIED.** Nav Login opened canonical `/login`. Destinations from `REACT_APP_CANONICAL_APP_URL` (local: `http://localhost:3000`). Buttons were not rebuilt.

## 5. Login integration

**IMPLEMENTED + FUNCTIONALLY VERIFIED + VISUALLY VERIFIED.** Website Login → canonical AuthSplit → DEV account → `/portals`. No website auth. No Supabase Auth.

## 6. DEV account

**IMPLEMENTED.** Email `akumartrabaajo@gamail.com` (exact spelling). Password only in gitignored `backend/.wave7-dev-account`. Not on hosted Supabase. Not super_admin.

## 7. Jobseeker

**IMPLEMENTED + VISUALLY VERIFIED.** Dashboard and Work ID opened with labelled DEV fixture data. Other Candidate routes remain as Wave 6.

## 8. Employer

**IMPLEMENTED + VISUALLY VERIFIED.** Command center opened for **AskTrabaajo DEV Company**. One DEV job published. No fabricated pipeline/offers.

## 9. Government

**BACKEND-LIMITED + VISUALLY VERIFIED foundation.** `/government` is an honesty page: membership, catalog roles, no aggregate APIs, no citizen data. Figma government product was **not** built.

## 10. Browser QA

**AVAILABLE.** Playwright Chromium (`scripts/wave7_capture.mjs`): website → login → portals → jobseeker → Work ID → employer → government. PASS.

## 11. Visual transition QA

Public site stays immersive/WebGL. Application stays operational OS (black/gold/240px). Portal picker uses the same language. Not flattened into each other.

## 12. Security / RBAC

Wave 7 E2E: stacked memberships, no god-mode, jobseeker + employer 200, cross-tenant 403, governance dashboard 403, unauthenticated 401. Frontend picker is links only.

## 13. Tests

| Suite | Result |
|---|---|
| `tsc --noEmit` | PASS |
| lint | PASS (5 pre-existing Careers warnings) |
| isolated production build | PASS (69 routes including `/portals`, `/government`) |
| Wave 2–5 E2E | PASS |
| Wave 7 multi-portal E2E | PASS |
| Playwright capture | PASS |
| Hosted DB | UNTOUCHED |

Phase 3 pytest was last fully run in Wave 6 (PASS). Wave 7 added no backend route surface.

## 14. Git commits

AskTrabaajo (`main`, local, **not pushed**):

| SHA | Message |
|---|---|
| `49e07e0` | wave7: local multi-portal dev identity |
| `3c46707` | wave7: portal integration |
| `2d638fc` | wave7: documentation |

Public website sibling repo (`557134f`): wave7: connect public website CTAs. **Not pushed.**

## 15. Current HEAD

`2d638fc` on asktrabaajo `main` (local, unpushed).

## 16. Working tree

Wave 7 files committed. Pre-existing Careers / legacy dirt left unstaged.

**Deliberately untouched:** hosted Supabase, `backend/.env`, Legacy Careers, website visual/WebGL/copy, canonical API contracts, production RBAC rules.

## 17. Known limitations

- Government intelligence APIs do not exist
- Website production still requires `REACT_APP_CANONICAL_APP_URL`
- Canonical Next `/` marketing page was not replaced (front door is :3001)
- No pipeline/interview/offer fixtures (empty states already render)
- DEV password is local-only

## 18. Exact localhost instructions

See `CURSOR_WAVE_7_LOCALHOST_GUIDE.md`.

```bash
backend/.venv/bin/python scripts/wave7_local_bootstrap.py
./scripts/wave6_start_backend.sh
cd frontend && npm run dev -- --port 3000
./scripts/wave7_start_website.sh
```

Open http://localhost:3001 → Login → `akumartrabaajo@gamail.com`.
