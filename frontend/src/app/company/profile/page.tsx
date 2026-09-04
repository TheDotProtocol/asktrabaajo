"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";

import {
  EmptyState,
  ErrorBanner,
  LoadingState,
  PageHeader,
  StatusPill,
  btnCls,
  cardCls,
  inputCls,
  labelCls,
} from "@/components/candidate/ui";
import { useOrg } from "@/context/OrgContext";
import { api } from "@/lib/api/session";
import { CompanyJob, CompanyProfile } from "@/lib/api/types";

const FIELDS: { key: keyof CompanyProfile; label: string }[] = [
  { key: "display_name", label: "Display name" },
  { key: "legal_name", label: "Legal name" },
  { key: "industry", label: "Industry" },
  { key: "sector", label: "Sector" },
  { key: "website_url", label: "Website" },
  { key: "company_size", label: "Company size" },
  { key: "company_type", label: "Company type" },
  { key: "country", label: "Country (HQ / office)" },
  { key: "city", label: "City (HQ / office)" },
  { key: "contact_name", label: "Hiring contact name" },
  { key: "contact_email", label: "Hiring contact email" },
];

export default function CompanyProfilePage() {
  const { organizationId } = useOrg();
  const [profile, setProfile] = useState<CompanyProfile | null>(null);
  const [jobs, setJobs] = useState<CompanyJob[]>([]);
  const [form, setForm] = useState<Record<string, string>>({});
  const [description, setDescription] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const load = useCallback(async () => {
    if (!organizationId) return;
    try {
      const [p, j] = await Promise.all([
        api.get<CompanyProfile>(`/company/${organizationId}/profile`),
        api.get<CompanyJob[]>(`/company/${organizationId}/jobs`).catch(() => []),
      ]);
      setProfile(p);
      setJobs(j);
      setForm(
        Object.fromEntries(
          FIELDS.map(({ key }) => [key, (p[key] as string | null) ?? ""])
        )
      );
      setDescription(p.description ?? "");
      setError("");
    } catch (e) {
      setError(String((e as Error).message ?? e));
    }
  }, [organizationId]);

  useEffect(() => {
    void load();
  }, [load]);

  async function save(event: FormEvent) {
    event.preventDefault();
    if (!organizationId) return;
    try {
      await api.patch(`/company/${organizationId}/profile`, {
        ...form,
        description,
      });
      setNotice("Profile saved. Only members with company-profile permission can change this.");
      await load();
    } catch (e) {
      setError(String((e as Error).message ?? e));
    }
  }

  if (!organizationId) {
    return <EmptyState title="Select an organization" body="Use the switcher in the sidebar." actionHref="/company" actionLabel="Command center" />;
  }
  if (error && !profile) return <ErrorBanner message={error} onRetry={() => void load()} />;
  if (!profile) return <LoadingState />;

  const departments = Array.from(new Set(jobs.map((j) => j.department).filter(Boolean))) as string[];

  return (
    <div className="space-y-8">
      <PageHeader
        kicker="Planning"
        title="Company profile"
        subtitle="Canonical company fields only. Mission, culture, and media galleries are not first-class APIs yet — they are not invented here."
        actions={<StatusPill status={profile.verification_status} />}
      />
      {error && <ErrorBanner message={error} />}
      {notice && <p className="text-sm text-emerald-400">{notice}</p>}

      <form onSubmit={save} className={`${cardCls} grid gap-3 sm:grid-cols-2`}>
        {FIELDS.map(({ key, label }) => (
          <div key={key}>
            <label className={labelCls}>{label}</label>
            <input
              className={inputCls}
              value={form[key] ?? ""}
              onChange={(e) => setForm((prev) => ({ ...prev, [key]: e.target.value }))}
            />
          </div>
        ))}
        <div className="sm:col-span-2">
          <label className={labelCls}>Description</label>
          <textarea className={inputCls} rows={4} value={description} onChange={(e) => setDescription(e.target.value)} />
        </div>
        <div className="sm:col-span-2">
          <button type="submit" className={btnCls}>Save profile</button>
        </div>
      </form>

      <section className={cardCls}>
        <h2 className="text-sm font-semibold">Offices & departments</h2>
        <p className="mt-2 text-sm text-[#9ca3af]">
          There is no separate offices/departments catalog. HQ location is the profile city/country.
          Departments shown below are distinct values already stored on jobs.
        </p>
        <p className="mt-4 text-sm">
          Office: {[profile.city, profile.country].filter(Boolean).join(", ") || "Not set"}
        </p>
        {departments.length === 0 ? (
          <p className="mt-3 text-sm text-[#6b7280]">No departments on jobs yet. Add a department when creating a job.</p>
        ) : (
          <div className="mt-3 flex flex-wrap gap-2">
            {departments.map((d) => (
              <span key={d} className="rounded-full border border-[#23272a] px-3 py-1 text-xs">{d}</span>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
