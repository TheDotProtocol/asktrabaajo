"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

import {
  ErrorBanner,
  PageHeader,
  btnCls,
  cardCls,
  ghostBtnCls,
  inputCls,
  labelCls,
} from "@/components/candidate/ui";
import { useOrg } from "@/context/OrgContext";
import { api } from "@/lib/api/session";

const STEPS = ["Basics", "Role", "Requirements", "Location", "Compensation", "Review"] as const;

export default function NewJobPage() {
  const router = useRouter();
  const { organizationId } = useOrg();
  const [step, setStep] = useState(0);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState({
    title: "",
    summary: "",
    description: "",
    department: "",
    requirements: "",
    skills_required: "",
    preferred_skills: "",
    experience_level: "",
    seniority: "",
    employment_type: "full_time",
    work_mode: "hybrid",
    location: "",
    city: "",
    country: "",
    remote_eligible: false,
    salary_min: "",
    salary_max: "",
    salary_currency: "USD",
    openings_count: "1",
  });

  function set<K extends keyof typeof form>(key: K, value: (typeof form)[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  async function saveDraft(event: FormEvent) {
    event.preventDefault();
    if (!organizationId || !form.title.trim()) {
      setError("Title is required.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      await api.post(`/company/${organizationId}/jobs`, {
        title: form.title.trim(),
        summary: form.summary || null,
        description: form.description || null,
        department: form.department || null,
        requirements: form.requirements.split("\n").map((s) => s.trim()).filter(Boolean),
        skills_required: form.skills_required.split(",").map((s) => s.trim()).filter(Boolean),
        preferred_skills: form.preferred_skills.split(",").map((s) => s.trim()).filter(Boolean),
        experience_level: form.experience_level || null,
        seniority: form.seniority || null,
        employment_type: form.employment_type,
        work_mode: form.work_mode,
        location: form.location || null,
        city: form.city || null,
        country: form.country || null,
        remote_eligible: form.remote_eligible,
        salary_min: form.salary_min ? Number(form.salary_min) : null,
        salary_max: form.salary_max ? Number(form.salary_max) : null,
        salary_currency: form.salary_currency,
        openings_count: Math.max(1, Number(form.openings_count) || 1),
      });
      router.push("/company/jobs");
    } catch (e) {
      setError(String((e as Error).message ?? e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={saveDraft} className="space-y-6">
      <PageHeader
        kicker="Job creation"
        title="New job draft"
        subtitle="Saves as draft. Publishing is a separate, explicit action on the jobs list."
      />
      <ol className="flex flex-wrap gap-2">
        {STEPS.map((label, i) => (
          <li key={label}>
            <button type="button" className={i === step ? btnCls : ghostBtnCls} onClick={() => setStep(i)}>
              {label}
            </button>
          </li>
        ))}
      </ol>
      {error && <ErrorBanner message={error} />}
      <section className={`${cardCls} space-y-3`}>
        {step === 0 && (
          <>
            <Field label="Title" value={form.title} onChange={(v) => set("title", v)} required />
            <Field label="Department" value={form.department} onChange={(v) => set("department", v)} />
            <Field label="Summary" value={form.summary} onChange={(v) => set("summary", v)} area />
          </>
        )}
        {step === 1 && (
          <>
            <Field label="Description" value={form.description} onChange={(v) => set("description", v)} area />
            <Field label="Seniority" value={form.seniority} onChange={(v) => set("seniority", v)} />
            <Field label="Experience level" value={form.experience_level} onChange={(v) => set("experience_level", v)} />
            <label className={labelCls}>Employment type</label>
            <select className={inputCls} value={form.employment_type} onChange={(e) => set("employment_type", e.target.value)}>
              <option value="full_time">Full time</option>
              <option value="part_time">Part time</option>
              <option value="contract">Contract</option>
            </select>
          </>
        )}
        {step === 2 && (
          <>
            <Field label="Requirements (one per line)" value={form.requirements} onChange={(v) => set("requirements", v)} area />
            <Field label="Required skills (comma-separated)" value={form.skills_required} onChange={(v) => set("skills_required", v)} />
            <Field label="Preferred skills" value={form.preferred_skills} onChange={(v) => set("preferred_skills", v)} />
          </>
        )}
        {step === 3 && (
          <>
            <Field label="Location" value={form.location} onChange={(v) => set("location", v)} />
            <Field label="City" value={form.city} onChange={(v) => set("city", v)} />
            <Field label="Country" value={form.country} onChange={(v) => set("country", v)} />
            <label className={labelCls}>Work mode</label>
            <select className={inputCls} value={form.work_mode} onChange={(e) => set("work_mode", e.target.value)}>
              <option value="onsite">On-site</option>
              <option value="hybrid">Hybrid</option>
              <option value="remote">Remote</option>
            </select>
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={form.remote_eligible} onChange={(e) => set("remote_eligible", e.target.checked)} />
              Remote eligible
            </label>
          </>
        )}
        {step === 4 && (
          <>
            <Field label="Salary min" value={form.salary_min} onChange={(v) => set("salary_min", v)} />
            <Field label="Salary max" value={form.salary_max} onChange={(v) => set("salary_max", v)} />
            <Field label="Currency" value={form.salary_currency} onChange={(v) => set("salary_currency", v)} />
            <Field label="Openings" value={form.openings_count} onChange={(v) => set("openings_count", v)} />
          </>
        )}
        {step === 5 && (
          <dl className="space-y-2 text-sm">
            <div className="flex justify-between gap-4"><dt className="text-[#9ca3af]">Title</dt><dd>{form.title || "—"}</dd></div>
            <div className="flex justify-between gap-4"><dt className="text-[#9ca3af]">Department</dt><dd>{form.department || "—"}</dd></div>
            <div className="flex justify-between gap-4"><dt className="text-[#9ca3af]">Mode</dt><dd>{form.work_mode}</dd></div>
            <p className="text-xs text-[#6b7280]">This will save as a draft. It will not appear in the candidate catalogue until you publish it.</p>
          </dl>
        )}
      </section>
      <div className="flex flex-wrap gap-2">
        {step > 0 && (
          <button type="button" className={ghostBtnCls} onClick={() => setStep((s) => s - 1)}>Back</button>
        )}
        {step < STEPS.length - 1 && (
          <button type="button" className={btnCls} onClick={() => setStep((s) => s + 1)}>Next</button>
        )}
        <button type="submit" className={btnCls} disabled={busy}>
          {busy ? "Saving…" : "Save draft"}
        </button>
      </div>
    </form>
  );
}

function Field({
  label,
  value,
  onChange,
  area,
  required,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  area?: boolean;
  required?: boolean;
}) {
  return (
    <div>
      <label className={labelCls}>{label}</label>
      {area ? (
        <textarea className={inputCls} rows={4} value={value} required={required} onChange={(e) => onChange(e.target.value)} />
      ) : (
        <input className={inputCls} value={value} required={required} onChange={(e) => onChange(e.target.value)} />
      )}
    </div>
  );
}
