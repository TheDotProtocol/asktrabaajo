"use client";
/**
 * Jobseeker Home — the personal Career Command Center.
 *
 * Answers: where am I, what is happening, what should I do next, what is
 * available. Every number comes from the canonical API over owned data.
 */
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { api, getAccessToken } from "@/lib/api/session";
import { Dashboard, OpportunityMatch } from "@/lib/api/types";

const cardCls =
  "rounded-xl border border-neutral-200 bg-white p-5 dark:border-neutral-800 dark:bg-neutral-900";
const statCls = "text-3xl font-semibold tracking-tight";
const labelCls = "text-xs uppercase tracking-wide text-neutral-400";

export default function JobseekerHome() {
  const router = useRouter();
  const [dash, setDash] = useState<Dashboard | null>(null);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    if (!getAccessToken()) {
      router.push("/id");
      return;
    }
    try {
      setDash(await api.get<Dashboard>("/jobseeker/dashboard"));
    } catch (e) {
      setError(String((e as Error).message ?? e));
    }
  }, [router]);

  useEffect(() => {
    load();
  }, [load]);

  if (error) {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50 p-5 text-sm text-red-700 dark:border-red-900 dark:bg-red-950 dark:text-red-300">
        {error} —{" "}
        <button onClick={() => load()} className="underline">
          retry
        </button>
      </div>
    );
  }
  if (!dash) {
    return <div className="py-20 text-center text-neutral-400">Loading your career command center…</div>;
  }

  const completion = dash.profile_completion?.percent ?? 0;
  const stats: { key: string; label: string; value: number }[] = [
    { key: "applications", label: "Applications", value: dash.stats.applications ?? 0 },
    { key: "live", label: "Live", value: dash.stats.live ?? 0 },
    { key: "upcoming_interviews", label: "Upcoming interviews", value: dash.stats.upcoming_interviews ?? 0 },
    { key: "pending_offers", label: "Pending offers", value: dash.stats.pending_offers ?? 0 },
  ];

  return (
    <div className="space-y-8">
      <section>
        <p className="text-sm text-neutral-400">Your career, operating-system style.</p>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight">
          Career Command Center
        </h1>
      </section>

      {/* Health strip */}
      <section className="grid gap-4 md:grid-cols-4">
        {stats.map((s) => (
          <div key={s.key} className={cardCls}>
            <p className={labelCls}>{s.label}</p>
            <p className={statCls}>{s.value}</p>
          </div>
        ))}
      </section>

      <section className="grid gap-6 lg:grid-cols-3">
        {/* Foundation */}
        <div className={`${cardCls} lg:col-span-1`}>
          <h2 className="text-sm font-semibold">Foundation</h2>
          <div className="mt-4 space-y-3 text-sm">
            <Link href="/id/work-id" className="block rounded-lg border border-neutral-200 p-3 hover:border-amber-400 dark:border-neutral-800">
              <div className="flex items-center justify-between">
                <span>Work ID</span>
                <span className="font-semibold text-amber-500">{completion}%</span>
              </div>
              <div className="mt-2 h-1.5 overflow-hidden rounded bg-neutral-100 dark:bg-neutral-800">
                <div className="h-full bg-amber-500" style={{ width: `${completion}%` }} />
              </div>
            </Link>
            <Link
              href="/jobseeker/work-dna"
              className="block rounded-lg border border-neutral-200 p-3 hover:border-amber-400 dark:border-neutral-800"
            >
              <div className="flex items-center justify-between">
                <span>Work DNA</span>
                <span className={dash.work_dna_status === "completed" ? "font-semibold text-emerald-500" : "font-semibold text-amber-500"}>
                  {dash.work_dna_status === "completed" ? "Complete" : "Build it"}
                </span>
              </div>
            </Link>
            <Link
              href="/jobseeker/career"
              className="block rounded-lg border border-neutral-200 p-3 hover:border-amber-400 dark:border-neutral-800"
            >
              <div className="flex items-center justify-between">
                <span>Career goal</span>
                <span className={dash.has_career_goal ? "font-semibold text-emerald-500" : "font-semibold text-neutral-400"}>
                  {dash.has_career_goal ? "Set" : "Not set"}
                </span>
              </div>
            </Link>
          </div>

          {dash.advisor && dash.advisor.next_actions.length > 0 && (
            <div className="mt-5">
              <h3 className={labelCls}>Recommended next</h3>
              <ol className="mt-2 list-decimal space-y-1 pl-4 text-sm text-neutral-600 dark:text-neutral-300">
                {dash.advisor.next_actions.slice(0, 3).map((a) => (
                  <li key={a}>{a}</li>
                ))}
              </ol>
            </div>
          )}
        </div>

        {/* Advisor + recommended */}
        <div className={`${cardCls} lg:col-span-2`}>
          {dash.advisor && (
            <p className="text-sm leading-relaxed text-neutral-600 dark:text-neutral-300">
              {dash.advisor.summary}
            </p>
          )}
          <div className="mt-5">
            <div className="mb-2 flex items-center justify-between">
              <h2 className="text-sm font-semibold">Recommended for you</h2>
              <Link href="/jobseeker/opportunities" className="text-sm text-amber-600 hover:underline dark:text-amber-400">
                View all →
              </Link>
            </div>
            <div className="space-y-2">
              {dash.recommended.length === 0 && (
                <p className="text-sm text-neutral-400">No open opportunities yet.</p>
              )}
              {dash.recommended.slice(0, 4).map((m: OpportunityMatch) => (
                <Link
                  key={m.opportunity_id}
                  href="/jobseeker/opportunities"
                  className="flex items-center justify-between gap-4 rounded-lg border border-neutral-200 px-4 py-3 hover:border-amber-400 dark:border-neutral-800"
                >
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium">{m.opportunity?.title}</p>
                    <p className="truncate text-xs text-neutral-400">
                      {m.opportunity?.company_name}
                      {m.opportunity?.city ? ` · ${m.opportunity.city}` : ""}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-lg font-semibold text-amber-500">{m.percent}%</p>
                    <p className="text-[10px] uppercase tracking-wide text-neutral-400">match</p>
                  </div>
                </Link>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Recent + upcoming */}
      <section className="grid gap-6 lg:grid-cols-2">
        <div className={cardCls}>
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold">Recent applications</h2>
            <Link href="/jobseeker/applications" className="text-sm text-amber-600 hover:underline dark:text-amber-400">
              All →
            </Link>
          </div>
          {dash.recent_applications.length === 0 && (
            <p className="text-sm text-neutral-400">Nothing yet — find your first opportunity.</p>
          )}
          <div className="space-y-2">
            {dash.recent_applications.slice(0, 4).map((a) => (
              <div key={a.id} className="flex items-center justify-between text-sm">
                <div className="min-w-0">
                  <p className="truncate font-medium">{a.opportunity?.title}</p>
                  <p className="truncate text-xs text-neutral-400">{a.opportunity?.company_name}</p>
                </div>
                <span className="rounded-full bg-neutral-100 px-2 py-0.5 text-xs capitalize text-neutral-600 dark:bg-neutral-800 dark:text-neutral-300">
                  {a.status.replace("_", " ")}
                </span>
              </div>
            ))}
          </div>
        </div>
        <div className={cardCls}>
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold">Upcoming interviews</h2>
            <Link href="/jobseeker/interviews" className="text-sm text-amber-600 hover:underline dark:text-amber-400">
              All →
            </Link>
          </div>
          {dash.upcoming_interviews.length === 0 && (
            <p className="text-sm text-neutral-400">No upcoming interviews.</p>
          )}
          <div className="space-y-2">
            {dash.upcoming_interviews.map((i) => (
              <div key={i.id} className="flex items-center justify-between text-sm">
                <span className="font-medium">
                  {new Date(i.scheduled_at).toLocaleString([], {
                    weekday: "short",
                    month: "short",
                    day: "numeric",
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </span>
                <span className="text-neutral-400">{i.mode} · {i.duration_minutes}m</span>
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}
