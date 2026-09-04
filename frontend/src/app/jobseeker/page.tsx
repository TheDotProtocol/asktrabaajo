"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { ErrorBanner, LoadingState, StatusPill, btnCls, cardCls, ghostBtnCls, labelCls } from "@/components/candidate/ui";
import { useCanonicalAuth } from "@/context/AuthContext";
import { api } from "@/lib/api/session";
import { Dashboard, OpportunityMatch } from "@/lib/api/types";

function greeting() {
  const hour = new Date().getHours();
  if (hour < 12) return "Good morning";
  if (hour < 17) return "Good afternoon";
  return "Good evening";
}

export default function JobseekerHome() {
  const { me } = useCanonicalAuth();
  const [dash, setDash] = useState<Dashboard | null>(null);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      setDash(await api.get<Dashboard>("/jobseeker/dashboard"));
      setError("");
    } catch (e) {
      setError(String((e as Error).message ?? e));
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  if (error && !dash) return <ErrorBanner message={error} onRetry={() => void load()} />;
  if (!dash) return <LoadingState label="Restoring your command surface…" />;

  const first = (me?.full_name || "there").split(" ")[0];
  const completion = dash.profile_completion?.percent ?? 0;
  const missing = dash.profile_completion?.missing ?? [];

  return (
    <div className="space-y-8">
      <header>
        <p className={labelCls}>Command surface</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight sm:text-4xl">
          {greeting()}, {first}.
        </h1>
      </header>

      <section className={`${cardCls} border-[#d4af37]/25`}>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-[#d4af37]">Career advisor</p>
          <span className={labelCls}>Canonical guidance</span>
        </div>
        <h2 className="mt-4 text-2xl font-semibold">Where do you want your career to go next?</h2>
        <p className="mt-2 max-w-2xl text-sm text-[#9ca3af]">
          {dash.advisor?.summary ||
            "Athena chat is not provisioned in this environment. Career Advisor uses your Work ID and goals — no invented statistics."}
        </p>
        <div className="mt-5 flex flex-wrap gap-3">
          <Link href="/jobseeker/career" className={btnCls}>
            Open Career Advisor
          </Link>
          <Link href="/jobseeker/opportunities" className={ghostBtnCls}>
            Explore opportunities
          </Link>
        </div>
      </section>

      <section className="grid gap-4 lg:grid-cols-3">
        <Link href="/id/work-id" className={cardCls}>
          <div className="flex items-start justify-between">
            <p className={labelCls}>Work ID</p>
            <StatusPill status={completion >= 80 ? "strong" : completion > 0 ? "in progress" : "not started"} />
          </div>
          <p className="mt-3 text-3xl font-semibold">{completion}%</p>
          <p className="mt-1 text-sm text-[#9ca3af]">
            {missing.length
              ? `Still needed: ${missing.slice(0, 3).join(", ")}`
              : "Identity record is in good shape."}
          </p>
        </Link>
        <Link href="/jobseeker/work-dna" className={cardCls}>
          <p className={labelCls}>Work DNA</p>
          <p className="mt-3 text-xl font-semibold capitalize">{dash.work_dna_status.replaceAll("_", " ")}</p>
          <p className="mt-1 text-sm text-[#9ca3af]">
            {dash.work_dna_status === "completed"
              ? "Your working patterns are on file."
              : "Take the assessment to inform matching."}
          </p>
        </Link>
        <div className={cardCls}>
          <p className={labelCls}>Upcoming</p>
          {dash.upcoming_interviews.length === 0 ? (
            <p className="mt-3 text-sm text-[#9ca3af]">No interviews scheduled. Applications come first.</p>
          ) : (
            <ul className="mt-3 space-y-2 text-sm">
              {dash.upcoming_interviews.slice(0, 3).map((item) => (
                <li key={item.id} className="flex justify-between gap-3">
                  <span>{new Date(item.scheduled_at).toLocaleString([], { weekday: "short", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}</span>
                  <span className="text-[#9ca3af]">{item.mode}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </section>

      <section className="grid gap-4 sm:grid-cols-4">
        {[
          { label: "Applications", value: dash.stats.applications ?? 0, href: "/jobseeker/applications" },
          { label: "Live", value: dash.stats.live ?? 0, href: "/jobseeker/applications" },
          { label: "Interviews", value: dash.stats.upcoming_interviews ?? 0, href: "/jobseeker/interviews" },
          { label: "Offers", value: dash.stats.pending_offers ?? 0, href: "/jobseeker/offers" },
        ].map((stat) => (
          <Link key={stat.label} href={stat.href} className={cardCls}>
            <p className={labelCls}>{stat.label}</p>
            <p className="mt-2 text-3xl font-semibold">{stat.value}</p>
          </Link>
        ))}
      </section>

      <section className="grid gap-6 lg:grid-cols-5">
        <div className={`${cardCls} lg:col-span-3`}>
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-sm font-semibold">Active pipeline</h2>
            <Link href="/jobseeker/applications" className="text-sm text-[#d4af37] hover:underline">
              All
            </Link>
          </div>
          {dash.recent_applications.length === 0 ? (
            <p className="text-sm text-[#9ca3af]">
              Nothing in motion yet.{" "}
              <Link href="/jobseeker/opportunities" className="text-[#d4af37] hover:underline">
                Find an opportunity
              </Link>{" "}
              and apply deliberately.
            </p>
          ) : (
            <ul className="space-y-3">
              {dash.recent_applications.slice(0, 5).map((app) => (
                <li key={app.id} className="flex items-center justify-between gap-3 text-sm">
                  <div className="min-w-0">
                    <p className="truncate font-medium">{app.opportunity?.title}</p>
                    <p className="truncate text-[#9ca3af]">{app.opportunity?.company_name}</p>
                  </div>
                  <StatusPill status={app.status} />
                </li>
              ))}
            </ul>
          )}
        </div>
        <div className={`${cardCls} lg:col-span-2`}>
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-sm font-semibold">Recommended</h2>
            <Link href="/jobseeker/opportunities" className="text-sm text-[#d4af37] hover:underline">
              All
            </Link>
          </div>
          {dash.recommended.length === 0 ? (
            <p className="text-sm text-[#9ca3af]">
              Matching needs a Work ID and at least one open opportunity. Complete your profile, then return here.
            </p>
          ) : (
            <ul className="space-y-3">
              {dash.recommended.slice(0, 4).map((match: OpportunityMatch) => (
                <li key={match.opportunity_id}>
                  <Link href={`/jobseeker/opportunities/${match.opportunity_id}`} className="block">
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <p className="truncate text-sm font-medium">{match.opportunity?.title}</p>
                        <p className="truncate text-xs text-[#9ca3af]">{match.opportunity?.company_name}</p>
                      </div>
                      <span className="font-mono text-sm text-[#d4af37]">{match.percent}%</span>
                    </div>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </div>
      </section>

      {dash.advisor && dash.advisor.next_actions.length > 0 && (
        <section className={cardCls}>
          <p className={labelCls}>Next useful actions</p>
          <ol className="mt-3 list-decimal space-y-1 pl-5 text-sm text-[#e5e7eb]">
            {dash.advisor.next_actions.slice(0, 4).map((action) => (
              <li key={action}>{action}</li>
            ))}
          </ol>
          {dash.advisor.disclaimer && (
            <p className="mt-4 text-xs text-[#6b7280]">{dash.advisor.disclaimer}</p>
          )}
        </section>
      )}
    </div>
  );
}
