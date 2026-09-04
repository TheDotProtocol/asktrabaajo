# CURSOR WAVE 5 READINESS

**Status:** CLOSED — implemented. See `CURSOR_WAVE_5_CLOSURE.md` and `CURSOR_ADMIN_DESIGN_DECISIONS.md`.  
**Depends on:** Wave 4 closed (including the Athena refinement pass).

Wave 5 is the Super Admin / Platform Operations Figma implementation. Wave 6 is **not** started.

## Rules that remain

- Do not replace Waves 1–5.
- Do not invent Athena tools or confirmation shortcuts.
- `AI_PROVIDER=none` and `PAYMENT_PROVIDER=mock` stay honest.
- Hosted DB: isolated sqlite / scratch Postgres unless a hosted write is documented first.
- Do not merge the public website repo.
- Do not touch legacy Careers.
- Do not start Wave 6 without a separate approval prompt (`CURSOR_WAVE_6_READINESS.md`).
