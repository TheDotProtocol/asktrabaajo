"use client";
import Link from "next/link";
/**
 * Application Manager — one lifecycle with a full timeline per application.
 * Statuses come from the controlled model; withdraw goes through the state
 * machine (the API never lets the UI write arbitrary statuses).
 */
import { useCallback, useEffect, useState } from "react";

import { api } from "@/lib/api/session";
import { ApplicationDetail, JobApplication } from "@/lib/api/types";

const cardCls =
  "rounded-xl border border-neutral-200 bg-white p-5 dark:border-neutral-800 dark:bg-neutral-900";

export default function ApplicationsPage() {
  const [applications, setApplications] = useState<JobApplication[]>([]);
  const [expanded, setExpanded] = useState<Record<string, ApplicationDetail | null>>({});
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      setApplications(await api.get<JobApplication[]>("/jobseeker/applications"));
    } catch (e) {
      setError(String((e as Error).message ?? e));
    }
  }, []);

  useEffect(() => {
    load();
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

  return (
    <div className="space-y-6">
      <section>
        <h1 className="text-2xl font-semibold tracking-tight">Applications</h1>
        <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
          One controlled lifecycle. Every status change is on the timeline.
        </p>
      </section>

      {error && (
        <div className="rounded-lg border border-red-300 bg-red-50 px-4 py-2 text-sm text-red-700 dark:border-red-900 dark:bg-red-950 dark:text-red-300">
          {error}
        </div>
      )}

      {applications.length === 0 && (
        <div className={cardCls}>
          <p className="text-center text-sm text-neutral-400">
            No applications yet — explore{" "}
            <Link href="/jobseeker/opportunities" className="text-amber-600 hover:underline">
              opportunities
            </Link>
            .
          </p>
        </div>
      )}

      <div className="space-y-3">
        {applications.map((a) => (
          <article key={a.id} className={cardCls}>
            <button
              type="button"
              className="flex w-full items-center justify-between gap-4 text-left"
              onClick={() => toggle(a.id)}
            >
              <div className="min-w-0">
                <p className="truncate font-medium">{a.opportunity?.title}</p>
                <p className="truncate text-xs text-neutral-400">
                  {a.opportunity?.company_name}
                  {a.applied_at
                    ? ` · applied ${new Date(a.applied_at).toLocaleDateString()}`
                    : ""}
                </p>
              </div>
              <div className="flex items-center gap-3">
                <span
                  className={`rounded-full px-2.5 py-0.5 text-xs capitalize ${
                    a.status === "accepted"
                      ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-400"
                      : a.status === "rejected" || a.status === "withdrawn"
                        ? "bg-neutral-100 text-neutral-500 dark:bg-neutral-800 dark:text-neutral-400"
                        : "bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-400"
                  }`}
                >
                  {a.status.replace("_", " ")}
                </span>
                <span className="text-neutral-300 dark:text-neutral-600">▾</span>
              </div>
            </button>

            {expanded[a.id] && (
              <div className="mt-4 border-t border-neutral-100 pt-4 dark:border-neutral-800">
                <div className="space-y-2">
                  {expanded[a.id]?.timeline.map((event) => (
                    <div key={event.id} className="flex items-start gap-3 text-sm">
                      <span className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-amber-500" />
                      <div>
                        <p>
                          <span className="capitalize">
                            {(event.from_status ?? "created").replace("_", " ")}
                          </span>{" "}
                          →{" "}
                          <span className="font-medium capitalize">
                            {event.to_status.replace("_", " ")}
                          </span>
                        </p>
                        {event.note && (
                          <p className="text-xs text-neutral-400">{event.note}</p>
                        )}
                        <p className="text-xs text-neutral-400">
                          {new Date(event.created_at).toLocaleString()}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
                <div className="mt-4 flex gap-2">
                  {expanded[a.id]?.has_interview && (
                    <span className="rounded-full bg-neutral-100 px-2.5 py-1 text-xs text-neutral-500 dark:bg-neutral-800 dark:text-neutral-400">
                      Interview scheduled
                    </span>
                  )}
                  {expanded[a.id]?.has_offer && (
                    <span className="rounded-full bg-emerald-100 px-2.5 py-1 text-xs text-emerald-700 dark:bg-emerald-950 dark:text-emerald-400">
                      Offer on the table
                    </span>
                  )}
                  {liveStatuses.has(a.status) && (
                    <button
                      type="button"
                      onClick={() => withdraw(a.id)}
                      className="ml-auto text-xs text-neutral-400 hover:text-red-500"
                    >
                      withdraw
                    </button>
                  )}
                </div>
              </div>
            )}
          </article>
        ))}
      </div>
    </div>
  );
}
