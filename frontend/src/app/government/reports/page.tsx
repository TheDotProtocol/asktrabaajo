"use client";

import { useState } from "react";

import { ErrorBanner, PageHeader, cardCls } from "@/components/candidate/ui";
import { BucketList, FilterBar, PrivacyNote } from "@/components/government/IntelligenceUI";
import { GovernmentFilters, IntelligenceEnvelope, governmentApi } from "@/lib/api/government";

const KINDS = [
  ["workforce", "Workforce Report"],
  ["skills", "Skills Report"],
  ["regional", "Regional Workforce Report"],
  ["industry", "Industry Report"],
  ["hiring_demand", "Hiring Demand Report"],
  ["skill_gap", "Skill Gap Report"],
];

export default function GovernmentReportsPage() {
  const [kind, setKind] = useState("workforce");
  const [filters, setFilters] = useState<GovernmentFilters>({});
  const [data, setData] = useState<IntelligenceEnvelope | null>(null);
  const [error, setError] = useState("");
  const [exportNote, setExportNote] = useState("");

  async function run() {
    setError("");
    setExportNote("");
    try {
      setData(await governmentApi.report(kind, filters));
    } catch (e) {
      setError(String((e as Error).message ?? e));
    }
  }

  async function doExport() {
    setExportNote("");
    const scope = Object.entries(filters)
      .filter(([, value]) => value)
      .map(([key, value]) => `${key}=${value}`)
      .join(", ");
    const confirmed = window.confirm(
      [
        "Export aggregate intelligence only.",
        `DATA SCOPE: ${kind}`,
        "TIME PERIOD: current snapshot",
        `FILTERS: ${scope || "none"}`,
        "RECORD TYPE: aggregate cells (no person records)",
        "PRIVACY STATUS: k-threshold applied to person cohorts",
        "Continue?",
      ].join("\n"),
    );
    if (!confirmed) return;
    try {
      const out = await governmentApi.exportJson(kind, filters);
      setExportNote(`Export prepared: ${out.rows.length} aggregate rows. No person records.`);
    } catch (e) {
      setError(String((e as Error).message ?? e));
    }
  }

  return (
    <div className="space-y-8">
      <PageHeader
        kicker="Reports"
        title="Reproducible aggregate reports"
        subtitle="Reports are query results, not stored person snapshots. Exports contain only permitted aggregate cells."
      />
      <FilterBar onApply={setFilters} />
      <div className={`${cardCls} flex flex-wrap items-end gap-3`}>
        <label className="text-sm text-[#9ca3af]">
          Report
          <select
            className="mt-2 block rounded-md border border-[#23272a] bg-[#0b0c0d] px-3 py-2 text-white"
            value={kind}
            onChange={(e) => setKind(e.target.value)}
          >
            {KINDS.map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
        <button type="button" onClick={run} className="rounded-md bg-[#d4af37] px-4 py-2 text-sm font-semibold text-[#0b0c0d]">
          Generate
        </button>
        <button type="button" onClick={doExport} className="rounded-md border border-[#23272a] px-4 py-2 text-sm">
          Export JSON
        </button>
      </div>
      {error && <ErrorBanner message={error} />}
      {exportNote && <p className="text-sm text-[#d4af37]">{exportNote}</p>}
      {data && (
        <>
          <PrivacyNote data={data} />
          <p className="text-lg font-semibold">{data.title || kind}</p>
          <BucketList title="Aggregate cells" buckets={data.buckets || data.top_skills?.buckets || data.supply?.buckets} />
        </>
      )}
    </div>
  );
}
