"use client";
/**
 * Opportunity discovery — one catalogue, explainable matching.
 *
 * Every card shows WHY it matches (per-component reasons) and what is
 * missing, never a bare percentage. Save / apply are explicit actions.
 */
import { useCallback, useEffect, useState } from "react";

import { api } from "@/lib/api/session";
import { OpportunityList, OpportunityMatch } from "@/lib/api/types";

const cardCls =
  "rounded-xl border border-neutral-200 bg-white p-5 dark:border-neutral-800 dark:bg-neutral-900";
const inputCls =
  "rounded border border-neutral-300 px-3 py-2 text-sm focus:border-amber-500 focus:outline-none dark:border-neutral-700 dark:bg-neutral-900";
const btnCls =
  "rounded bg-amber-500 px-3 py-1.5 text-sm font-medium text-black hover:bg-amber-400 disabled:opacity-50";
const ghostBtnCls =
  "rounded border border-neutral-300 px-3 py-1.5 text-sm text-neutral-600 hover:border-amber-400 dark:border-neutral-700 dark:text-neutral-300";

export default function OpportunitiesPage() {
  const [list, setList] = useState<OpportunityList | null>(null);
  const [query, setQuery] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [appliedIds, setAppliedIds] = useState<Set<string>>(new Set());

  const load = useCallback(async (q = "") => {
    setBusy(true);
    setError("");
    try {
      const result = await api.get<OpportunityList>(
        `/jobseeker/opportunities${q ? `?q=${encodeURIComponent(q)}` : ""}`
      );
      setList(result);
      setAppliedIds(
        new Set(result.items.filter((i) => i.applied).map((i) => i.opportunity_id))
      );
    } catch (e) {
      setError(String((e as Error).message ?? e));
    } finally {
      setBusy(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function apply(item: OpportunityMatch) {
    setError("");
    try {
      await api.post("/jobseeker/applications", {
        opportunity_id: item.opportunity_id,
        cover_note: "I found this through my AskTrabaajo Career OS.",
      });
      setNotice(`Applied to ${item.opportunity?.title}.`);
      setAppliedIds((prev) => new Set(prev).add(item.opportunity_id));
    } catch (e) {
      setError(String((e as Error).message ?? e));
    }
  }

  async function save(item: OpportunityMatch) {
    try {
      await api.post(`/jobseeker/opportunities/${item.opportunity_id}/save`);
      await load(query);
    } catch (e) {
      setError(String((e as Error).message ?? e));
    }
  }

  return (
    <div className="space-y-6">
      <section className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Opportunities</h1>
          <p className="mt-1 max-w-2xl text-sm text-neutral-500 dark:text-neutral-400">
            Ranked for you with reasons — not a black-box percentage. Strengthen
            your Work ID to sharpen every match.
          </p>
        </div>
        <div className="flex gap-2">
          <input
            className={inputCls}
            placeholder="Search roles, companies, skills…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && load(query)}
          />
          <button type="button" className={btnCls} onClick={() => load(query)} disabled={busy}>
            Search
          </button>
        </div>
      </section>

      {notice && (
        <div className="rounded-lg border border-emerald-300 bg-emerald-50 px-4 py-2 text-sm text-emerald-700 dark:border-emerald-800 dark:bg-emerald-950 dark:text-emerald-300">
          {notice}
        </div>
      )}
      {error && (
        <div className="rounded-lg border border-red-300 bg-red-50 px-4 py-2 text-sm text-red-700 dark:border-red-900 dark:bg-red-950 dark:text-red-300">
          {error}
        </div>
      )}

      {busy && !list && <p className="text-center text-neutral-400">Matching…</p>}

      <div className="grid gap-4 lg:grid-cols-2">
        {(list?.items ?? []).map((item) => {
          const opp = item.opportunity;
          const alreadyApplied = appliedIds.has(item.opportunity_id);
          return (
            <article key={item.opportunity_id} className={cardCls}>
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h2 className="font-semibold">{opp?.title}</h2>
                  <p className="text-sm text-neutral-500 dark:text-neutral-400">
                    {opp?.company_name}
                    {opp?.city ? ` · ${opp.city}${opp.country ? `, ${opp.country}` : ""}` : ""}
                    {opp?.work_mode ? ` · ${opp.work_mode}` : ""}
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-xl font-semibold text-amber-500">{item.percent}%</p>
                  <p className="text-[10px] uppercase tracking-wide text-neutral-400">match</p>
                </div>
              </div>

              {opp?.summary && (
                <p className="mt-2 text-sm text-neutral-500 dark:text-neutral-400">
                  {opp.summary}
                </p>
              )}

              <div className="mt-3 space-y-1 text-xs">
                {item.strengths.slice(0, 2).map((s, i) => (
                  <p key={`s-${i}`} className="text-emerald-600 dark:text-emerald-400">
                    ✓ {s}
                  </p>
                ))}
                {item.gaps.slice(0, 2).map((g, i) => (
                  <p key={`g-${i}`} className="text-amber-600 dark:text-amber-400">
                    ▲ {g}
                  </p>
                ))}
              </div>

              {item.missing_skills.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1">
                  {item.missing_skills.slice(0, 3).map((ms) => (
                    <span
                      key={ms}
                      className="rounded-full bg-neutral-100 px-2 py-0.5 text-[11px] text-neutral-500 dark:bg-neutral-800 dark:text-neutral-400"
                    >
                      − {ms}
                    </span>
                  ))}
                </div>
              )}

              {opp?.min_salary ? (
                <p className="mt-2 text-xs text-neutral-400">
                  {opp.salary_currency} {opp.min_salary.toLocaleString()}
                  {opp.max_salary ? ` – ${opp.max_salary.toLocaleString()}` : ""}
                </p>
              ) : null}

              <div className="mt-4 flex gap-2">
                {alreadyApplied ? (
                  <span className="rounded bg-emerald-100 px-3 py-1.5 text-sm font-medium text-emerald-700 dark:bg-emerald-950 dark:text-emerald-400">
                    Applied ✓
                  </span>
                ) : (
                  <>
                    <button type="button" className={btnCls} onClick={() => apply(item)}>
                      Apply
                    </button>
                    <button
                      type="button"
                      className={ghostBtnCls}
                      onClick={() => save(item)}
                    >
                      {item.saved ? "Saved ✓" : "Save"}
                    </button>
                  </>
                )}
              </div>
            </article>
          );
        })}
      </div>

      {(list?.items ?? []).length === 0 && !busy && (
        <div className={cardCls}>
          <p className="text-center text-sm text-neutral-400">
            No opportunities match your filters.
          </p>
        </div>
      )}
    </div>
  );
}
