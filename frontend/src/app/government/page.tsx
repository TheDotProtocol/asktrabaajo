"use client";

import { useEffect, useState } from "react";

import { ErrorBanner, LoadingState, PageHeader } from "@/components/candidate/ui";
import { BucketList, FilterBar, MetricCard, PrivacyNote } from "@/components/government/IntelligenceUI";
import { GovernmentFilters, IntelligenceEnvelope, governmentApi } from "@/lib/api/government";

export default function GovernmentCommandCenter() {
  const [data, setData] = useState<IntelligenceEnvelope | null>(null);
  const [error, setError] = useState("");
  const [filters, setFilters] = useState<GovernmentFilters>({});

  useEffect(() => {
    setError("");
    governmentApi
      .overview(filters)
      .then(setData)
      .catch((e) => setError(String((e as Error).message ?? e)));
  }, [filters]);

  return (
    <div className="space-y-8">
      <PageHeader
        kicker="Government · Command Center"
        title="Workforce intelligence"
        subtitle="Aggregate, anonymized platform signals. This is not a citizen database."
      />
      <PrivacyNote data={data} />
      <FilterBar onApply={setFilters} />
      {error && <ErrorBanner message={error} onRetry={() => setFilters({ ...filters })} />}
      {!data && !error && <LoadingState label="Calculating aggregates…" />}
      {data?.status === "insufficient_cohort" && (
        <p className="text-sm text-[#9ca3af]">{data.message || "INSUFFICIENT_COHORT"}</p>
      )}
      {data?.cards && (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <MetricCard title="Registered workforce" cell={data.cards.registered_workforce} />
          <MetricCard title="Current employment records" cell={data.cards.current_employment_records} />
          <MetricCard title="Active employers" cell={data.cards.active_employers} />
          <MetricCard title="Open opportunities" cell={data.cards.open_opportunities} />
        </div>
      )}
      <BucketList title="Top skills (supply)" buckets={data?.top_skills?.buckets} />
      {data?.emerging_skills && (
        <p className="text-sm text-[#6b7280]">{data.emerging_skills.message}</p>
      )}
    </div>
  );
}
