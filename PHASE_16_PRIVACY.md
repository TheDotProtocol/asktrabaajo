# Phase 16 — Privacy

Interview data is sensitive. Phase 16 follows the platform privacy model:
data minimization, purpose limitation, least privilege, consent,
auditability, retention control and user control.

## Ownership & access

| Data | Owned by | Visible to |
|---|---|---|
| Session metadata (state, config, consent snapshot) | Organization + candidate | Org members with interviews.* ; the candidate via entry token |
| Question plan | Organization (employer-authored config) | The candidate during the flow; org members after |
| Evaluations (dimensions only) | Organization | Org members with interviews.read |
| Report | Organization | Org members with interviews.read (full); the candidate via feedback endpoint (strengths/preparation areas only) |
| Integrity signals | Session | Org report (labeled review signals); never the candidate's penalty |

## What is never collected or stored

- **Raw answers / transcripts** — no storage path exists. Evaluations store
  dimension scores, strengths/improvements and objective evidence markers.
- **Audio / video** — no recording capability exists.
- Government IDs, passports, tax IDs, KYC state/documents, contact details,
  private messages, document contents — never fetched by the engine.
- Provider credentials — never stored; server-side configuration only.

## Candidate controls

- Explicit consent before start (per capability: mic, camera, recording).
- Consent can be withdrawn at any time — withdrawal stops the session and
  marks it cancelled.
- Question repeats never penalize.
- The candidate can pause/resume and finish early.
- The candidate's feedback view never contains employer deliberations,
  internal notes or the employer's decision.

## Employer privacy

- Employer A can never see employer B's sessions, candidates or reports.
- Candidates never see another candidate's session or data.
- The employer report marks its content "AI-assisted assessment. Human
  review required."

## Audit

Audit rows carry session/tool metadata and action codes only. They never
contain answer content, prompt bodies, audio, or video (asserted by test).

## Integrity signals are not surveillance

Signals are objective session events reported by the client. There is no
server-side monitoring of candidate behaviour, no facial analysis, no eye
tracking, no emotion reading. Signals are labeled review signals for humans,
never automated judgment.
