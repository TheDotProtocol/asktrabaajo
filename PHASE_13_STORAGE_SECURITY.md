# PHASE 13 — STORAGE SECURITY

## Legacy buckets (Supabase Storage)

From `supabase-storage.sql` — three private buckets with `auth.uid()`-keyed
object policies:

| Bucket | Purpose | Legacy policy | Phase 13 status |
|---|---|---|---|
| `user-documents` | candidate documents (resumes, certificates) | owner-only (`auth.uid()::text = foldername[1]`) | **NOT touched, NOT deleted, NOT made public.** Reviewed; owner-only pattern is directionally right but keys on `auth.uid()` and is unaudited |
| `kyc-documents` | KYC/identity documents | owner-upload, admin review via service role | **NOT touched.** Highest sensitivity; service-role review path must be replaced by the canonical governance workflow |
| `kyc-selfies` | facial selfies | owner-upload | **NOT touched.** Product decision from Phase 4: no facial capture in the canonical architecture; bucket is deprecated for new writes, retained for historical preservation |

**Storage buckets in the live project were NOT inspected or modified**
(read-only REST cannot enumerate storage; direct SQL is blocked).

## Canonical storage target

The canonical document architecture (`person_documents`,
`document_access_grants`, `consents`, credential states) is
**provider-neutral** — Phase 12 documented this and Phase 13 keeps it.
Required properties (from the Phase 13 brief, all satisfied by design):

- private storage, no public buckets for sensitive documents ✓ (design)
- document ownership tied to canonical identity ✓ (`person_documents.person_id`)
- versioning where required ✓ (credential/document state model supports it)
- credential status (verified/unverified/pending/expired/revoked) ✓ (`credentials`)
- consent + access grants + expiry + revocation ✓ (`consents`, `document_access_grants`)
- audit ✓ (grant/disclosure events audited)
- controlled download/signed URLs, no raw URLs ✓ (provider-neutral abstraction, not yet wired)
- KYC isolation ✓ (KYC class is governance-gated; no selfie capture)

## If Supabase Storage is retained (decision required)

- Keep buckets **private**; never re-apply the old object policies as-is.
- Object ownership in the path (`{canonical_user_id}/{filename}`) is
  compatible, but authorization must flow from `document_access_grants`,
  not from parsing `auth.uid()`.
- Service-role access: restrict to the governance/verification workflow
  with audit; the canonical app never uses the service-role key.
- Signed URLs must expire; downloads must be audited.
- KYC objects: only the governance workflow (with explicit permission)
  may access; administrators cannot casually browse.

## Status

- Live storage: **NOT touched** (and not inspectable without SQL access).
- Canonical storage layer: provider-neutral abstraction designed
  (Phases 4/12), **NOT wired** — the upload/download endpoints belong to
  the document-storage workstream recommended for the next phase after
  live deployment. Until then the legacy buckets remain the only live
  document store, untouched.