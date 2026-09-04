"use client";
/**
 * Interview Center (jobseeker side) — workflow infrastructure only.
 * No AI interviewer, no facial/behavioural analysis in this phase.
 * Rescheduling is policy-controlled (a small configurable number of
 * requests, each requiring a reason).
 */
import { FormEvent, useCallback, useEffect, useState } from "react";

import { AthenaAskLink } from "@/components/athena/AthenaAskLink";
import { EmptyState, ErrorBanner, PageHeader, StatusPill, btnCls, cardCls, ghostBtnCls, inputCls } from "@/components/candidate/ui";
import { api } from "@/lib/api/session";
import { Interview } from "@/lib/api/types";
import Link from "next/link";

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
      <PageHeader
        kicker="Calendar"
        title="Interviews"
        subtitle="Upcoming and past interviews. Rescheduling is limited by backend policy — this page cannot bypass it."
        actions={
          <div className="flex flex-wrap gap-2">
            <AthenaAskLink portal="candidate" from="interviews" />
            <Link href="/jobseeker/ai-interview" className={ghostBtnCls}>AI Interview</Link>
            <Link href="/jobseeker/interview-prep" className={ghostBtnCls}>Interview prep</Link>
          </div>
        }
      />

      {notice && <p className="text-sm text-emerald-400">{notice}</p>}
      {error && <ErrorBanner message={error} />}

      {interviews.length === 0 && (
        <EmptyState
          title="No interviews scheduled"
          body="When a company schedules an interview on one of your applications, it will appear here. You cannot invent a slot from this screen."
          actionHref="/jobseeker/applications"
          actionLabel="View applications"
        />
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
                <p className="mt-1 text-sm capitalize text-[#9ca3af]">
                  {i.mode} interview · {i.duration_minutes} minutes
                  {i.interviewer_name ? ` · with ${i.interviewer_name}` : ""}
                </p>
              </div>
              <StatusPill status={i.status} />
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
