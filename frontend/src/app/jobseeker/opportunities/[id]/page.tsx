"use client";
/**
 * Opportunity intelligence — the reverse side of the Talent Graph.
 *
 * Shows the explainable match, the structured requirements (raw employer
 * wording preserved), and the skill-gap analysis with evidence drawn from
 * the caller's own Work ID. Apply / save remain explicit actions.
 */
import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { api } from "@/lib/api/session";
import { JobseekerOpportunityDetail } from "@/lib/api/types";

const cardCls =
  "rounded-xl border border-neutral-200 bg-white p-5 dark:border-neutral-800 dark:bg-neutral-900";
const btnCls =
  "rounded bg-amber-500 px-3 py-1.5 text-sm font-medium text-black hover:bg-amber-400 disabled:opacity-50";
const ghostBtnCls =
  "rounded border border-neutral-300 px-3 py-1.5 text-sm text-neutral-600 hover:border-amber-400 dark:border-neutral-700 dark:text-neutral-300";

export default function OpportunityDetailPage() {
  const params = useParams<{ id: string }>();
  const oppId = params.id;
  const [detail, setDetail] = useState<JobseekerOpportunityDetail | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const load = useCallback(async () => {
    setError("");
    try {
      setDetail(await api.get<JobseekerOpportunityDetail>(`/jobseeker/opportunities/${oppId}`));
    } catch (e) {
      setError(String((e as Error).message ?? e));
    }
  }, [oppId]);

  useEffect(() => {
    void load();
  }, [load]);

  async function apply() {
    setError("");
    try {
      await api.post("/jobseeker/applications", {
        opportunity_id: oppId,
        cover_note: "I found this through my AskTrabaajo Career OS.",
      });
      setNotice("Application submitted.");
      await load();
    } catch (e) {
      setError(String((e as Error).message ?? e));
    }
  }

  async function save() {
    setError("");
    try {
      await api.post(`/jobseeker/opportunities/${oppId}/save`);
      await load();
    } catch (e) {
      setError(String((e as Error).message ?? e));
    }
  }

  if (error) {
    return (
      <div className={cardCls}>
        <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
        <Link href="/jobseeker/opportunities" className="mt-3 inline-block text-sm text-neutral-400 hover:text-amber-600">
          ← All opportunities
        </Link>
      </div>
    );
  }
  if (!detail) {
    return <div className="py-16 text-center text-neutral-400">Loading…</div>;
  }

  const opp = detail.opportunity;
  const match = detail.match;
  const gap = detail.gap_analysis;

  return (
    <div className="space-y-6">
      <Link
        href="/jobseeker/opportunities"
        className="text-sm text-neutral-400 hover:text-amber-600"
      >
        ← Opportunities
      </Link>

      {notice && (
        <div className="rounded-lg border border-emerald-300 bg-emerald-50 px-4 py-2 text-sm text-emerald-700 dark:border-emerald-800 dark:bg-emerald-950 dark:text-emerald-300">
          {notice}
        </div>
      )}

      <section className={cardCls}>
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">{opp.title}</h1>
            <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
              {opp.company_name}
              {opp.city ? ` · ${opp.city}${opp.country ? `, ${opp.country}` : ""}` : ""}
              {opp.work_mode ? ` · ${opp.work_mode}` : ""}
              {opp.employment_type ? ` · ${opp.employment_type.replace("_", " ")}` : ""}
            </p>
          </div>
          {match && (
            <div className="text-right">
              <p className="text-3xl font-semibold text-amber-500">{match.percent}%</p>
              <p className="text-[10px] uppercase tracking-wide text-neutral-400">
                explainable match
              </p>
            </div>
          )}
        </div>
        {opp.summary && (
          <p className="mt-3 text-sm text-neutral-500 dark:text-neutral-400">{opp.summary}</p>
        )}
        {opp.min_salary && (
          <p className="mt-2 text-xs text-neutral-400">
            {opp.salary_currency} {opp.min_salary.toLocaleString()}
            {opp.max_salary ? ` – ${opp.max_salary.toLocaleString()}` : ""}
          </p>
        )}
        <div className="mt-4 flex gap-2">
          {detail.applied ? (
            <span className="rounded bg-emerald-100 px-3 py-1.5 text-sm font-medium text-emerald-700 dark:bg-emerald-950 dark:text-emerald-400">
              Applied ✓
            </span>
          ) : (
            <>
              <button type="button" className={btnCls} onClick={apply}>
                Apply
              </button>
              <button type="button" className={ghostBtnCls} onClick={save}>
                {detail.saved ? "Saved ✓" : "Save"}
              </button>
            </>
          )}
        </div>
      </section>

      {match && (
        <section className={`${cardCls} grid gap-6 md:grid-cols-2`}>
          <div>
            <h2 className="text-sm font-semibold">Why this matches you</h2>
            <div className="mt-3 space-y-1.5 text-sm">
              {match.strengths.slice(0, 4).map((s, i) => (
                <p key={`s-${i}`} className="text-emerald-600 dark:text-emerald-400">
                  ✓ {s}
                </p>
              ))}
              {match.gaps.slice(0, 4).map((g, i) => (
                <p key={`g-${i}`} className="text-amber-600 dark:text-amber-400">
                  ▲ {g}
                </p>
              ))}
            </div>
          </div>
          <div>
            <h2 className="text-sm font-semibold">Skill gap — against this role</h2>
            <div className="mt-3 space-y-2">
              {gap.matched.length > 0 && (
                <p className="text-xs text-neutral-500 dark:text-neutral-400">
                  <span className="font-medium text-neutral-700 dark:text-neutral-200">Covered:</span>{" "}
                  {gap.matched
                    .map((m) => `${m.skill}${m.evidence.length ? ` (${m.evidence.length} evidence)` : ""}`)
                    .join(", ")}
                </p>
              )}
              {gap.gaps.length > 0 && (
                <p className="text-xs text-amber-600 dark:text-amber-400">
                  <span className="font-medium">Gaps:</span>{" "}
                  {gap.gaps.map((g) => g.skill).join(", ")}
                </p>
              )}
              {gap.gaps.length === 0 && (
                <p className="text-xs text-emerald-600 dark:text-emerald-400">
                  You cover every stated skill requirement.
                </p>
              )}
            </div>
          </div>
        </section>
      )}

      {detail.requirements.length > 0 && (
        <section className={cardCls}>
          <h2 className="text-sm font-semibold">Structured requirements</h2>
          <p className="mt-1 text-xs text-neutral-400">
            Original employer wording preserved; linked to the canonical skill
            taxonomy where one resolves.
          </p>
          <div className="mt-3 space-y-1.5 text-sm">
            {detail.requirements.map((r) => (
              <div key={r.id} className="flex flex-wrap items-center gap-2">
                <span className="rounded-full bg-neutral-100 px-2 py-0.5 text-[11px] capitalize text-neutral-600 dark:bg-neutral-800 dark:text-neutral-300">
                  {r.requirement_kind}
                </span>
                {r.min_years != null && (
                  <span className="text-[11px] text-neutral-400">{r.min_years}+ yrs</span>
                )}
                <span className="text-neutral-700 dark:text-neutral-200">{r.raw_text}</span>
                {r.skill && (
                  <span className="text-[11px] text-amber-600 dark:text-amber-400">
                    → {r.skill}
                  </span>
                )}
              </div>
            ))}
          </div>
        </section>
      )}

      <p className="max-w-3xl text-xs text-neutral-400">
        Matches and gaps are computed from your Work ID and this opportunity —
        deterministic and explainable, never a prediction of hiring outcomes.
      </p>
    </div>
  );
}
