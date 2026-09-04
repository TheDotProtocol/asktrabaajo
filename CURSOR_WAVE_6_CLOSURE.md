# CURSOR WAVE 6 CLOSURE — Localhost portal QA + Figma visual validation

**Status:** IMPLEMENTED (local, unpushed)  
**Depends on:** Wave 5 closed  
**Wave 7:** not started  
**Hosted database:** **UNTOUCHED**  
**Pixel-perfect:** **not claimed**

## 1. Executive summary

AskTrabaajo now runs as one local product: Candidate OS + Work ID + Employer OS + Athena (degraded) + Super Admin, with auth that matches the Figma split-screen language. Figma megamenus without APIs were not fabricated. Government remains design-only.

## 2. Localhost setup result

- Isolated SQLite `backend/asktrabaajo_wave6.db` via `scripts/wave6_local_bootstrap.py`
- API http://127.0.0.1:8000 with `DATABASE_URL` override (hosted `.env` URL **not** used)
- Frontend http://localhost:3000
- DEV login verified against the local API
- Guide: `CURSOR_WAVE_6_LOCALHOST_GUIDE.md`

## 3. Portals successfully opened

Login, Register, Forgot password, Candidate OS (all implemented jobseeker routes), Work ID, Employer OS (implemented company/employer routes), Candidate Athena, Employer Athena, Super Admin command/governance/finance/ops.

## 4. Routes inspected

See `CURSOR_WAVE_6_PORTAL_MAP.md`. Missing aliases: `/jobseeker/dashboard`, `/jobseeker/advisor`, `/company/jobs/[id]`, `/company/outreach`, `/government`.

## 5. Figma screens mapped

See `CURSOR_WAVE_6_FIGMA_MAPPING.md`. Four Figma files read via MCP. Athena has no Figma.

## 6. Pixel/visual discrepancies found

P0: none on running routes.  
P1: Auth sat under marketing Header/Footer and used a light card — **fixed**. Employer Figma topbar+search and Admin megamenu remain PARTIAL / BACKEND-LIMITED.  
P2: Candidate career-map art, combined settings, Planning=profile label.  
P3: Next favicon conflict; Next.js dev overlay on screenshots.

## 7. Fixes made

- `AuthSplit` login / register / forgot-password (Figma two-column)
- Auth routes excluded from `ConditionalChrome`
- Local bootstrap + start script + Playwright capture
- Register role grid reduced to jobseeker/employer intent (government not self-selected)

## 8. Responsive fixes

Auth and Candidate home/Athena captured at 390×844. Sidebar collapses to a drawer. No dedicated tablet/laptop screenshot pass.

## 9. Functional QA

Playwright: DEV candidate → Candidate routes; employer → Company routes; admin → Admin routes. Canonical tokens only. Invalid login remains on `/login`.

## 10. Athena QA

`AI_PROVIDER=none`: “not configured”, no composer, no fabricated reply, OS capability cards remain. **VISUALLY VERIFIED** on Candidate; Employer/Admin Athena opened.

## 11. Super Admin QA

Command center honest zeros, finance empty, Athena Soon, support honesty. Megamenu not built.

## 12. Government status

Figma exists. No route. Aggregate-only backend. Documented, not fabricated.

## 13. Browser automation

**Available.** Playwright Chromium (`scripts/wave6_capture.mjs`).

## 14. Screenshot comparison

Figma MCP screenshots + localhost PNGs under `wave6-qa/localhost/` (gitignored). Compared by inspection. **No overlay/diff tool.**

## 15. Known limitations

Empty DEV data; Athena degraded; no Government; no platform directories; hosted DB unused; 1280/1024/768 not screenshot-verified.

## 16. Remaining visual discrepancies

Employer missing Figma top search bar. Admin missing Figma megamenu/top search. Candidate career map illustration. Populated Figma vs empty DEV.

## 17. Backend-limited screens

Listed in the Figma mapping (skills intel, compensation, onboarding, People/Companies, tickets, platform Athena tools, government).

## 18. Test results

| Suite | Result |
|---|---|
| `npx tsc --noEmit` | PASS |
| `npm run lint` | PASS (5 pre-existing careers `useEffect` warnings) |
| `NEXT_DIST_DIR=.next-wave6-build npm run build` | PASS (67 routes; first attempt failed only because `next dev` owned `.next`) |
| `pytest tests_phase3` | PASS (11 skipped, same as prior waves) |
| Wave 2–5 E2E | PASS |
| Playwright portal capture | PASS (localhost, isolated SQLite) |
| Hosted DB | **UNTOUCHED** |

## 19. Git commits

Created on `main` (local, **not pushed**):

| SHA | Message |
|---|---|
| `ed2aba3` | wave6: local portal runtime setup |
| `1fe5a96` | wave6: auth visual corrections |
| (this docs commit + record-head) | wave6: visual qa documentation |

## 20. Current HEAD

See `PROJECT_STATUS.json` `git_head` after the record-head commit. Parent of this documentation set is `1fe5a96`.

## 21. Working tree status

Wave 6 files committed. Pre-existing Careers / legacy / Phase-1 dirt left **unstaged** on purpose.

**Deliberately untouched:** hosted Supabase, `backend/.env`, legacy Careers app, public marketing site (except auth no longer wraps in marketing chrome), canonical API contracts, Wave 1–5 behavior.

## 22. Exact localhost startup

See `CURSOR_WAVE_6_LOCALHOST_GUIDE.md`.

```bash
backend/.venv/bin/python scripts/wave6_local_bootstrap.py
./scripts/wave6_start_backend.sh
# other terminal
cd frontend && npm run dev -- --port 3000
```

Open http://localhost:3000/login  
DEV password: `Wave6-dev-local!`  
Accounts: `dev+wave6.candidate@example.com`, `dev+wave6.employer@example.com`, `dev+wave6.admin@example.com`

## Visual categories

**VISUALLY VERIFIED:** login, register, forgot-password, Candidate home, Work ID, Candidate Athena (desktop+mobile), Employer command center, Admin command center, plus Playwright-opened sibling routes in the same shells.

**IMPLEMENTED BUT NOT VISUALLY VERIFIED:** case/enforcement/appeal **detail** pages with live records; candidate profile with a talent hit; tablet/laptop viewports; populated Figma states.
