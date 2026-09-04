"use client";

import { useEffect, useState } from "react";

import { ErrorBanner, LoadingState, PageHeader, cardCls } from "@/components/candidate/ui";
import { GovernmentSettings, governmentApi } from "@/lib/api/government";

export default function GovernmentSettingsPage() {
  const [data, setData] = useState<GovernmentSettings | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    governmentApi
      .settings()
      .then(setData)
      .catch((e) => setError(String((e as Error).message ?? e)));
  }, []);

  return (
    <div className="space-y-8">
      <PageHeader
        kicker="Settings"
        title="Government access"
        subtitle="This organization reads privacy-protected aggregates. It cannot look up people."
      />
      {error && <ErrorBanner message={error} />}
      {!data && !error && <LoadingState label="Loading settings…" />}
      {data && (
        <div className="grid gap-4 md:grid-cols-2">
          <div className={cardCls}>
            <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-[#9ca3af]">Privacy</p>
            <p className="mt-3 text-sm text-[#e5e7eb]">{data.privacy}</p>
            <p className="mt-2 text-sm text-[#9ca3af]">Threshold K = {data.privacy_threshold}</p>
            <p className="mt-2 text-sm text-[#9ca3af]">Freshness: {data.freshness.replaceAll("_", " ")}</p>
          </div>
          <div className={cardCls}>
            <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-[#9ca3af]">Boundaries</p>
            <ul className="mt-3 space-y-2 text-sm text-[#9ca3af]">
              <li>Individual lookup: {data.individual_lookup ? "enabled" : "disabled"}</li>
              <li>Person consent disclosure: {data.consent_disclosure}</li>
              <li>Investment workflows: {data.investment_workflows}</li>
              <li>Government ↔ industry outreach: {data.government_industry_outreach}</li>
            </ul>
          </div>
          <div className={`${cardCls} md:col-span-2`}>
            <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-[#9ca3af]">Memberships</p>
            <ul className="mt-3 space-y-2 text-sm">
              {data.memberships.map((row) => (
                <li key={row.organization_id}>
                  {row.organization_name} · {row.role.replaceAll("_", " ")}
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}
