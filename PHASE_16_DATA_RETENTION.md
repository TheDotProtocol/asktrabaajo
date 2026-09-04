# Phase 16 — Data Retention

## Policy (by data class)

| Data | Retention behavior |
|---|---|
| Session metadata (state, config, consent snapshot, entry-token hash) | Lazy expiry via `expires_at` (7-day invite window; pre-start sessions transition to `expired` deterministically). Employer can cancel; terminal states are retained while the hiring context is live |
| Question plan | Lives for the session; dropped with the session (cascade). Unanswered areas are copied into the report at completion |
| Evaluations | No raw answers by construction; dimension rows live for the session and are aggregated into the report |
| Report | Retained for the employer review and human decision; this is the durable artifact of the interview |
| Integrity signals | Bounded (50/session) objective events; aggregated into the report at completion |
| Raw answers / transcripts | **Not stored by default — by design.** No transcript storage exists. If an employer workflow genuinely requires a transcript, it becomes a separate, explicitly governed feature with consent, retention, access control, audit and deletion (see below) |
| Audio / video | Not stored — no recording capability exists |
| Audit entries | Append-only platform audit; metadata only |

## Correctness does not depend on a purge job

Pre-start sessions hard-expire lazily on any touch (`expires_at`). Live
sessions end deterministically on the time budget. This mirrors Athena
sessions and prep sessions: a scheduler improves operational cleanup but is
not required for correctness.

## Documented future retention job

When the platform worker architecture is ready, add a periodic purge that:

1. hard-deletes `ai_interview_*` rows for sessions terminal
   (`expired`/`cancelled`/`failed`/`completed`) older than a configurable
   window (e.g. 90 days), and
2. optionally archives report rows (the durable employer artifact) separately
   from the question/evaluation detail rows.

Nothing in this phase pretends such a job exists; the settings and table
structure are chosen so the job is a straightforward addition.

## Governing a future transcript/recording feature

If a transcript (or recording) feature is ever approved, it must ship with
all of: explicit candidate consent (separate from interview consent), a
bounded retention window with hard deletion, org-scoped access controls that
mirror the report permissions, an audit trail for every access, candidate
rights to request deletion, and a "no default retention" posture. None of
that exists in Phase 16, and the privacy-sensitive paths are closed by design
rather than by policy alone.
