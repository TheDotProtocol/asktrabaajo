"use client";

import { useCallback, useEffect, useState } from "react";

import {
  EmptyState,
  ErrorBanner,
  LoadingState,
  PageHeader,
  cardCls,
  labelCls,
} from "@/components/candidate/ui";
import { useOrg } from "@/context/OrgContext";
import { api } from "@/lib/api/session";
import { CompanyAnalytics } from "@/lib/api/types";

export default function AnalyticsPage() {
  const { organizationId } = useOrg();
  const [data, setData] = useState<CompanyAnalytics | null>(null);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    if (!organizationId) return;
    try {
      setData(await api.get<CompanyAnalytics>(`/company/${organizationId}/analytics`));
      setError("");
    } catch (e) {
      setError(String((e as Error).message ?? e));
    }
  }, [organizationId]);

  useEffect(() => {
    void load();
  }, [load]);

  if (!organizationId) {
    return <EmptyState title="Select an organization" body="Analytics are tenant-scoped." actionHref="/company" actionLabel="Command center" />;
  }
  if (error && !data) return <ErrorBanner message={error} onRetry={() => void load()} />;
  if (!data) return <LoadingState />;

  const empty = data.applications_total === 0 && data.total_jobs === 0;

  return (
    <div className="space-y-8">
      <PageHeader
        kicker="Hiring analytics"
        title="Funnel"
        subtitle="Canonical /company/{org}/analytics only. No client-side metrics."
      />
      {empty ? (
        <EmptyState title="No hiring activity yet" body="Publish a job and receive applications. This page will not invent a funnel." actionHref="/company/jobs" actionLabel="Open jobs" />
      ) : (
        <>
          <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {[
              ["Open jobs", data.open_jobs],
              ["Total jobs", data.total_jobs],
              ["Applications", data.applications_total],
              ["Need review", data.needs_review],
              ["Interviews", data.interviews_scheduled],
              ["Offers pending", data.offers_pending],
            ].map(([label, value]) => (
              <div key={String(label)} className={cardCls}>
                <p className={labelCls}>{label}</p>
                <p className="mt-2 text-3xl font-semibold">{value}</p>
              </div>
            ))}
          </section>
          <section className={cardCls}>
            <h2 className="text-sm font-semibold">By status</h2>
            <ul className="mt-3 space-y-2 text-sm">
              {Object.entries(data.by_status).map(([status, count]) => (
                <li key={status} className="flex justify-between">
                  <span className="capitalize">{status.replaceAll("_", " ")}</span>
                  <span className="font-mono text-[#d4af37]">{count}</span>
                </li>
              ))}
            </ul>
          </section>
        </>
      )}
    </div>
  );
}
