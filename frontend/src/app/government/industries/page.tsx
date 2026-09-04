"use client";

import { useEffect, useState } from "react";

import { ErrorBanner, LoadingState, PageHeader } from "@/components/candidate/ui";
import { BucketList, FilterBar, PrivacyNote } from "@/components/government/IntelligenceUI";
import { GovernmentFilters, IntelligenceEnvelope, governmentApi } from "@/lib/api/government";

export default function GovernmentIndustriesPage() {
  const [filters, setFilters] = useState<GovernmentFilters>({});
  const [data, setData] = useState<IntelligenceEnvelope | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    governmentApi
      .industries(filters)
      .then(setData)
      .catch((e) => setError(String((e as Error).message ?? e)));
  }, [filters]);

  return (
    <div className="space-y-8">
      <PageHeader
        kicker="Industry"
        title="Hiring demand by industry"
        subtitle="Published opportunity volume. Neutral metric — not labelled as economic growth."
      />
      <PrivacyNote data={data} />
      <FilterBar onApply={setFilters} />
      {error && <ErrorBanner message={error} />}
      {!data && !error && <LoadingState label="Calculating industries…" />}
      <BucketList title="Open opportunities" buckets={data?.buckets} />
    </div>
  );
}
