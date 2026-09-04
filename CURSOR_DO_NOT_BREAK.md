# 🚫 CURSOR — DO NOT BREAK

**READ THIS FIRST.** AskTrabaajo is a security-hardened, multi-phase platform. The backend, database, RBAC, AI controls, and commerce controls are complete and tested. Your job is **frontend/UI integration only** — connect the UI to the existing canonical backend. Do not redesign or bypass what exists.

## ABSOLUTE RULES

1. **DO NOT create a second authentication system.** The canonical auth lives in `backend/app/api/v1/auth.py` + `frontend/src/lib/api/session.ts`. Consume it. The frontend already has `ApiClient` in `frontend/src/lib/api/client.ts`.
2. **DO NOT create a second database architecture.** All canonical data lives behind `/api/v1`. Never hit the database directly from the frontend, never call Supabase REST for canonical data.
3. **DO NOT recreate Work ID.** Work ID is the identity spine, served by `/api/v1/work-id/*` and `/api/v1/jobseeker/*`. Candidate-controlled ownership, visibility, and consent apply — preserve them.
4. **DO NOT bypass RBAC or ownership checks.** Every call uses the caller's token; the backend enforces permissions and tenant isolation. The UI must surface permission denials, never work around them.
5. **DO NOT expose private documents.** Documents and disclosures go through `/api/v1/documents/*` and document requests — never render protected content without the user's authorized grant.
6. **DO NOT expose government individual/citizen data.** Government surfaces expose aggregates only. No citizen lookup, no individual records.
7. **DO NOT bypass Athena's confirmation gates.** High-risk Athena actions require explicit, exact-scope confirmation (`POST /api/v1/athena/confirm`). The UI must show confirmations and never auto-confirm.
8. **DO NOT implement autonomous hiring decisions.** AI interviews produce reports; a human records the decision (`/ai-interviews/{id}/decision`). No auto-advance/reject.
9. **DO NOT reintroduce facial emotion detection, lie detection, or protected-characteristic inference.** These are forbidden features — they do not exist anywhere in the canonical platform.
10. **DO NOT migrate, rewrite, or "modernize" the legacy Careers platform** (`api/`, `frontend/src/app/careers/*`, `frontend/src/lib/careers/*`). Legacy is preserved as-is; careers reads use the legacy Supabase client.
11. **DO NOT modify canonical Alembic migrations (0001–0014)** to make frontend integration easier. Schema changes require a new migration + full justification.
12. **DO NOT hardcode or expose secrets.** `backend/.env` is gitignored and untracked — never commit it, never copy values into frontend code, never add secrets to the bundle. `NEXT_PUBLIC_*` is public — only non-secret config belongs there.
13. **DO NOT invent API endpoints.** Use the documented 246 canonical routes (`/api/v1`). If an existing endpoint solves the need, use it. New backend endpoints are out of scope for UI integration.
14. **DO NOT mark mocked functionality as production functionality.** `PAYMENT_PROVIDER=mock`, `AI_PROVIDER=none`, STT/TTS `none` are safe defaults, not production integrations. No real money, no fake AI claims.
15. **DO NOT touch the 63 carried Phase-1 working-tree entries** (legacy/Careers/modified legacy files listed in `git status`). Leave them unstaged and unmodified.
16. **DO NOT push** without explicit authorization from the owner.
17. **DO NOT start "Phase 20"** or add new product features. This is UI integration of what exists.

## The ground truth

- **Canonical backend:** `backend/app/` — FastAPI modular monolith, `/api/v1`, 246 routes, 80 tables, RLS, RBAC.
- **Canonical DB:** PostgreSQL/Supabase (project `zrvrjqwboylvvzusorry`), migrations 0001–0014.
- **Legacy backend:** `backend/main.py` + `api/` — 107 routes, preserved, careers-era.
- **Frontend canonical client:** `frontend/src/lib/api/{client,session,types}.ts` — already used by ~28 pages.
- **Frontend legacy auth:** `frontend/src/hooks/useAuth.ts` (Supabase + local) — used by login/register/older surfaces; bridge to canonical in Wave 1.
- **Docs:** `CURSOR_HANDOFF.md` (primary), `CURSOR_UI_INTEGRATION_PLAN.md` (waves), `API_CONTRACT.md` (routes), `FRONTEND_GAP_REPORT.md` (gaps), `PHASE_19_REPORT.md`.

**If a UI decision would weaken any of the above, stop and ask the owner instead of proceeding.**