"use client";

import { useEffect, useState } from "react";

import { ErrorBanner, LoadingState, PageHeader } from "@/components/candidate/ui";
import { BucketList, FilterBar, MetricCard, PrivacyNote } from "@/components/government/IntelligenceUI";
import { GovernmentFilters, IntelligenceEnvelope, governmentApi } from "@/lib/api/government";

export default function GovernmentCompaniesPage() {
  const [filters, setFilters] = useState<GovernmentFilters>({});
  const [data, setData] = useState<IntelligenceEnvelope | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    governmentApi
      .companies(filters)
      .then(setData)
      .catch((e) => setError(String((e as Error).message ?? e)));
  }, [filters]);

  return (
    <div className="space-y-8">
      <PageHeader
        kicker="Companies"
        title="Employer landscape"
        subtitle="Organization counts only. Names, contacts and private company profiles are not included."
      />
      <PrivacyNote data={data} />
      <FilterBar onApply={setFilters} />
      {error && <ErrorBanner message={error} />}
      {!data && !error && <LoadingState label="Calculating employers…" />}
      <MetricCard title="Active employers" cell={data?.active_employers} />
      <BucketList title="Employers by industry" buckets={data?.buckets} />
    </div>
  );
}
