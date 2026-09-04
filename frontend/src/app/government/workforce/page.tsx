"use client";

import { useEffect, useState } from "react";

import { ErrorBanner, LoadingState, PageHeader } from "@/components/candidate/ui";
import { BucketList, FilterBar, PrivacyNote } from "@/components/government/IntelligenceUI";
import { GovernmentFilters, IntelligenceEnvelope, governmentApi } from "@/lib/api/government";

export default function GovernmentWorkforcePage() {
  const [groupBy, setGroupBy] = useState("country");
  const [filters, setFilters] = useState<GovernmentFilters>({});
  const [data, setData] = useState<IntelligenceEnvelope | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    governmentApi
      .workforce(groupBy, filters)
      .then(setData)
      .catch((e) => setError(String((e as Error).message ?? e)));
  }, [groupBy, filters]);

  return (
    <div className="space-y-8">
      <PageHeader
        kicker="Workforce"
        title="Workforce distribution"
        subtitle="Counts of registered Work IDs. Employment labels are observational, not official labour-force statistics."
      />
      <PrivacyNote data={data} />
      <FilterBar onApply={setFilters}>
        <select
          className="rounded-md border border-[#23272a] bg-[#0b0c0d] px-3 py-2 text-sm"
          value={groupBy}
          onChange={(e) => setGroupBy(e.target.value)}
        >
          <option value="country">Country</option>
          <option value="state">State / province</option>
          <option value="city">City</option>
          <option value="education">Education</option>
          <option value="employment">Employment record</option>
        </select>
      </FilterBar>
      {error && <ErrorBanner message={error} />}
      {!data && !error && <LoadingState label="Calculating workforce…" />}
      <BucketList title={`By ${groupBy}`} buckets={data?.buckets} />
    </div>
  );
}
