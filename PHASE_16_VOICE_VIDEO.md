# Phase 16 — Voice & Video

Phase 16 ships the **architecture** for voice/video, not a production vendor
integration. The interview engine is text-first and fully functional today;
voice/video are opt-in, configuration-driven, and disabled by default.

## Provider-neutral media abstraction (`app/services/media.py`)

- `MediaProfile` — session media configuration (voice enabled, video enabled,
  STT/TTS provider names, language, device constraints). Never contains
  credentials.
- `SpeechToText` / `TextToSpeech` — capability interfaces. Provider adapters
  are future work; with no provider configured (`ai_stt_provider=none`,
  `ai_tts_provider=none`, the safe defaults), calls fail with
  `ai.media_unavailable` (503). The engine **never fabricates** a transcript
  or audio.
- `MockMedia` — deterministic test double, restricted to the test suite, used
  to exercise failure/fallback paths.

## Configuration

```
AI_STT_PROVIDER=none     # openai / deepgram adapters land behind this switch
AI_TTS_PROVIDER=none     # openai / elevenlabs adapters land behind this switch
```

Voice is only enabled for a session when the employer opts in AND a real
provider is configured. `build_media_profile` reflects that honestly in the
session's `media_profile`.

## Media pipeline (designed, documented)

```
Audio input → STT (adapter) → interview engine (text) → TTS (adapter) → audio out
```

Each adapter step must: never log audio or transcripts, respect the session
language, apply strict timeouts, and raise provider-neutral errors
(`ai.stt_failed`, `ai.tts_failed`) that surface as session quality signals —
never as candidate performance penalties.

## Video / WebRTC

No server-side media protocol was invented. The design stance:

- Video transport is a **frontend** concern using the browser's standard
  getUserMedia + WebRTC when the session media profile enables it.
- Required properties (documented, not yet wired): secure signaling,
  session-authenticated peers, ICE, TURN where required, reconnect and
  network-degradation handling, microphone/camera permission flows.
- No internal signaling credentials are ever exposed to the candidate UI.
- Camera participation is never assumed and never mandatory for a
  configured text interview.

## Recording

**Not implemented.** If a future workflow genuinely requires recording, it
must be built as an explicit, consent-governed, retention-bound feature (see
PHASE_16_PRIVACY.md). The engine stores no audio or video today and the
consent snapshot includes explicit recording consent fields that remain
`false` by default.

## Integrity of transport events

Objective transport events (disconnect, reconnect, unexpected termination,
mic/camera state changes, duplicate session) flow through the integrity
signal channel and are labeled **review signals** — they are never treated as
cheating detection and never affect evaluation.

## Honest status

- VOICE: MOCKED / architecture-only (safe-degraded without a configured
  provider).
- VIDEO: MOCKED / architecture-only (backend media profile + frontend
  consent gating; no provider wired).
- No facial emotion analysis, no lie detection, no personality-from-face
  inference — these are explicitly absent from the platform.
