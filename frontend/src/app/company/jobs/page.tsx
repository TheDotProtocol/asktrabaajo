"use client";
/**
 * Company Jobs — create, publish, pause and close job postings.
 *
 * Publishing maps the job into the ONE canonical Opportunity catalogue, so
 * jobseekers immediately discover it (publish -> opportunity sync on the
 * backend). Lifecycle statuses come from the API, never hard-coded here.
 */
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { api, getAccessToken } from "@/lib/api/session";
import { CompanyJob } from "@/lib/api/types";

const ORG_KEY = "asktrabaajo_org_id";
const cardCls =
  "rounded-xl border border-neutral-200 bg-white p-5 dark:border-neutral-800 dark:bg-neutral-900";

const STATUS_STYLE: Record<string, string> = {
  draft: "bg-neutral-100 text-neutral-600 dark:bg-neutral-800 dark:text-neutral-300",
  published: "bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300",
  paused: "bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300",
  closed: "bg-neutral-200 text-neutral-500 dark:bg-neutral-800 dark:text-neutral-400",
  archived: "bg-neutral-200 text-neutral-500 dark:bg-neutral-800 dark:text-neutral-400",
};

export default function CompanyJobs() {
  const router = useRouter();
  const [orgId, setOrgId] = useState("");
  const [orgName, setOrgName] = useState("");
  const [jobs, setJobs] = useState<CompanyJob[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    title: "",
    summary: "",
    location: "",
    work_mode: "hybrid",
    employment_type: "full_time",
    remote_eligible: false,
    salary_min: "",
    salary_max: "",
    salary_currency: "USD",
    skills_required: "",
    seniority: "",
    experience_level: "",
    openings_count: "1",
  });

  const load = useCallback(
    async (id: string) => {
      const [rows, dash] = await Promise.all([
        api.get<CompanyJob[]>(`/company/${id}/jobs`),
        api.get<{ organization: { name: string } }>(`/company/${id}/dashboard`),
      ]);
      setJobs(rows);
      setOrgName(dash.organization.name);
    },
    []
  );

  useEffect(() => {
    if (!getAccessToken()) {
      router.push("/id");
      return;
    }
    const id = window.localStorage.getItem(ORG_KEY) ?? "";
    if (!id) {
      router.push("/company");
      return;
    }
    setOrgId(id);
    load(id).catch((e) => setError(String((e as Error).message ?? e)));
  }, [router, load]);

  async function act(path: string, refresh = true) {
    setBusy(true);
    setError("");
    try {
      await api.post(path);
      if (refresh) await load(orgId);
    } catch (e) {
      setError(String((e as Error).message ?? e));
    } finally {
      setBusy(false);
    }
  }

  async function createJob() {
    if (!form.title.trim() || busy) return;
    setBusy(true);
    setError("");
    try {
      await api.post(`/company/${orgId}/jobs`, {
        title: form.title.trim(),
        summary: form.summary.trim() || null,
        location: form.location.trim() || null,
        work_mode: form.work_mode,
        employment_type: form.employment_type,
        remote_eligible: form.remote_eligible,
        salary_min: form.salary_min ? Number(form.salary_min) : null,
        salary_max: form.salary_max ? Number(form.salary_max) : null,
        salary_currency: form.salary_currency,
        skills_required: form.skills_required
          ? form.skills_required.split(",").map((s) => s.trim()).filter(Boolean)
          : [],
        seniority: form.seniority || null,
        experience_level: form.experience_level || null,
        openings_count: Math.max(1, Number(form.openings_count) || 1),
      });
      setForm({
        ...form,
        title: "",
        summary: "",
        skills_required: "",
      });
      setShowForm(false);
      await load(orgId);
    } catch (e) {
      setError(String((e as Error).message ?? e));
    } finally {
      setBusy(false);
    }
  }

  if (error && jobs.length === 0) {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50 p-5 text-sm text-red-700 dark:border-red-900 dark:bg-red-950 dark:text-red-300">
        {error} —{" "}
        <button onClick={() => load(orgId)} className="underline">
          retry
        </button>
      </div>
    );
  }

  const inputCls =
    "w-full rounded-lg border border-neutral-300 bg-white px-3 py-2 text-sm dark:border-neutral-700 dark:bg-neutral-900";
  const labelCls = "text-xs font-medium text-neutral-500 dark:text-neutral-400";

  return (
    <div className="space-y-6">
      <section className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-sm text-neutral-400">{orgName || "Company"}</p>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight">Jobs</h1>
        </div>
        <button
          onClick={() => setShowForm((v) => !v)}
          className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500"
        >
          {showForm ? "Cancel" : "Create job"}
        </button>
      </section>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-900 dark:bg-red-950 dark:text-red-300">
          {error}
        </div>
      )}

      {showForm && (
        <section className={cardCls}>
          <h2 className="text-sm font-semibold">New job posting</h2>
          <div className="mt-4 grid gap-4 md:grid-cols-2">
            <div className="md:col-span-2">
              <label className={labelCls}>Title *</label>
              <input
                className={inputCls}
                value={form.title}
                onChange={(e) => setForm({ ...form, title: e.target.value })}
                placeholder="e.g. Senior Frontend Engineer"
              />
            </div>
            <div className="md:col-span-2">
              <label className={labelCls}>Summary</label>
              <textarea
                className={inputCls}
                rows={3}
                value={form.summary}
                onChange={(e) => setForm({ ...form, summary: e.target.value })}
                placeholder="One-paragraph description jobseekers see first"
              />
            </div>
            <div>
              <label className={labelCls}>Location</label>
              <input
                className={inputCls}
                value={form.location}
                onChange={(e) => setForm({ ...form, location: e.target.value })}
                placeholder="Dubai, UAE"
              />
            </div>
            <div>
              <label className={labelCls}>Work mode</label>
              <select
                className={inputCls}
                value={form.work_mode}
                onChange={(e) => setForm({ ...form, work_mode: e.target.value })}
              >
                <option value="onsite">On-site</option>
                <option value="hybrid">Hybrid</option>
                <option value="remote">Remote</option>
              </select>
            </div>
            <div>
              <label className={labelCls}>Employment type</label>
              <select
                className={inputCls}
                value={form.employment_type}
                onChange={(e) =>
                  setForm({ ...form, employment_type: e.target.value })
                }
              >
                <option value="full_time">Full time</option>
                <option value="part_time">Part time</option>
                <option value="contract">Contract</option>
                <option value="internship">Internship</option>
              </select>
            </div>
            <div>
              <label className={labelCls}>Seniority</label>
              <select
                className={inputCls}
                value={form.seniority}
                onChange={(e) => setForm({ ...form, seniority: e.target.value })}
              >
                <option value="">Any</option>
                <option value="entry">Entry</option>
                <option value="junior">Junior</option>
                <option value="mid">Mid</option>
                <option value="senior">Senior</option>
                <option value="lead">Lead</option>
              </select>
            </div>
            <div>
              <label className={labelCls}>Salary min ({form.salary_currency})</label>
              <input
                className={inputCls}
                type="number"
                value={form.salary_min}
                onChange={(e) => setForm({ ...form, salary_min: e.target.value })}
              />
            </div>
            <div>
              <label className={labelCls}>Salary max</label>
              <input
                className={inputCls}
                type="number"
                value={form.salary_max}
                onChange={(e) => setForm({ ...form, salary_max: e.target.value })}
              />
            </div>
            <div className="flex items-end gap-4">
              <div className="flex-1">
                <label className={labelCls}>Currency</label>
                <select
                  className={inputCls}
                  value={form.salary_currency}
                  onChange={(e) =>
                    setForm({ ...form, salary_currency: e.target.value })
                  }
                >
                  <option>USD</option>
                  <option>AED</option>
                  <option>EUR</option>
                  <option>GBP</option>
                  <option>NGN</option>
                  <option>KES</option>
                </select>
              </div>
              <label className="flex items-center gap-2 pb-2 text-sm">
                <input
                  type="checkbox"
                  checked={form.remote_eligible}
                  onChange={(e) =>
                    setForm({ ...form, remote_eligible: e.target.checked })
                  }
                />
                Remote
              </label>
            </div>
            <div className="md:col-span-2">
              <label className={labelCls}>
                Required skills (comma separated)
              </label>
              <input
                className={inputCls}
                value={form.skills_required}
                onChange={(e) =>
                  setForm({ ...form, skills_required: e.target.value })
                }
                placeholder="React, TypeScript, AWS"
              />
            </div>
          </div>
          <button
            onClick={createJob}
            disabled={busy}
            className="mt-4 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500 disabled:opacity-50"
          >
            {busy ? "Creating…" : "Create draft job"}
          </button>
        </section>
      )}

      {jobs.length === 0 && !showForm && (
        <div className={cardCls}>
          <p className="text-sm text-neutral-400">
            No jobs yet. Create your first posting — publishing it opens the
            role to jobseeker discovery in the canonical opportunity catalogue.
          </p>
        </div>
      )}

      <section className="space-y-3">
        {jobs.map((job) => (
          <div key={job.id} className={cardCls}>
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <h3 className="font-medium">{job.title}</h3>
                  <span
                    className={`rounded-full px-2 py-0.5 text-xs capitalize ${STATUS_STYLE[job.status] ?? "bg-neutral-100 text-neutral-600"}`}
                  >
                    {job.status.replace("_", " ")}
                  </span>
                  {job.opportunity_id && (
                    <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-xs text-emerald-600 dark:bg-emerald-950 dark:text-emerald-300">
                      in catalogue
                    </span>
                  )}
                </div>
                <p className="mt-1 text-xs text-neutral-400">
                  {[job.department, job.location, job.work_mode]
                    .filter(Boolean)
                    .join(" · ")}
                  {job.salary_min != null &&
                    ` · ${job.salary_currency ?? ""} ${job.salary_min}${job.salary_max != null ? `–${job.salary_max}` : ""}`}
                </p>
                {job.skills_required && job.skills_required.length > 0 && (
                  <p className="mt-2 text-xs text-neutral-500 dark:text-neutral-400">
                    {job.skills_required.join(", ")}
                  </p>
                )}
              </div>
              <div className="flex shrink-0 items-center gap-2 text-sm">
                {job.status === "published" && (
                  <span className="text-xs text-neutral-400">
                    {job.applications_count} application
                    {job.applications_count === 1 ? "" : "s"}
                  </span>
                )}
                {(job.status === "draft" || job.status === "paused" || job.status === "pending_review") && (
                  <button
                    disabled={busy}
                    onClick={() => act(`/company/${orgId}/jobs/${job.id}/publish`)}
                    className="rounded-lg bg-emerald-600 px-3 py-1.5 font-medium text-white hover:bg-emerald-500 disabled:opacity-50"
                  >
                    Publish
                  </button>
                )}
                {job.status === "published" && (
                  <button
                    disabled={busy}
                    onClick={() => act(`/company/${orgId}/jobs/${job.id}/pause`)}
                    className="rounded-lg border border-neutral-300 px-3 py-1.5 text-neutral-600 hover:bg-neutral-50 dark:border-neutral-700 dark:text-neutral-300 dark:hover:bg-neutral-800"
                  >
                    Pause
                  </button>
                )}
                {job.status !== "closed" && job.status !== "archived" && (
                  <button
                    disabled={busy}
                    onClick={() => act(`/company/${orgId}/jobs/${job.id}/close`)}
                    className="rounded-lg border border-neutral-300 px-3 py-1.5 text-neutral-600 hover:bg-neutral-50 dark:border-neutral-700 dark:text-neutral-300 dark:hover:bg-neutral-800"
                  >
                    Close
                  </button>
                )}
              </div>
            </div>
          </div>
        ))}
      </section>
    </div>
  );
}
