# Wave 3 — Development database classification

**Date:** 2026-09-05  
**Decision:** Isolated canonical sqlite for Wave 3 validation. **Hosted Supabase project was not written to.**

Same policy as Wave 2 (`CURSOR_WAVE_2_DB_CLASSIFICATION.md`).

| Question | Answer |
|---|---|
| Canonical? | Alembic `0001`–`0014`, 80 tables |
| Needed by Wave 3? | Company profile, jobs, applications, interviews, offers, talent, billing — already in canonical schema |
| Offices / departments / job templates as first-class tables? | **Not in canonical schema.** UI uses profile city/country + job.department + clone-job-as-draft |
| Local/scratch sufficient? | **Yes** — `scripts/wave3_employer_e2e.py` |
| Hosted write necessary? | **No** |
| Rebuilt? | **No hosted rebuild.** Isolated sqlite `create_all` + catalog seed only |

DEV fixtures in the e2e script use `dev+…@example.com` and names `DEV_ORG_A` / `DEV_ORG_B`.
