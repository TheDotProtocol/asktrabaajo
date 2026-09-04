"use client";
/**
 * Career — goals, milestones, and Career Advisor.
 * Recommendations come only from /jobseeker/advisor, /jobseeker/career/intelligence,
 * and /career-advisor/*. Nothing is invented in the browser.
 */
import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";

import {
  EmptyState,
  ErrorBanner,
  PageHeader,
  btnCls,
  cardCls,
  ghostBtnCls,
  inputCls,
  labelCls,
} from "@/components/candidate/ui";
import { api } from "@/lib/api/session";
import {
  AdvisorSnapshot,
  CareerAdvisorActionPlan,
  CareerAdvisorGaps,
  CareerAdvisorOpportunities,
  CareerAdvisorPaths,
  CareerGoal,
  CareerIntelligence,
  CareerMilestone,
} from "@/lib/api/types";

const MODES = [
  { id: "strong", label: "Strong" },
  { id: "potential", label: "Potential" },
  { id: "transition", label: "Career transition" },
  { id: "explore", label: "Explore" },
] as const;

export default function CareerPage() {
  const [advisor, setAdvisor] = useState<AdvisorSnapshot | null>(null);
  const [goals, setGoals] = useState<CareerGoal[]>([]);
  const [milestones, setMilestones] = useState<CareerMilestone[]>([]);
  const [intel, setIntel] = useState<CareerIntelligence | null>(null);
  const [gaps, setGaps] = useState<CareerAdvisorGaps | null>(null);
  const [paths, setPaths] = useState<CareerAdvisorPaths | null>(null);
  const [plan, setPlan] = useState<CareerAdvisorActionPlan | null>(null);
  const [recs, setRecs] = useState<CareerAdvisorOpportunities | null>(null);
  const [mode, setMode] = useState<(typeof MODES)[number]["id"]>("strong");
  const [error, setError] = useState("");
  const [goalTitle, setGoalTitle] = useState("");
  const [targetRole, setTargetRole] = useState("");
  const [industries, setIndustries] = useState("");
  const [workModes, setWorkModes] = useState("");

  const load = useCallback(async () => {
    try {
      const [adv, g, m, i, gap, path, action] = await Promise.all([
        api.get<AdvisorSnapshot>("/jobseeker/advisor"),
        api.get<CareerGoal[]>("/jobseeker/goals"),
        api.get<CareerMilestone[]>("/jobseeker/milestones"),
        api.get<CareerIntelligence>("/jobseeker/career/intelligence"),
        api.get<CareerAdvisorGaps>("/career-advisor/gaps"),
        api.get<CareerAdvisorPaths>("/career-advisor/paths"),
        api.get<CareerAdvisorActionPlan>("/career-advisor/action-plan"),
      ]);
      setAdvisor(adv);
      setGoals(g);
      setMilestones(m);
      setIntel(i);
      setGaps(gap);
      setPaths(path);
      setPlan(action);
      setError("");
    } catch (e) {
      setError(String((e as Error).message ?? e));
    }
  }, []);

  const loadRecs = useCallback(async (nextMode: string) => {
    try {
      setRecs(await api.get<CareerAdvisorOpportunities>(`/career-advisor/opportunities?mode=${nextMode}&limit=8`));
    } catch (e) {
      setError(String((e as Error).message ?? e));
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    void loadRecs(mode);
  }, [loadRecs, mode]);

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
      await loadRecs(mode);
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
      <PageHeader
        kicker="Career Advisor"
        title="Your career map"
        subtitle="Guidance is computed from your Work ID and stated goals. The backend is authoritative — this page never invents a recommendation."
      />
      {error && <ErrorBanner message={error} onRetry={() => void load()} />}

      {intel && (
        <section className="grid gap-6 lg:grid-cols-3">
          <div className={`${cardCls} lg:col-span-2`}>
            <h2 className="text-sm font-semibold">Career intelligence</h2>
            <p className="mt-1 text-xs text-[#6b7280]">
              Computed from your Work ID against real, active opportunities — never a guarantee.
            </p>
            <div className="mt-4 grid gap-4 sm:grid-cols-2">
              <div>
                <h3 className={labelCls}>Roles within reach</h3>
                <div className="mt-2 space-y-2">
                  {intel.roles_within_reach.length === 0 && (
                    <p className="text-xs text-[#6b7280]">Complete your Work ID and add a goal to see these.</p>
                  )}
                  {intel.roles_within_reach.map((r) => (
                    <Link
                      key={r.opportunity_id}
                      href={`/jobseeker/opportunities/${r.opportunity_id}`}
                      className="block rounded-lg border border-[#23272a] px-3 py-2 text-sm hover:border-[#d4af37]/40"
                    >
                      <p className="truncate font-medium">{r.title}</p>
                      <p className="text-xs text-[#9ca3af]">{r.company} · {r.percent}% match</p>
                    </Link>
                  ))}
                </div>
              </div>
              <div>
                <h3 className={labelCls}>Roles to grow into</h3>
                <div className="mt-2 space-y-2">
                  {intel.roles_to_grow_into.length === 0 && (
                    <p className="text-xs text-[#6b7280]">Keep your profile current to unlock these.</p>
                  )}
                  {intel.roles_to_grow_into.map((r) => (
                    <Link
                      key={r.opportunity_id}
                      href={`/jobseeker/opportunities/${r.opportunity_id}`}
                      className="block rounded-lg border border-[#23272a] px-3 py-2 text-sm hover:border-[#d4af37]/40"
                    >
                      <p className="truncate font-medium">{r.title}</p>
                      <p className="text-xs text-[#9ca3af]">{r.company} · {r.percent}%</p>
                      {r.missing_skills.length > 0 && (
                        <p className="mt-1 text-[10px] text-[#d4af37]">needs: {r.missing_skills.slice(0, 4).join(", ")}</p>
                      )}
                    </Link>
                  ))}
                </div>
              </div>
            </div>
          </div>
          <div className={cardCls}>
            <h2 className="text-sm font-semibold">What to develop</h2>
            {intel.skill_development.length > 0 ? (
              <ol className="mt-3 space-y-2 text-sm">
                {intel.skill_development.map((s) => (
                  <li key={s.skill} className="flex items-center justify-between gap-2">
                    <span className="capitalize">{s.skill}</span>
                    <span className="rounded-full border border-[#23272a] px-2 py-0.5 text-[10px] text-[#9ca3af]">
                      {s.appears_in_roles} role{s.appears_in_roles === 1 ? "" : "s"}
                    </span>
                  </li>
                ))}
              </ol>
            ) : (
              <p className="mt-3 text-xs text-[#6b7280]">Roles you nearly match will surface concrete skill gaps here.</p>
            )}
            {intel.path_advice?.next_step && (
              <div className="mt-4 rounded-lg border border-[#23272a] p-3 text-sm">
                <h3 className={labelCls}>Advisory next step</h3>
                <p className="mt-2 font-medium">{intel.path_advice.next_step.role_title}</p>
                <p className="mt-2 text-[10px] text-[#6b7280]">{intel.path_advice.note}</p>
              </div>
            )}
            <p className="mt-4 text-[10px] leading-relaxed text-[#6b7280]">{intel.disclaimer}</p>
          </div>
        </section>
      )}

      <section className={cardCls}>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-sm font-semibold">Recommended opportunities</h2>
            <p className="mt-1 text-xs text-[#6b7280]">{recs?.note ?? "Canonical matching modes from Career Advisor."}</p>
          </div>
          <div className="flex flex-wrap gap-2">
            {MODES.map((item) => (
              <button
                key={item.id}
                type="button"
                className={mode === item.id ? btnCls : ghostBtnCls}
                onClick={() => setMode(item.id)}
              >
                {item.label}
              </button>
            ))}
          </div>
        </div>
        {!recs || recs.items.length === 0 ? (
          <EmptyState
            title="No recommendations in this mode"
            body="Add a career goal and complete your Work ID. Recommendations are never fabricated when the catalogue is empty."
            actionHref="/id/work-id"
            actionLabel="Complete Work ID"
          />
        ) : (
          <ul className="mt-4 grid gap-3 lg:grid-cols-2">
            {recs.items.map((item) => (
              <li key={item.opportunity_id}>
                <Link href={`/jobseeker/opportunities/${item.opportunity_id}`} className="block rounded-lg border border-[#23272a] p-3 hover:border-[#d4af37]/40">
                  <div className="flex justify-between gap-3">
                    <div className="min-w-0">
                      <p className="truncate font-medium">{item.title}</p>
                      <p className="truncate text-xs text-[#9ca3af]">{item.company}</p>
                    </div>
                    <span className="font-mono text-sm text-[#d4af37]">{item.percent}%</span>
                  </div>
                  {item.career_signal?.signals?.[0] && (
                    <p className="mt-2 text-xs text-[#9ca3af]">{item.career_signal.signals[0]}</p>
                  )}
                  {item.missing_skills.length > 0 && (
                    <p className="mt-1 text-[10px] text-[#d4af37]">Missing: {item.missing_skills.slice(0, 4).join(", ")}</p>
                  )}
                </Link>
              </li>
            ))}
          </ul>
        )}
        {recs?.disclaimer && <p className="mt-4 text-[10px] text-[#6b7280]">{recs.disclaimer}</p>}
      </section>

      <section className="grid gap-6 lg:grid-cols-2">
        <div className={cardCls}>
          <h2 className="text-sm font-semibold">Advisor snapshot</h2>
          {advisor ? (
            <div className="mt-3 space-y-4 text-sm">
              <p className="leading-relaxed text-[#e5e7eb]">{advisor.summary}</p>
              {advisor.strongest_skills.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {advisor.strongest_skills.map((s) => (
                    <span key={s} className="rounded-full border border-[#23272a] px-2.5 py-0.5 text-xs capitalize text-[#9ca3af]">
                      {s}
                    </span>
                  ))}
                </div>
              )}
              {advisor.gaps.length > 0 ? (
                <ul className="space-y-2">
                  {advisor.gaps.slice(0, 4).map((g, i) => (
                    <li key={i} className="rounded-lg border border-[#23272a] p-3">
                      <p className="font-medium">{g.title}</p>
                      <p className="mt-0.5 text-xs text-[#9ca3af]">{g.detail}</p>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-xs text-[#6b7280]">Set a career goal and complete your Work ID to unlock targeted guidance.</p>
              )}
              {advisor.disclaimer && <p className="text-[10px] text-[#6b7280]">{advisor.disclaimer}</p>}
            </div>
          ) : (
            <p className="mt-3 text-sm text-[#6b7280]">Loading advisor…</p>
          )}
        </div>

        <div className="space-y-6">
          <div className={cardCls}>
            <h2 className="text-sm font-semibold">Career goal</h2>
            <form onSubmit={createGoal} className="mt-3 space-y-3">
              <input className={inputCls} placeholder="Goal title (e.g. Staff Engineer by 2027)" value={goalTitle} onChange={(e) => setGoalTitle(e.target.value)} />
              <input className={inputCls} placeholder="Target role (e.g. AI Engineer)" value={targetRole} onChange={(e) => setTargetRole(e.target.value)} />
              <input className={inputCls} placeholder="Industries (comma-separated)" value={industries} onChange={(e) => setIndustries(e.target.value)} />
              <input className={inputCls} placeholder="Work modes: remote, hybrid" value={workModes} onChange={(e) => setWorkModes(e.target.value)} />
              <button type="submit" className={btnCls}>
                {goals.length === 0 ? "Set my goal" : "Add another goal"}
              </button>
            </form>
            {goals.length === 0 ? (
              <p className="mt-3 text-xs text-[#6b7280]">No goal yet. Advisor recommendations stay empty until you set one.</p>
            ) : (
              <div className="mt-4 space-y-2">
                {goals.map((g) => (
                  <div key={g.id} className="flex items-center justify-between rounded-lg border border-[#23272a] px-3 py-2 text-sm">
                    <div className="min-w-0">
                      <p className="truncate font-medium">
                        {g.title}
                        {g.is_primary && <span className="ml-2 font-mono text-[10px] uppercase text-[#d4af37]">primary</span>}
                      </p>
                      {g.target_role && <p className="truncate text-xs text-[#9ca3af]">→ {g.target_role}</p>}
                    </div>
                    <button type="button" onClick={() => void deleteGoal(g.id)} className="text-xs text-[#9ca3af] hover:text-red-300">
                      remove
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className={cardCls}>
            <h2 className="text-sm font-semibold">Skill gaps</h2>
            {!gaps || ((gaps.missing_skills?.length ?? 0) + (gaps.matched_skills?.length ?? 0) + (gaps.partial_skills?.length ?? 0) === 0) ? (
              <p className="mt-2 text-xs text-[#6b7280]">
                No target yet. Set a goal or open an opportunity — the advisor will not invent a requirement set.
              </p>
            ) : (
              <div className="mt-3 space-y-2 text-sm">
                {(gaps.matched_skills ?? []).slice(0, 4).map((s) => (
                  <p key={s.skill} className="text-emerald-400">✓ {s.skill}</p>
                ))}
                {(gaps.partial_skills ?? []).slice(0, 3).map((s) => (
                  <p key={s.skill} className="text-[#d4af37]">~ {s.skill}</p>
                ))}
                {(gaps.missing_skills ?? []).slice(0, 4).map((s) => (
                  <p key={s.skill} className="text-[#9ca3af]">− {s.skill}</p>
                ))}
              </div>
            )}
          </div>
        </div>
      </section>

      <section className="grid gap-6 lg:grid-cols-2">
        <div className={cardCls}>
          <h2 className="text-sm font-semibold">Career paths</h2>
          {(paths?.paths ?? []).length === 0 ? (
            <p className="mt-2 text-xs text-[#6b7280]">
              No advisory paths match your history or goal yet. Paths are never invented.
            </p>
          ) : (
            <ul className="mt-3 space-y-2">
              {(paths?.paths ?? []).slice(0, 5).map((p, i) => (
                <li key={`${p.path ?? p.title}-${i}`} className="rounded-lg border border-[#23272a] p-3 text-sm">
                  <p className="font-medium">{p.path ?? p.title}</p>
                  <p className="text-xs capitalize text-[#9ca3af]">{p.classification}{p.target_role ? ` · ${p.target_role}` : ""}</p>
                </li>
              ))}
            </ul>
          )}
        </div>
        <div className={cardCls}>
          <h2 className="text-sm font-semibold">Suggested action plan</h2>
          {(plan?.actions ?? []).length === 0 ? (
            <p className="mt-2 text-xs text-[#6b7280]">The plan appears after a goal or gap analysis exists.</p>
          ) : (
            <ol className="mt-3 list-decimal space-y-2 pl-5 text-sm">
              {(plan?.actions ?? []).slice(0, 6).map((a, i) => (
                <li key={`${a.title}-${i}`}>
                  <p className="font-medium">{a.title}</p>
                  {a.detail && <p className="text-xs text-[#9ca3af]">{a.detail}</p>}
                </li>
              ))}
            </ol>
          )}
          {plan?.disclaimer && <p className="mt-3 text-[10px] text-[#6b7280]">{plan.disclaimer}</p>}
        </div>
      </section>

      <section className={cardCls}>
        <h2 className="text-sm font-semibold">Career milestones</h2>
        {milestones.length === 0 ? (
          <p className="mt-2 text-xs text-[#6b7280]">
            Milestones land here as you progress — offers accepted, roles started, credentials earned. Nothing is faked.
          </p>
        ) : (
          <ol className="mt-3 space-y-2">
            {milestones.map((m) => (
              <li key={m.id} className="flex items-center justify-between rounded-lg border border-[#23272a] px-3 py-2 text-sm">
                <span>
                  <span className="font-medium">{m.title}</span>
                  <span className="ml-2 text-xs text-[#9ca3af]">{m.kind}</span>
                </span>
                <span className="text-xs text-[#6b7280]">{m.occurred_on}</span>
              </li>
            ))}
          </ol>
        )}
      </section>
    </div>
  );
}
