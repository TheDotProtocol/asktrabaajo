"use client";

import { useEffect, useState } from "react";

import { ErrorBanner, LoadingState, PageHeader } from "@/components/candidate/ui";
import { BucketList, FilterBar, PrivacyNote } from "@/components/government/IntelligenceUI";
import { GovernmentFilters, IntelligenceEnvelope, governmentApi } from "@/lib/api/government";

export default function GovernmentOpportunitiesPage() {
  const [groupBy, setGroupBy] = useState("industry");
  const [filters, setFilters] = useState<GovernmentFilters>({});
  const [data, setData] = useState<IntelligenceEnvelope | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    governmentApi
      .opportunities(groupBy, filters)
      .then(setData)
      .catch((e) => setError(String((e as Error).message ?? e)));
  }, [groupBy, filters]);

  return (
    <div className="space-y-8">
      <PageHeader
        kicker="Opportunities"
        title="Where opportunities exist"
        subtitle="Aggregate published roles. No candidate or application records."
      />
      <PrivacyNote data={data} />
      <FilterBar onApply={setFilters}>
        <select
          className="rounded-md border border-[#23272a] bg-[#0b0c0d] px-3 py-2 text-sm"
          value={groupBy}
          onChange={(e) => setGroupBy(e.target.value)}
        >
          <option value="industry">Industry</option>
          <option value="country">Country</option>
          <option value="city">City</option>
          <option value="work_mode">Work mode</option>
          <option value="employment_type">Employment type</option>
          <option value="experience_level">Experience</option>
        </select>
      </FilterBar>
      {error && <ErrorBanner message={error} />}
      {!data && !error && <LoadingState label="Calculating opportunities…" />}
      <BucketList title={`Hiring demand by ${groupBy}`} buckets={data?.buckets} />
    </div>
  );
}
