# Phase 18 — Provider Readiness

Per-provider status with evidence. "Production" is never claimed without configured, tested infrastructure.

| Provider | Status | Evidence / notes |
|---|---|---|
| **AI (Athena core)** | `none` (safe degraded) — **NOT CONFIGURED** for production | `AI_PROVIDER` default `none`; provider abstraction exists; deterministic/mocked paths carry the full test suite. Production requires an approved provider + env credential (`OPENAI_API_KEY` etc.) and then a smoke pass. |
| **AI STT / TTS (voice)** | `none` — **NOT CONFIGURED** | Phase 16 media abstraction is provider-neutral; voice disabled by default and media calls fail with `ai.media_unavailable` — never fabricated. No production STT/TTS provider provisioned. |
| **Video / WebRTC** | **NOT CONFIGURED** | Phase 16 documents the governed transport design (signaling, auth, ICE/TURN, reconnect); no provider wired; no server-side recording. Video requirement is optional per interview configuration. |
| **Payments** | `mock` (sandbox) — **NOT PRODUCTION** | `PAYMENT_PROVIDER=mock` default; deterministic sandbox, no real money. `stripe` value exists in the validator but is **not wired** — activating it requires an approved provider integration + secret management + a sandbox→production plan. **No production charge path exists.** |
| **Email / notifications** | **NOT CONFIGURED** | No email provider configured in canonical config. Notifications are in-app records only. No mass-send path. |
| **Storage** | Supabase storage, **3 private buckets** | `kyc-documents`, `kyc-selfies`, `user-documents` all `public=false`. Per-object policies require dashboard verification (launch item). Canonical document access remains authorization-controlled in-app. |
| **Database** | Supabase (session pooler) | Connected + identity verified, read-only. Live writes gated on Backup/PITR. |

## Summary

Everything that can be safely mocked is mocked and tested. Nothing production-grade is claimed for AI, voice, video, payments, or email until its provider is provisioned and verified end-to-end. The canonical platform is **DEVELOPMENT READY**; production requires the launch checklist (`PHASE_18_LAUNCH_CHECKLIST.md`).
