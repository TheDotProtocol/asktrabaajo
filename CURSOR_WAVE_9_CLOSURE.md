# CURSOR WAVE 9 CLOSURE — Unified product + production preparation

**Wave 10:** not started  
**Hosted database:** **UNTOUCHED**  
**Supabase push:** **NO**

## Exact local URLs

| Surface | URL |
|---|---|
| Public website | http://localhost:3001 |
| Login | http://localhost:3001/login |
| Register | http://localhost:3001/register |
| Portals | http://localhost:3001/portals |
| Jobseeker | http://localhost:3001/jobseeker |
| Work ID | http://localhost:3001/id/work-id |
| Employer | http://localhost:3001/company |
| Government | http://localhost:3001/government |
| Government Athena | http://localhost:3001/government/athena |
| Jobseeker Athena | http://localhost:3001/jobseeker/athena |
| Employer Athena | http://localhost:3001/company/athena |
| **Super Admin** | **http://localhost:3001/admin** |
| Governance | http://localhost:3001/admin/governance |
| Enforcement | http://localhost:3001/admin/governance/enforcement |
| Appeals | http://localhost:3001/admin/governance/appeals |
| Finance | http://localhost:3001/admin/finance |
| API | http://127.0.0.1:8000 |

## Architecture chosen

The public website is **real Next.js application code** in `frontend/src/marketing`, not an iframe and not a second React app on another port.

```
localhost:3001  →  public website
        →  /login /register
        →  canonical portals (Jobseeker / Employer / Government / Super Admin)
127.0.0.1:8000  →  FastAPI
```

`TheDotProtocol/trabaajowebsite` is the visual source/reference. Production source is `TheDotProtocol/asktrabaajo`.

## Reports

- **Vercel variables:** YES — see `CURSOR_WAVE_9_VERCEL_ENV_AUDIT.md`. Redeploy after adding them.
- **Supabase push:** **NO**
- **GitHub:** `TheDotProtocol/asktrabaajo` `main`  
  Wave 9 product SHA: `7907e97`  
  Follow-up: Next.js `15.5.24` security patch (Vercel blocked `15.5.4` after a successful compile)  
  Previous remote tip before Wave 9: `88a4a97`

## Verification

- Playwright: website → login → jobseeker / employer / government / Super Admin. No localhost:3000 redirects.
- Desktop 1440×900 and mobile 390×844. Other listed viewports were not re-captured this wave.
- `tsc` PASS. Lint 0 errors (font + pre-existing Careers warnings). Isolated `next build` PASS.
- Government + auth pytest PASS. RLS 11 skipped without `TEST_PG_URL`.
- DEV password not in git.

## Provider matrix

See `CURSOR_WAVE_9_PRODUCTION_READINESS.md`. AI/email/payments/voice are **not** silently switched to live.

## STOP

Wave 9 ends here. No live database migration. No invented domain. No fake “message sent”.
