"use client";

import { FormEvent, ReactNode, useState } from "react";

import { cardCls, inputCls, labelCls } from "@/components/candidate/ui";
import { Bucket, CohortCell, GovernmentFilters, IntelligenceEnvelope } from "@/lib/api/government";

export function PrivacyNote({ data }: { data?: IntelligenceEnvelope | null }) {
  return (
    <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-[#d4af37]">
      {data?.privacy || "Privacy-protected aggregate data. Individual records are not exposed."}
      {data?.generated_at ? ` · Live aggregate · ${new Date(data.generated_at).toLocaleString()}` : ""}
      {data?.privacy_threshold ? ` · K=${data.privacy_threshold}` : ""}
    </p>
  );
}

export function MetricCard({ title, cell }: { title: string; cell?: CohortCell }) {
  const suppressed = !cell || cell.status !== "ok" || cell.value == null;
  return (
    <div className={cardCls}>
      <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-[#9ca3af]">{title}</p>
      <p className="mt-3 text-3xl font-semibold tracking-tight">
        {suppressed ? "—" : cell.value}
      </p>
      <p className="mt-2 text-xs text-[#6b7280]">
        {suppressed ? (cell?.label || cell?.status || "No sufficient data").replaceAll("_", " ") : "Observed count"}
      </p>
    </div>
  );
}

export function BucketList({
  title,
  buckets,
  empty,
}: {
  title: string;
  buckets?: Bucket[];
  empty?: string;
}) {
  return (
    <div className={cardCls}>
      <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-[#9ca3af]">{title}</p>
      {!buckets?.length ? (
        <p className="mt-4 text-sm text-[#6b7280]">{empty || "No sufficient data"}</p>
      ) : (
        <ul className="mt-4 divide-y divide-[#23272a]">
          {buckets.map((bucket) => (
            <li key={bucket.key} className="flex items-center justify-between py-2.5 text-sm">
              <span className="text-[#e5e7eb]">{bucket.key}</span>
              <span className="font-mono text-[#9ca3af]">
                {bucket.status === "ok" && bucket.value != null
                  ? bucket.value
                  : bucket.status === "suppressed"
                    ? "SUPPRESSED"
                    : "INSUFFICIENT"}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export function FilterBar({
  onApply,
  children,
}: {
  onApply: (filters: GovernmentFilters) => void;
  children?: ReactNode;
}) {
  const [country, setCountry] = useState("");
  const [state, setState] = useState("");
  const [city, setCity] = useState("");
  const [industry, setIndustry] = useState("");
  const [skill, setSkill] = useState("");

  function submit(event: FormEvent) {
    event.preventDefault();
    onApply({
      country: country.trim() || undefined,
      state_province: state.trim() || undefined,
      city: city.trim() || undefined,
      industry: industry.trim() || undefined,
      skill: skill.trim() || undefined,
    });
  }

  return (
    <form onSubmit={submit} className={`${cardCls} grid gap-4 md:grid-cols-6`}>
      <label className={`${labelCls} flex flex-col gap-2`}>
        Country
        <input className={inputCls} value={country} onChange={(e) => setCountry(e.target.value)} placeholder="DEV" />
      </label>
      <label className={`${labelCls} flex flex-col gap-2`}>
        State / province
        <input className={inputCls} value={state} onChange={(e) => setState(e.target.value)} placeholder="Optional" />
      </label>
      <label className={`${labelCls} flex flex-col gap-2`}>
        City
        <input className={inputCls} value={city} onChange={(e) => setCity(e.target.value)} placeholder="Development City" />
      </label>
      <label className={`${labelCls} flex flex-col gap-2`}>
        Industry
        <input className={inputCls} value={industry} onChange={(e) => setIndustry(e.target.value)} placeholder="Technology" />
      </label>
      <label className={`${labelCls} flex flex-col gap-2`}>
        Skill
        <input className={inputCls} value={skill} onChange={(e) => setSkill(e.target.value)} placeholder="Python" />
      </label>
      <div className="flex items-end gap-3">
        <button type="submit" className="rounded-md bg-[#d4af37] px-4 py-2 text-sm font-semibold text-[#0b0c0d]">
          Apply filters
        </button>
        {children}
      </div>
    </form>
  );
}
