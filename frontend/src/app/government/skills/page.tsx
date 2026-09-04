"use client";

import { useEffect, useState } from "react";

import { ErrorBanner, LoadingState, PageHeader, cardCls } from "@/components/candidate/ui";
import { BucketList, FilterBar, PrivacyNote } from "@/components/government/IntelligenceUI";
import { GovernmentFilters, IntelligenceEnvelope, governmentApi } from "@/lib/api/government";

export default function GovernmentSkillsPage() {
  const [filters, setFilters] = useState<GovernmentFilters>({});
  const [data, setData] = useState<IntelligenceEnvelope | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    governmentApi
      .skills(filters)
      .then(setData)
      .catch((e) => setError(String((e as Error).message ?? e)));
  }, [filters]);

  return (
    <div className="space-y-8">
      <PageHeader
        kicker="Skills"
        title="Skill supply and hiring demand"
        subtitle="Supply is people with the skill on a Work ID. Demand is published opportunities listing the skill. Gaps are not forecasts."
      />
      <PrivacyNote data={data} />
      <FilterBar onApply={setFilters} />
      {error && <ErrorBanner message={error} />}
      {!data && !error && <LoadingState label="Calculating skills…" />}
      <div className="grid gap-4 lg:grid-cols-2">
        <BucketList title="Skill supply" buckets={data?.supply?.buckets} />
        <BucketList title="Skill demand (open roles)" buckets={data?.demand?.buckets} />
      </div>
      <div className={cardCls}>
        <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-[#9ca3af]">Skill gaps</p>
        <ul className="mt-4 divide-y divide-[#23272a]">
          {(data?.gaps || []).map((gap) => (
            <li key={gap.key} className="flex items-center justify-between py-2.5 text-sm">
              <span>{gap.key}</span>
              <span className="font-mono text-[#9ca3af]">
                {gap.status === "ok" ? `demand ${gap.demand} · supply ${gap.supply} · gap ${gap.gap}` : gap.message || "INSUFFICIENT DATA"}
              </span>
            </li>
          ))}
          {!data?.gaps?.length && <li className="py-2 text-sm text-[#6b7280]">No sufficient data</li>}
        </ul>
      </div>
    </div>
  );
}
