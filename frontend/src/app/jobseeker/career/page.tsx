"use client";
/**
 * Career — Career Advisor snapshot, career goals, and milestones.
 *
 * The Advisor reasons over the real Work ID (roles held, strongest skills,
 * stated goal) and lists concrete gaps + a small set of prioritized
 * recommendations. No invented career facts, no guaranteed outcomes.
 */
import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";

import { api } from "@/lib/api/session";
import {
  AdvisorSnapshot,
  CareerGoal,
  CareerIntelligence,
  CareerMilestone,
} from "@/lib/api/types";

const cardCls =
  "rounded-xl border border-neutral-200 bg-white p-5 dark:border-neutral-800 dark:bg-neutral-900";
const inputCls =
  "w-full rounded border border-neutral-300 px-3 py-2 text-sm focus:border-amber-500 focus:outline-none dark:border-neutral-700 dark:bg-neutral-900";
const btnCls =
  "rounded bg-amber-500 px-4 py-2 text-sm font-medium text-black hover:bg-amber-400 disabled:opacity-50";
const labelCls = "text-xs uppercase tracking-wide text-neutral-400";

export default function CareerPage() {
  const [advisor, setAdvisor] = useState<AdvisorSnapshot | null>(null);
  const [goals, setGoals] = useState<CareerGoal[]>([]);
  const [milestones, setMilestones] = useState<CareerMilestone[]>([]);
  const [intel, setIntel] = useState<CareerIntelligence | null>(null);
  const [error, setError] = useState("");

  const [goalTitle, setGoalTitle] = useState("");
  const [targetRole, setTargetRole] = useState("");
  const [industries, setIndustries] = useState("");
  const [workModes, setWorkModes] = useState("");

  const load = useCallback(async () => {
    try {
      setAdvisor(await api.get<AdvisorSnapshot>("/jobseeker/advisor"));
      setGoals(await api.get<CareerGoal[]>("/jobseeker/goals"));
      setMilestones(await api.get<CareerMilestone[]>("/jobseeker/milestones"));
      setIntel(await api.get<CareerIntelligence>("/jobseeker/career/intelligence"));
    } catch (e) {
      setError(String((e as Error).message ?? e));
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function createGoal(event: FormEvent) {
    event.preventDefault();
    setError("");
    try {
      await api.post("/jobseeker/goals", {
        title: goalTitle || targetRole || "Career direction",
        target_role: targetRole || null,
        target_industries: industries
          ? industries.split(",").map((s) => s.trim()).filter(Boolean)
          : null,
        preferred_work_modes: workModes
          ? workModes.split(",").map((s) => s.trim().toLowerCase()).filter(Boolean)
          : null,
        is_primary: goals.length === 0,
      });
      setGoalTitle("");
      setTargetRole("");
      setIndustries("");
      setWorkModes("");
      await load();
    } catch (e) {
      setError(String((e as Error).message ?? e));
    }
  }

  async function deleteGoal(id: string) {
    try {
      await api.delete(`/jobseeker/goals/${id}`);
      await load();
    } catch (e) {
      setError(String((e as Error).message ?? e));
    }
  }

  return (
    <div className="space-y-8">
      <section>
        <h1 className="text-2xl font-semibold tracking-tight">Career</h1>
        <p className="mt-1 max-w-2xl text-sm text-neutral-500 dark:text-neutral-400">
          Where you are, where you could go, and what stands between the two —
          derived from your own Work ID, never invented.
        </p>
      </section>

      {error && (
        <div className="rounded-lg border border-red-300 bg-red-50 px-4 py-2 text-sm text-red-700 dark:border-red-900 dark:bg-red-950 dark:text-red-300">
          {error}
        </div>
      )}

      {intel && (
        <section className="grid gap-6 lg:grid-cols-3">
          <div className={`${cardCls} lg:col-span-2`}>
            <h2 className="text-sm font-semibold">Career intelligence</h2>
            <p className="mt-1 text-xs text-neutral-400">
              Computed from your Work ID against real, active opportunities —
              never invented, never a guarantee.
            </p>
            <div className="mt-4 grid gap-4 sm:grid-cols-2">
              <div>
                <h3 className={labelCls}>Roles within reach</h3>
                <div className="mt-2 space-y-2">
                  {intel.roles_within_reach.length === 0 && (
                    <p className="text-xs text-neutral-400">Complete your Work ID to see these.</p>
                  )}
                  {intel.roles_within_reach.map((r) => (
                    <Link
                      key={r.opportunity_id}
                      href={`/jobseeker/opportunities/${r.opportunity_id}`}
                      className="block rounded-lg border border-neutral-200 px-3 py-2 text-sm hover:border-amber-400 dark:border-neutral-800"
                    >
                      <p className="truncate font-medium">{r.title}</p>
                      <p className="text-xs text-neutral-400">
                        {r.company} · {r.percent}% match
                      </p>
                    </Link>
                  ))}
                </div>
              </div>
              <div>
                <h3 className={labelCls}>Roles to grow into</h3>
                <div className="mt-2 space-y-2">
                  {intel.roles_to_grow_into.length === 0 && (
                    <p className="text-xs text-neutral-400">Keep your profile current to unlock these.</p>
                  )}
                  {intel.roles_to_grow_into.map((r) => (
                    <Link
                      key={r.opportunity_id}
                      href={`/jobseeker/opportunities/${r.opportunity_id}`}
                      className="block rounded-lg border border-neutral-200 px-3 py-2 text-sm hover:border-amber-400 dark:border-neutral-800"
                    >
                      <p className="truncate font-medium">{r.title}</p>
                      <p className="text-xs text-neutral-400">{r.company} · {r.percent}%</p>
                      {r.missing_skills.length > 0 && (
                        <p className="mt-1 text-[10px] text-amber-600 dark:text-amber-400">
                          needs: {r.missing_skills.slice(0, 4).join(", ")}
                        </p>
                      )}
                    </Link>
                  ))}
                </div>
              </div>
            </div>
          </div>

          <div className={`${cardCls} lg:col-span-1`}>
            <h2 className="text-sm font-semibold">What to develop</h2>
            {intel.skill_development.length > 0 ? (
              <ol className="mt-3 space-y-2 text-sm">
                {intel.skill_development.map((s) => (
                  <li key={s.skill} className="flex items-center justify-between gap-2">
                    <span className="capitalize">{s.skill}</span>
                    <span className="rounded-full bg-neutral-100 px-2 py-0.5 text-[10px] text-neutral-500 dark:bg-neutral-800 dark:text-neutral-400">
                      appears in {s.appears_in_roles} role{s.appears_in_roles === 1 ? "" : "s"}
                    </span>
                  </li>
                ))}
              </ol>
            ) : (
              <p className="mt-3 text-xs text-neutral-400">
                Roles you nearly match will surface concrete skill gaps here.
              </p>
            )}

            {intel.path_advice && intel.path_advice.next_step && (
              <div className="mt-4 rounded-lg border border-neutral-200 p-3 text-sm dark:border-neutral-800">
                <h3 className={labelCls}>Advisory next step</h3>
                <p className="mt-2 font-medium">{intel.path_advice.next_step.role_title}</p>
                {intel.path_advice.next_step.typical_skills && (
                  <div className="mt-2 flex flex-wrap gap-1">
                    {intel.path_advice.next_step.typical_skills.slice(0, 6).map((s) => (
                      <span
                        key={s}
                        className="rounded-full bg-neutral-100 px-2 py-0.5 text-[10px] capitalize text-neutral-500 dark:bg-neutral-800 dark:text-neutral-400"
                      >
                        {s}
                      </span>
                    ))}
                  </div>
                )}
                <p className="mt-2 text-[10px] text-neutral-400">{intel.path_advice.note}</p>
              </div>
            )}

            <p className="mt-4 text-[10px] leading-relaxed text-neutral-400">
              {intel.disclaimer}
            </p>
          </div>
        </section>
      )}

      <section className="grid gap-6 lg:grid-cols-2">
        {/* Advisor */}
        <div className={cardCls}>
          <h2 className="text-sm font-semibold">Career Advisor</h2>
          {advisor ? (
            <div className="mt-3 space-y-4 text-sm">
              <p className="leading-relaxed text-neutral-600 dark:text-neutral-300">
                {advisor.summary}
              </p>
              {advisor.strongest_skills.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {advisor.strongest_skills.map((s) => (
                    <span
                      key={s}
                      className="rounded-full bg-neutral-100 px-2.5 py-0.5 text-xs capitalize text-neutral-600 dark:bg-neutral-800 dark:text-neutral-300"
                    >
                      {s}
                    </span>
                  ))}
                </div>
              )}
              {advisor.gaps.length > 0 ? (
                <div>
                  <h3 className={labelCls}>What stands between you and your goal</h3>
                  <ul className="mt-2 space-y-2">
                    {advisor.gaps.slice(0, 4).map((g, i) => (
                      <li key={i} className="rounded-lg border border-neutral-200 p-3 dark:border-neutral-800">
                        <p className="font-medium">{g.title}</p>
                        <p className="mt-0.5 text-xs text-neutral-500 dark:text-neutral-400">{g.detail}</p>
                      </li>
                    ))}
                  </ul>
                </div>
              ) : (
                <p className="text-xs text-neutral-400">
                  Set a career goal and complete your Work ID to unlock targeted
                  development guidance.
                </p>
              )}
              {advisor.learning_recommendations.length > 0 && (
                <div>
                  <h3 className={labelCls}>Learning & certifications</h3>
                  <ul className="mt-2 space-y-1.5">
                    {advisor.learning_recommendations.map((r, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm">
                        <span className="mt-0.5 text-amber-500">◆</span>
                        <span>
                          <span className="capitalize">{r.skill}</span> — {r.recommendation}
                          <span className="ml-1.5 text-xs uppercase text-neutral-400">({r.kind})</span>
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              <div className="rounded-lg bg-neutral-50 p-3 text-xs text-neutral-400 dark:bg-neutral-950">
                {advisor.disclaimer}
              </div>
            </div>
          ) : (
            <p className="mt-3 text-sm text-neutral-400">Loading…</p>
          )}
        </div>

        {/* Goals */}
        <div className="space-y-6">
          <div className={cardCls}>
            <h2 className="text-sm font-semibold">Career goal</h2>
            <form onSubmit={createGoal} className="mt-3 space-y-3">
              <input
                className={inputCls}
                placeholder="Goal title (e.g. Staff Engineer by 2027)"
                value={goalTitle}
                onChange={(e) => setGoalTitle(e.target.value)}
              />
              <input
                className={inputCls}
                placeholder="Target role (e.g. AI Engineer)"
                value={targetRole}
                onChange={(e) => setTargetRole(e.target.value)}
              />
              <input
                className={inputCls}
                placeholder="Industries (comma-separated)"
                value={industries}
                onChange={(e) => setIndustries(e.target.value)}
              />
              <input
                className={inputCls}
                placeholder="Work modes: remote, hybrid (comma-separated)"
                value={workModes}
                onChange={(e) => setWorkModes(e.target.value)}
              />
              <button type="submit" className={btnCls}>
                {goals.length === 0 ? "Set my goal" : "Add another goal"}
              </button>
            </form>
            {goals.length > 0 && (
              <div className="mt-4 space-y-2">
                {goals.map((g) => (
                  <div
                    key={g.id}
                    className="flex items-center justify-between rounded-lg border border-neutral-200 px-3 py-2 text-sm dark:border-neutral-800"
                  >
                    <div className="min-w-0">
                      <p className="truncate font-medium">
                        {g.title}
                        {g.is_primary && (
                          <span className="ml-2 rounded-full bg-amber-100 px-1.5 py-0.5 text-[10px] uppercase text-amber-700 dark:bg-amber-950 dark:text-amber-400">
                            primary
                          </span>
                        )}
                      </p>
                      {g.target_role && (
                        <p className="truncate text-xs text-neutral-400">→ {g.target_role}</p>
                      )}
                    </div>
                    <button
                      onClick={() => deleteGoal(g.id)}
                      className="text-xs text-neutral-400 hover:text-red-500"
                    >
                      remove
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Milestones */}
          <div className={cardCls}>
            <h2 className="text-sm font-semibold">Career milestones</h2>
            {milestones.length === 0 ? (
              <p className="mt-2 text-xs text-neutral-400">
                Milestones land here automatically as you progress (offers accepted,
                roles started, credentials earned).
              </p>
            ) : (
              <ol className="mt-3 space-y-2">
                {milestones.map((m) => (
                  <li
                    key={m.id}
                    className="flex items-center justify-between rounded-lg border border-neutral-200 px-3 py-2 text-sm dark:border-neutral-800"
                  >
                    <span className="min-w-0">
                      <span className="font-medium">{m.title}</span>
                      <span className="ml-2 text-xs text-neutral-400">{m.kind}</span>
                    </span>
                    <span className="text-xs text-neutral-400">{m.occurred_on}</span>
                  </li>
                ))}
              </ol>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}
