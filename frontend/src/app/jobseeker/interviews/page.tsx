"use client";
/**
 * Interview Center (jobseeker side) — workflow infrastructure only.
 * No AI interviewer, no facial/behavioural analysis in this phase.
 * Rescheduling is policy-controlled (a small configurable number of
 * requests, each requiring a reason).
 */
import { FormEvent, useCallback, useEffect, useState } from "react";

import { api } from "@/lib/api/session";
import { Interview } from "@/lib/api/types";

const cardCls =
  "rounded-xl border border-neutral-200 bg-white p-5 dark:border-neutral-800 dark:bg-neutral-900";
const inputCls =
  "w-full rounded border border-neutral-300 px-3 py-2 text-sm focus:border-amber-500 focus:outline-none dark:border-neutral-700 dark:bg-neutral-900";
const btnCls =
  "rounded bg-amber-500 px-4 py-2 text-sm font-medium text-black hover:bg-amber-400 disabled:opacity-50";

export default function InterviewsPage() {
  const [interviews, setInterviews] = useState<Interview[]>([]);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [requesting, setRequesting] = useState<string | null>(null);
  const [reason, setReason] = useState("");

  const load = useCallback(async () => {
    try {
      setInterviews(await api.get<Interview[]>("/jobseeker/interviews"));
    } catch (e) {
      setError(String((e as Error).message ?? e));
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function requestReschedule(id: string, event: FormEvent) {
    event.preventDefault();
    try {
      await api.post(`/jobseeker/interviews/${id}/reschedule-request`, { reason });
      setNotice("Reschedule request recorded.");
      setReason("");
      setRequesting(null);
      await load();
    } catch (e) {
      setError(String((e as Error).message ?? e));
    }
  }

  return (
    <div className="space-y-6">
      <section>
        <h1 className="text-2xl font-semibold tracking-tight">Interviews</h1>
        <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
          Your interview center. Rescheduling is limited and reason-based.
        </p>
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

      {interviews.length === 0 && (
        <div className={cardCls}>
          <p className="text-center text-sm text-neutral-400">
            No interviews scheduled yet. They appear here once a company
            schedules one on your application.
          </p>
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-2">
        {interviews.map((i) => (
          <article key={i.id} className={cardCls}>
            <div className="flex items-start justify-between">
              <div>
                <p className="text-lg font-semibold">
                  {new Date(i.scheduled_at).toLocaleString([], {
                    weekday: "short",
                    month: "long",
                    day: "numeric",
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </p>
                <p className="mt-1 text-sm capitalize text-neutral-500 dark:text-neutral-400">
                  {i.mode} interview · {i.duration_minutes} minutes
                  {i.interviewer_name ? ` · with ${i.interviewer_name}` : ""}
                </p>
              </div>
              <span
                className={`rounded-full px-2.5 py-0.5 text-xs capitalize ${
                  i.status === "completed"
                    ? "bg-neutral-100 text-neutral-500 dark:bg-neutral-800 dark:text-neutral-400"
                    : "bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-400"
                }`}
              >
                {i.status.replace("_", " ")}
              </span>
            </div>

            {i.meeting_link && i.status === "scheduled" && (
              <a
                href={i.meeting_link}
                target="_blank"
                rel="noreferrer"
                className="mt-3 inline-block rounded bg-neutral-900 px-3 py-1.5 text-sm text-white hover:bg-neutral-700 dark:bg-neutral-100 dark:text-black"
              >
                Join meeting ↗
              </a>
            )}

            {i.reschedule_count > 0 && (
              <p className="mt-2 text-xs text-neutral-400">
                Rescheduled {i.reschedule_count} time(s)
                {i.reschedule_reason ? ` — last reason: ${i.reschedule_reason}` : ""}
              </p>
            )}

            {requesting === i.id ? (
              <form
                onSubmit={(e) => requestReschedule(i.id, e)}
                className="mt-3 space-y-2 border-t border-neutral-100 pt-3 dark:border-neutral-800"
              >
                <textarea
                  className={inputCls}
                  rows={2}
                  placeholder="Why do you need to reschedule?"
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                />
                <div className="flex gap-2">
                  <button type="submit" className={btnCls} disabled={reason.trim().length < 5}>
                    Send request
                  </button>
                  <button
                    type="button"
                    className="rounded border border-neutral-300 px-3 py-1.5 text-sm text-neutral-500 dark:border-neutral-700"
                    onClick={() => setRequesting(null)}
                  >
                    Cancel
                  </button>
                </div>
              </form>
            ) : (
              i.status === "scheduled" && (
                <button
                  type="button"
                  className="mt-3 text-sm text-neutral-500 underline-offset-2 hover:text-amber-600 hover:underline dark:text-neutral-400"
                  onClick={() => {
                    setRequesting(i.id);
                    setReason("");
                  }}
                >
                  Request reschedule
                </button>
              )
            )}
          </article>
        ))}
      </div>
    </div>
  );
}
