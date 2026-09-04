"use client";

import { useCallback, useEffect, useState } from "react";

import {
  EmptyState,
  ErrorBanner,
  LoadingState,
  PageHeader,
  StatusPill,
  btnCls,
  cardCls,
  ghostBtnCls,
} from "@/components/candidate/ui";
import { useOrg } from "@/context/OrgContext";
import { api } from "@/lib/api/session";
import { CompanyInterview } from "@/lib/api/types";
import Link from "next/link";

export default function CompanyInterviewsPage() {
  const { organizationId } = useOrg();
  const [rows, setRows] = useState<CompanyInterview[] | null>(null);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    if (!organizationId) return;
    try {
      setRows(await api.get<CompanyInterview[]>(`/company/${organizationId}/interviews`));
      setError("");
    } catch (e) {
      setError(String((e as Error).message ?? e));
    }
  }, [organizationId]);

  useEffect(() => {
    void load();
  }, [load]);

  async function complete(id: string) {
    if (!organizationId) return;
    try {
      await api.post(`/company/${organizationId}/interviews/${id}/complete`);
      await load();
    } catch (e) {
      setError(String((e as Error).message ?? e));
    }
  }

  async function confirmReschedule(id: string) {
    if (!organizationId) return;
    try {
      await api.post(`/company/${organizationId}/interviews/${id}/confirm-reschedule`);
      await load();
    } catch (e) {
      setError(String((e as Error).message ?? e));
    }
  }

  if (!organizationId) {
    return <EmptyState title="Select an organization" body="Interviews are tenant-scoped." actionHref="/company" actionLabel="Command center" />;
  }
  if (error && !rows) return <ErrorBanner message={error} onRetry={() => void load()} />;
  if (!rows) return <LoadingState />;

  return (
    <div className="space-y-6">
      <PageHeader
        kicker="Calendar"
        title="Interviews"
        subtitle="Schedule from the pipeline. Reschedule confirmation follows backend policy. AI Interview management is a separate human-review surface."
        actions={
          <Link href="/employer/ai-interviews" className={ghostBtnCls}>
            AI Interviews
          </Link>
        }
      />
      {error && <ErrorBanner message={error} />}
      {rows.length === 0 ? (
        <EmptyState
          title="No interviews scheduled"
          body="Open an application in the pipeline to schedule. This page will not invent slots."
          actionHref="/company/pipeline"
          actionLabel="Open pipeline"
        />
      ) : (
        <ul className="grid gap-4 lg:grid-cols-2">
          {rows.map((row) => (
            <li key={row.id} className={cardCls}>
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="font-medium">{new Date(row.scheduled_at).toLocaleString()}</p>
                  <p className="text-sm text-[#9ca3af]">
                    {row.mode} · {row.duration_minutes} min
                    {row.interviewer_name ? ` · ${row.interviewer_name}` : ""}
                  </p>
                </div>
                <StatusPill status={row.status} />
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                {row.status === "scheduled" && (
                  <button type="button" className={btnCls} onClick={() => void complete(row.id)}>
                    Mark complete
                  </button>
                )}
                {row.status === "reschedule_requested" && (
                  <button type="button" className={ghostBtnCls} onClick={() => void confirmReschedule(row.id)}>
                    Confirm reschedule
                  </button>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
