"use client";
/**
 * Application tracker — statuses come from the controlled backend model.
 */
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import {
  EmptyState,
  ErrorBanner,
  LoadingState,
  PageHeader,
  StatusPill,
  cardCls,
} from "@/components/candidate/ui";
import { api } from "@/lib/api/session";
import { ApplicationDetail, JobApplication } from "@/lib/api/types";

const PIPELINE = [
  "applied",
  "screening",
  "interview",
  "decision",
  "offer",
  "accepted",
  "onboarding",
] as const;

function stageIndex(status: string): number {
  const map: Record<string, number> = {
    applied: 0,
    application_received: 0,
    screening: 1,
    assessment: 1,
    interview: 2,
    on_hold: 2,
    rejected: 3,
    withdrawn: 3,
    offer: 4,
    accepted: 5,
    onboarding: 6,
  };
  return map[status] ?? 0;
}

export default function ApplicationsPage() {
  const [applications, setApplications] = useState<JobApplication[] | null>(null);
  const [expanded, setExpanded] = useState<Record<string, ApplicationDetail | null>>({});
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      setApplications(await api.get<JobApplication[]>("/jobseeker/applications"));
      setError("");
    } catch (e) {
      setError(String((e as Error).message ?? e));
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function toggle(appId: string) {
    if (expanded[appId]) {
      setExpanded((prev) => ({ ...prev, [appId]: null }));
      return;
    }
    try {
      const detail = await api.get<ApplicationDetail>(`/jobseeker/applications/${appId}`);
      setExpanded((prev) => ({ ...prev, [appId]: detail }));
    } catch (e) {
      setError(String((e as Error).message ?? e));
    }
  }

  async function withdraw(appId: string) {
    if (!window.confirm("Withdraw this application?")) return;
    try {
      await api.post(`/jobseeker/applications/${appId}/withdraw`);
      await load();
    } catch (e) {
      setError(String((e as Error).message ?? e));
    }
  }

  const liveStatuses = new Set([
    "applied",
    "application_received",
    "screening",
    "assessment",
    "interview",
    "on_hold",
  ]);

  if (error && !applications) return <ErrorBanner message={error} onRetry={() => void load()} />;
  if (!applications) return <LoadingState />;

  return (
    <div className="space-y-6">
      <PageHeader
        kicker="Pipeline"
        title="Applications"
        subtitle="One controlled lifecycle. Every status change is recorded on the timeline. The UI cannot invent a stage."
      />
      {error && <ErrorBanner message={error} />}

      {applications.length === 0 ? (
        <EmptyState
          title="No applications yet"
          body="When you apply, the journey appears here: Applied → Screening → Interview → Decision → Offer → Accepted → Onboarding."
          actionHref="/jobseeker/opportunities"
          actionLabel="Find an opportunity"
        />
      ) : (
        <div className="space-y-3">
          {applications.map((a) => {
            const idx = stageIndex(a.status);
            return (
              <article key={a.id} className={cardCls}>
                <button type="button" className="flex w-full items-center justify-between gap-4 text-left" onClick={() => void toggle(a.id)}>
                  <div className="min-w-0">
                    <p className="truncate font-medium">{a.opportunity?.title}</p>
                    <p className="truncate text-xs text-[#9ca3af]">
                      {a.opportunity?.company_name}
                      {a.applied_at ? ` · applied ${new Date(a.applied_at).toLocaleDateString()}` : ""}
                    </p>
                  </div>
                  <StatusPill status={a.status} />
                </button>
                <ol className="mt-4 flex flex-wrap gap-1">
                  {PIPELINE.map((step, i) => (
                    <li
                      key={step}
                      className={`rounded-full px-2 py-0.5 font-mono text-[10px] uppercase ${
                        i <= idx ? "bg-[#d4af37]/15 text-[#d4af37]" : "text-[#6b7280]"
                      }`}
                    >
                      {step}
                    </li>
                  ))}
                </ol>
                {expanded[a.id] && (
                  <div className="mt-4 border-t border-[#23272a] pt-4">
                    <div className="space-y-2">
                      {expanded[a.id]?.timeline.map((event) => (
                        <div key={event.id} className="flex items-start gap-3 text-sm">
                          <span className="mt-1.5 size-2 shrink-0 rounded-full bg-[#d4af37]" />
                          <div>
                            <p>
                              <span className="capitalize">{(event.from_status ?? "created").replace("_", " ")}</span>
                              {" → "}
                              <span className="font-medium capitalize">{event.to_status.replace("_", " ")}</span>
                            </p>
                            {event.note && <p className="text-xs text-[#9ca3af]">{event.note}</p>}
                            <p className="text-xs text-[#6b7280]">{new Date(event.created_at).toLocaleString()}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                    <div className="mt-4 flex flex-wrap gap-2">
                      {expanded[a.id]?.has_interview && (
                        <Link href="/jobseeker/interviews" className="text-xs text-[#d4af37] hover:underline">
                          Interview scheduled
                        </Link>
                      )}
                      {expanded[a.id]?.has_offer && (
                        <Link href="/jobseeker/offers" className="text-xs text-emerald-400 hover:underline">
                          Offer on the table
                        </Link>
                      )}
                      {liveStatuses.has(a.status) && (
                        <button type="button" onClick={() => void withdraw(a.id)} className="ml-auto text-xs text-[#9ca3af] hover:text-red-300">
                          withdraw
                        </button>
                      )}
                    </div>
                  </div>
                )}
              </article>
            );
          })}
        </div>
      )}
    </div>
  );
}
