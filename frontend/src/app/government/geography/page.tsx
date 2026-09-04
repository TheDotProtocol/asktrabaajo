"use client";

import { useEffect, useState } from "react";

import { ErrorBanner, LoadingState, PageHeader } from "@/components/candidate/ui";
import { BucketList, FilterBar, PrivacyNote } from "@/components/government/IntelligenceUI";
import { GovernmentFilters, IntelligenceEnvelope, governmentApi } from "@/lib/api/government";

export default function GovernmentGeographyPage() {
  const [filters, setFilters] = useState<GovernmentFilters>({});
  const [data, setData] = useState<IntelligenceEnvelope | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    governmentApi
      .geography(filters)
      .then(setData)
      .catch((e) => setError(String((e as Error).message ?? e)));
  }, [filters]);

  return (
    <div className="space-y-8">
      <PageHeader
        kicker="Geography"
        title="Workforce by city"
        subtitle="City labels from Work ID profiles. Street addresses and coordinates are never included."
      />
      <PrivacyNote data={data} />
      <FilterBar onApply={setFilters} />
      {error && <ErrorBanner message={error} />}
      {!data && !error && <LoadingState label="Calculating geography…" />}
      {data?.status === "insufficient_cohort" && <p className="text-sm text-[#9ca3af]">{data.message}</p>}
      <BucketList title="Cities" buckets={data?.buckets} />
    </div>
  );
}
