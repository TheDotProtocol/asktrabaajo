"use client";
/**
 * Candidate profile — progressive disclosure in action.
 *
 * Discovery context shows only the PUBLIC professional summary. Choosing a
 * published job computes an explainable match (mode, strengths, gaps and
 * skill-gap evidence) — never a bare score, never private data.
 */
import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { cardCls, ghostBtnCls } from "@/components/candidate/ui";
import { api } from "@/lib/api/session";
import {
  CandidateProfile,
  CompanyJob,
  GapAnalysis,
  OutreachRequestRow,
} from "@/lib/api/types";
import { useOrg } from "@/context/OrgContext";
const modeStyle: Record<string, string> = {
  strong: "bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-400",
  potential: "bg-indigo-100 text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300",
  career_transition:
    "bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-400",
  explore: "bg-neutral-100 text-neutral-600 dark:bg-neutral-800 dark:text-neutral-300",
};

export default function CandidateDetailPage() {
  const params = useParams<{ id: string }>();
  const search = useSearchParams();
  const personId = params.id;
  const { organizationId } = useOrg();
  const [orgId, setOrgId] = useState("");
  const [profile, setProfile] = useState<CandidateProfile | null>(null);
  const [jobs, setJobs] = useState<CompanyJob[]>([]);
  const [jobId, setJobId] = useState(search.get("job") ?? "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [outreach, setOutreach] = useState<OutreachRequestRow[]>([]);
  const [outreachMsg, setOutreachMsg] = useState("");
  const [outreachCtx, setOutreachCtx] = useState("");
  const [outreachSent, setOutreachSent] = useState("");

  const loadProfile = useCallback(
    async (oppId?: string) => {
      if (!orgId) return;
      setBusy(true);
      setError("");
      try {
        const q = oppId ? `?opportunity_id=${oppId}` : "";
        const data = await api.get<CandidateProfile>(
          `/talent/${orgId}/candidates/${personId}${q}`
        );
        setProfile(data);
      } catch (e) {
        setError(String((e as Error).message ?? e));
      } finally {
        setBusy(false);
      }
    },
    [orgId, personId]
  );

  useEffect(() => {
    setOrgId(organizationId);
    if (organizationId) {
      api
        .get<CompanyJob[]>(`/company/${organizationId}/jobs`)
        .then((rows) => setJobs(rows.filter((j) => j.status === "published")))
        .catch(() => setJobs([]));
      api
        .get<OutreachRequestRow[]>(`/talent/${organizationId}/outreach`)
        .then((rows) => setOutreach(rows.filter((r) => r.candidate?.person_id === personId)))
        .catch(() => setOutreach([]));
    }
  }, [personId, organizationId]);

  useEffect(() => {
    if (orgId && personId) {
      void loadProfile();
    }
  }, [orgId, personId, loadProfile]);

  async function selectJob(id: string) {
    setJobId(id);
    if (!id) {
      await loadProfile();
      return;
    }
    const job = jobs.find((j) => j.id === id);
    if (job?.opportunity_id) {
      await loadProfile(job.opportunity_id);
    }
  }

  async function toggleSave() {
    if (!orgId || !profile) return;
    setError("");
    try {
      if (profile.saved) {
        await api.delete(`/talent/${orgId}/candidates/${personId}/saved`);
      } else {
        await api.post(`/talent/${orgId}/candidates/${personId}/saved`, {
          note: "Saved from candidate profile.",
        });
      }
      const opp = jobs.find((j) => j.id === jobId)?.opportunity_id ?? undefined;
      await loadProfile(opp);
    } catch (e) {
      setError(String((e as Error).message ?? e));
    }
  }

  async function sendOutreach() {
    if (!orgId || !outreachMsg.trim()) return;
    setBusy(true);
    setError("");
    setOutreachSent("");
    try {
      const opp = jobs.find((j) => j.id === jobId)?.opportunity_id ?? undefined;
      await api.post(`/talent/${orgId}/outreach`, {
        person_id: personId,
        opportunity_id: opp,
        message: outreachMsg.trim(),
        context: outreachCtx.trim() || undefined,
      });
      setOutreachMsg("");
      setOutreachCtx("");
      setOutreachSent("Request sent — the candidate decides whether to accept.");
      const rows = await api.get<OutreachRequestRow[]>(`/talent/${orgId}/outreach`);
      setOutreach(rows.filter((r) => r.candidate?.person_id === personId));
    } catch (e) {
      setError(String((e as Error).message ?? e));
    } finally {
      setBusy(false);
    }
  }

  const name =
    profile?.name ??
    profile?.person?.full_name ??
    "Candidate";
  const match = profile?.match;
  const skills = profile?.skills ?? [];

  return (
    <div className="space-y-6">
      <Link
        href="/company/candidates"
        className="text-sm text-neutral-400 hover:text-indigo-600"
      >
        ← Candidate discovery
      </Link>

      {error && (
        <div className="rounded-lg border border-red-300 bg-red-50 px-4 py-2 text-sm text-red-700 dark:border-red-900 dark:bg-red-950 dark:text-red-300">
          {error} —{" "}
          <Link href="/company/candidates" className="underline">
            back to search
          </Link>
        </div>
      )}

      {!profile && !error && (
        <div className="py-16 text-center text-neutral-400">Loading…</div>
      )}

      {profile && (
        <>
          <section className={cardCls}>
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <p className="text-xs uppercase tracking-wide text-neutral-400">
                  {profile.context === "pipeline"
                    ? "Candidate from your pipeline"
                    : "Discoverable public profile"}
                </p>
                <h1 className="mt-1 text-2xl font-semibold tracking-tight">{name}</h1>
                {profile.headline && (
                  <p className="mt-1 text-neutral-500 dark:text-neutral-400">
                    {profile.headline}
                  </p>
                )}
                <p className="mt-1 text-sm text-neutral-400">
                  {profile.location ?? "Location not disclosed"}
                  {profile.experience_years != null
                    ? ` · ${profile.experience_years}+ yrs experience`
                    : ""}
                </p>
              </div>
              <button onClick={toggleSave} className={ghostBtnCls}>
                {profile.saved ? "Saved ✓" : "Save candidate"}
              </button>
            </div>

            {profile.experience && profile.experience.length > 0 && (
              <div className="mt-4">
                <h2 className="text-xs uppercase tracking-wide text-neutral-400">
                  Experience
                </h2>
                <ul className="mt-2 space-y-1 text-sm">
                  {profile.experience.map((e, i) => (
                    <li key={i}>
                      <span className="font-medium">{e.title}</span>
                      <span className="text-neutral-400"> — {e.company_name}</span>
                      {e.is_current && (
                        <span className="ml-2 rounded-full bg-emerald-100 px-1.5 py-0.5 text-[10px] text-emerald-700 dark:bg-emerald-950 dark:text-emerald-400">
                          current
                        </span>
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {skills.length > 0 && (
              <div className="mt-4">
                <h2 className="text-xs uppercase tracking-wide text-neutral-400">
                  Skills
                </h2>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {skills.map((s) => (
                    <span
                      key={s.name}
                      className="rounded-full bg-neutral-100 px-2.5 py-0.5 text-xs capitalize text-neutral-600 dark:bg-neutral-800 dark:text-neutral-300"
                    >
                      {s.name}
                      {s.level ? ` · ${s.level}` : ""}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {profile.education && profile.education.length > 0 && (
              <div className="mt-4">
                <h2 className="text-xs uppercase tracking-wide text-neutral-400">
                  Education
                </h2>
                <ul className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
                  {profile.education.map((e, i) => (
                    <li key={i}>{e.degree ?? e.institution}</li>
                  ))}
                </ul>
              </div>
            )}
          </section>

          {/* Live match against one of the company's published jobs */}
          <section className={cardCls}>
            <h2 className="text-sm font-semibold">Why this person matches</h2>
            <div className="mt-3 flex flex-wrap items-center gap-2">
              <select
                value={jobId}
                onChange={(e) => selectJob(e.target.value)}
                className="rounded border border-neutral-300 px-3 py-2 text-sm dark:border-neutral-700 dark:bg-neutral-900"
              >
                <option value="">Compare against a published job…</option>
                {jobs.map((j) => (
                  <option key={j.id} value={j.id}>
                    {j.title}
                  </option>
                ))}
              </select>
              {busy && <span className="text-sm text-neutral-400">Matching…</span>}
            </div>

            {match && (
              <div className="mt-4 space-y-4">
                <div className="flex flex-wrap items-center gap-3">
                  <p className="text-3xl font-semibold tracking-tight">
                    {match.percent}%
                  </p>
                  <span
                    className={`rounded-full px-2.5 py-1 text-xs font-medium capitalize ${modeStyle[match.mode] ?? modeStyle.explore}`}
                  >
                    {match.mode.replace("_", " ")} match
                  </span>
                  <span className="text-[10px] uppercase tracking-wide text-neutral-400">
                    explainable — not a black-box score
                  </span>
                </div>

                {match.strengths.length > 0 && (
                  <div className="space-y-1 text-sm">
                    {match.strengths.map((s, i) => (
                      <p key={`s-${i}`} className="text-emerald-600 dark:text-emerald-400">
                        ✓ {s}
                      </p>
                    ))}
                  </div>
                )}
                {match.gaps.length > 0 && (
                  <div className="space-y-1 text-sm">
                    {match.gaps.map((g, i) => (
                      <p key={`g-${i}`} className="text-amber-600 dark:text-amber-400">
                        ▲ {g}
                      </p>
                    ))}
                  </div>
                )}

                <GapBlock gap={match.gap_analysis} />
              </div>
            )}
          </section>

          {/* Controlled contact request — never reveals private details */}
          <section className={cardCls}>
            <h2 className="text-sm font-semibold">Request contact</h2>
            <p className="mt-1 text-xs text-neutral-400">
              The candidate stays in control. Accepting opens a conversation
              inside AskTrabaajo — no phone numbers or emails are shared.
            </p>
            <div className="mt-3 space-y-3">
              <div className="flex flex-wrap items-center gap-2 text-sm">
                <select
                  value={jobId}
                  onChange={(e) => selectJob(e.target.value)}
                  className="rounded border border-neutral-300 px-3 py-2 dark:border-neutral-700 dark:bg-neutral-900"
                >
                  <option value="">Regarding… (no specific job)</option>
                  {jobs.map((j) => (
                    <option key={j.id} value={j.id}>
                      {j.title}
                    </option>
                  ))}
                </select>
              </div>
              <textarea
                value={outreachMsg}
                onChange={(e) => setOutreachMsg(e.target.value)}
                rows={3}
                placeholder={"Introduce your organization and why you'd like to talk (min 10 characters)."}
                className="w-full rounded border border-neutral-300 bg-white px-3 py-2 text-sm dark:border-neutral-700 dark:bg-neutral-900"
              />
              <input
                value={outreachCtx}
                onChange={(e) => setOutreachCtx(e.target.value)}
                placeholder="Context / role — optional"
                className="w-full rounded border border-neutral-300 bg-white px-3 py-2 text-sm dark:border-neutral-700 dark:bg-neutral-900"
              />
              <button
                className="rounded bg-indigo-500 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-600 disabled:opacity-40"
                disabled={busy || outreachMsg.trim().length < 10}
                onClick={sendOutreach}
              >
                Send request
              </button>
              {outreachSent && (
                <p className="text-sm text-emerald-600 dark:text-emerald-400">
                  {outreachSent}
                </p>
              )}

              {outreach.length > 0 && (
                <div className="flex flex-wrap gap-2 pt-1">
                  {outreach.map((r) => (
                    <span
                      key={r.id}
                      className="rounded-full bg-neutral-100 px-2.5 py-1 text-xs capitalize text-neutral-600 dark:bg-neutral-800 dark:text-neutral-300"
                    >
                      {r.status}
                      {r.opportunity_title ? ` · ${r.opportunity_title}` : ""}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </section>
        </>
      )}
    </div>
  );
}

function GapBlock({ gap }: { gap: GapAnalysis }) {
  return (
    <div className="grid gap-4 sm:grid-cols-2">
      {gap.matched.length > 0 && (
        <div className="rounded-lg border border-neutral-200 p-3 dark:border-neutral-800">
          <p className="text-xs uppercase tracking-wide text-neutral-400">Covered</p>
          <div className="mt-2 space-y-1.5">
            {gap.matched.map((m) => (
              <p key={m.skill} className="text-sm capitalize">
                <span className="font-medium">{m.skill}</span>
                {m.evidence.length > 0 && (
                  <span className="ml-2 text-[10px] text-neutral-400">
                    evidence:{" "}
                    {m.evidence
                      .map((e) => `${e.evidence_type}${e.verification_status === "verified" ? " (verified)" : ""}`)
                      .join(", ")}
                  </span>
                )}
              </p>
            ))}
          </div>
        </div>
      )}
      {gap.gaps.length > 0 && (
        <div className="rounded-lg border border-amber-200 p-3 dark:border-amber-900/40">
          <p className="text-xs uppercase tracking-wide text-amber-500">Gaps</p>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {gap.gaps.map((g) => (
              <span
                key={g.skill}
                className="rounded-full bg-amber-50 px-2 py-0.5 text-xs capitalize text-amber-700 dark:bg-amber-950 dark:text-amber-400"
              >
                − {g.skill}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
