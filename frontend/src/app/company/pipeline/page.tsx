"use client";
/**
 * Company Pipeline — review candidates and run the hiring workflow.
 *
 * This is the employer side of ONE shared application lifecycle: decisions
 * move the same state machine the jobseeker sees, offers sync to the
 * candidate's Offer Center, and document access always requires candidate
 * authorization (requests show here as pending until the candidate approves).
 */
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { api } from "@/lib/api/session";
import {
  ApplicationReview,
  CompanyApplication,
  CompanyOffer,
  DocumentRequestRow,
} from "@/lib/api/types";
import { useOrg } from "@/context/OrgContext";
const cardCls =
  "rounded-xl border border-neutral-200 bg-white p-5 dark:border-neutral-800 dark:bg-neutral-900";

const LIVE_STATUSES = new Set([
  "applied",
  "application_received",
  "screening",
  "assessment",
  "interview",
  "offer",
  "on_hold",
]);

export default function CompanyPipeline() {
  const router = useRouter();
  const { organizationId } = useOrg();
  const [orgId, setOrgId] = useState("");
  const [apps, setApps] = useState<CompanyApplication[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [review, setReview] = useState<ApplicationReview | null>(null);
  const [docRequests, setDocRequests] = useState<DocumentRequestRow[]>([]);
  const [offers, setOffers] = useState<CompanyOffer[]>([]);
  const [filter, setFilter] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [form, setForm] = useState({
    note: "",
    when: "",
    interviewer: "",
    duration: "45",
    docType: "",
    purpose: "",
    salary: "",
    currency: "USD",
    startDate: "",
    terms: "",
  });
  const [openPanel, setOpenPanel] = useState("");

  const load = useCallback(
    async (id: string) => {
      const suffix = filter ? `?status=${encodeURIComponent(filter)}` : "";
      const [rows, docRows, offerRows] = await Promise.all([
        api.get<CompanyApplication[]>(`/company/${id}/applications${suffix}`),
        api.get<DocumentRequestRow[]>(`/company/${id}/document-requests`),
        api.get<CompanyOffer[]>(`/company/${id}/offers`),
      ]);
      setApps(rows);
      setDocRequests(docRows);
      setOffers(offerRows);
    },
    [filter]
  );

  useEffect(() => {
    if (!organizationId) {
      router.push("/company");
      return;
    }
    setOrgId(organizationId);
    load(organizationId).catch((e) => setError(String((e as Error).message ?? e)));
  }, [router, load, organizationId]);

  async function selectApp(app: CompanyApplication) {
    setSelectedId(app.id);
    setOpenPanel("");
    setError("");
    setReview(null);
    try {
      setReview(
        await api.get<ApplicationReview>(
          `/company/${orgId}/applications/${app.id}`
        )
      );
    } catch (e) {
      setError(String((e as Error).message ?? e));
    }
  }

  async function run(path: string, body?: unknown, then?: () => void) {
    setBusy(true);
    setError("");
    try {
      await api.post(path, body);
      await load(orgId);
      if (selectedId) {
        const app = apps.find((a) => a.id === selectedId);
        if (app) await selectApp(app);
      }
      then?.();
    } catch (e) {
      setError(String((e as Error).message ?? e));
    } finally {
      setBusy(false);
    }
  }

  async function decide(action: string) {
    if (!selectedId) return;
    await run(
      `/company/${orgId}/applications/${selectedId}/decision`,
      { action, note: form.note.trim() || null },
      () => setForm((f) => ({ ...f, note: "" }))
    );
  }

  async function scheduleInterview() {
    if (!selectedId || !form.when) return;
    await run(
      `/company/${orgId}/interviews`,
      {
        application_id: selectedId,
        scheduled_at: new Date(form.when).toISOString(),
        duration_minutes: Number(form.duration) || 45,
        mode: "video",
        interviewer_name: form.interviewer.trim() || null,
      },
      () => {
        setForm((f) => ({ ...f, when: "", interviewer: "" }));
        setOpenPanel("");
      }
    );
  }

  async function requestDocument() {
    if (!selectedId || !form.docType) return;
    await run(
      `/company/${orgId}/document-requests`,
      {
        application_id: selectedId,
        document_type: form.docType.trim(),
        purpose: form.purpose.trim() || null,
      },
      () => {
        setForm((f) => ({ ...f, docType: "", purpose: "" }));
        setOpenPanel("");
      }
    );
  }

  async function createOffer() {
    if (!selectedId) return;
    await run(
      `/company/${orgId}/offers`,
      {
        application_id: selectedId,
        salary_amount: form.salary ? Number(form.salary) : null,
        salary_currency: form.currency,
        start_date: form.startDate || null,
        terms_summary: form.terms.trim() || null,
        expires_days: 7,
      },
      () => {
        setForm((f) => ({ ...f, salary: "", startDate: "", terms: "" }));
        setOpenPanel("");
      }
    );
  }

  async function sendOffer(offerId: string) {
    await run(`/company/${orgId}/offers/${offerId}/send`);
  }

  if (error && apps.length === 0) {
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

  const selected = review?.application
    ? { ...review.application, candidate_name: apps.find((a) => a.id === selectedId)?.candidate_name ?? "Candidate" }
    : null;

  return (
    <div className="space-y-6">
      <section className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-sm text-neutral-400">Applications across your jobs</p>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight">
            Candidate pipeline
          </h1>
        </div>
        <div className="flex items-center gap-2 text-sm">
          <span className="text-neutral-400">Filter</span>
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="rounded-lg border border-neutral-300 bg-white px-3 py-1.5 text-sm dark:border-neutral-700 dark:bg-neutral-900"
          >
            <option value="">All statuses</option>
            {[
              "applied",
              "application_received",
              "screening",
              "assessment",
              "interview",
              "offer",
              "accepted",
              "rejected",
              "withdrawn",
              "on_hold",
            ].map((s) => (
              <option key={s} value={s}>
                {s.replace("_", " ")}
              </option>
            ))}
          </select>
        </div>
      </section>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-900 dark:bg-red-950 dark:text-red-300">
          {error}
        </div>
      )}

      {apps.length === 0 && (
        <div className={cardCls}>
          <p className="text-sm text-neutral-400">
            {filter
              ? "No applications in this status."
              : "No applications yet. Published jobs appear to jobseekers and matching is automatic."}
          </p>
        </div>
      )}

      <section className="space-y-2">
        {apps.map((app) => {
          const active = app.id === selectedId;
          return (
            <button
              key={app.id}
              onClick={() => selectApp(app)}
              className={`w-full rounded-xl border bg-white px-4 py-3 text-left text-sm hover:border-indigo-400 dark:bg-neutral-900 ${
                active
                  ? "border-indigo-500 ring-1 ring-indigo-500 dark:border-indigo-500"
                  : "border-neutral-200 dark:border-neutral-800"
              }`}
            >
              <div className="flex items-center justify-between gap-4">
                <div className="min-w-0">
                  <p className="truncate font-medium">{app.candidate_name}</p>
                  <p className="truncate text-xs text-neutral-400">
                    {app.job_title ?? "Opportunity"}
                  </p>
                </div>
                <div className="flex shrink-0 items-center gap-3 text-xs text-neutral-400">
                  {app.applied_at && (
                    <span>{new Date(app.applied_at).toLocaleDateString()}</span>
                  )}
                  <span className="rounded-full bg-neutral-100 px-2 py-0.5 capitalize text-neutral-600 dark:bg-neutral-800 dark:text-neutral-300">
                    {app.status.replace("_", " ")}
                  </span>
                </div>
              </div>
            </button>
          );
        })}
      </section>

      {/* Review detail */}
      {selected && review && (
        <section className={`${cardCls} space-y-5`}>
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h2 className="text-lg font-semibold">{selected.candidate_name}</h2>
              <p className="text-sm text-neutral-400">
                {selected.job_id ? review.job?.title ?? "Job" : "Opportunity"} ·{" "}
                <span className="capitalize">{selected.status.replace("_", " ")}</span>
                {review.application.applied_at &&
                  ` · applied ${new Date(review.application.applied_at).toLocaleDateString()}`}
              </p>
            </div>
            <div className="flex items-center gap-2 text-sm">
              <button
                disabled={busy}
                onClick={() => decide("advance")}
                className="rounded-lg bg-indigo-600 px-3 py-1.5 font-medium text-white hover:bg-indigo-500 disabled:opacity-50"
              >
                Advance
              </button>
              <button
                disabled={busy}
                onClick={() => decide("hold")}
                className="rounded-lg border border-neutral-300 px-3 py-1.5 text-neutral-600 hover:bg-neutral-50 dark:border-neutral-700 dark:text-neutral-300 dark:hover:bg-neutral-800"
              >
                Hold
              </button>
              <button
                disabled={busy}
                onClick={() => decide("reject")}
                className="rounded-lg border border-red-300 px-3 py-1.5 text-red-600 hover:bg-red-50 dark:border-red-900 dark:text-red-400 dark:hover:bg-red-950"
              >
                Reject
              </button>
            </div>
          </div>

          <input
            className={inputCls}
            placeholder="Optional note on this decision (audited)"
            value={form.note}
            onChange={(e) => setForm({ ...form, note: e.target.value })}
          />

          {/* Candidate snapshot — progressive disclosure */}
          {review.candidate && (
            <div className="grid gap-4 md:grid-cols-2">
              <div className="rounded-lg border border-neutral-200 p-4 dark:border-neutral-800">
                <h3 className="text-xs uppercase tracking-wide text-neutral-400">
                  Candidate snapshot
                </h3>
                <p className="mt-2 text-sm text-neutral-600 dark:text-neutral-300">
                  {LIVE_STATUSES.has(selected.status)
                    ? "Professional summary + skills visible at this stage. Work ID documents require candidate authorization."
                    : "Candidate summary"}
                </p>
                <div className="mt-3 flex flex-wrap gap-1.5">
                  {review.candidate.skills.length === 0 && (
                    <span className="text-xs text-neutral-400">No skills on record</span>
                  )}
                  {review.candidate.skills.slice(0, 10).map((s) => (
                    <span
                      key={`${s.name}-${s.level}`}
                      className="rounded-full bg-neutral-100 px-2 py-0.5 text-xs capitalize text-neutral-600 dark:bg-neutral-800 dark:text-neutral-300"
                    >
                      {s.name}
                      {s.level ? ` · ${s.level}` : ""}
                    </span>
                  ))}
                </div>
                <div className="mt-3 space-y-1 text-xs text-neutral-400">
                  <p>Disclosure:</p>
                  {Object.entries(review.candidate.disclosure).map(([scope, on]) => (
                    <p key={scope} className="capitalize">
                      {scope.replace(/_/g, " ")}:{" "}
                      <span className={on ? "text-emerald-600" : "text-neutral-500"}>
                        {on ? "shared" : "not shared"}
                      </span>
                    </p>
                  ))}
                </div>
              </div>
              <div className="rounded-lg border border-neutral-200 p-4 dark:border-neutral-800">
                <h3 className="text-xs uppercase tracking-wide text-neutral-400">
                  Timeline ({review.candidate.events.length})
                </h3>
                <div className="mt-2 space-y-1.5">
                  {review.candidate.events.length === 0 && (
                    <p className="text-xs text-neutral-400">No events yet.</p>
                  )}
                  {review.candidate.events.map((ev) => (
                    <p key={ev.id} className="text-xs text-neutral-500 dark:text-neutral-400">
                      <span className="capitalize">
                        {(ev.from_status ?? "started").replace(/_/g, " ")}
                      </span>{" "}
                      →{" "}
                      <span className="capitalize">{ev.to_status.replace(/_/g, " ")}</span>
                      <span className="text-neutral-400">
                        {" "}
                        · {new Date(ev.created_at).toLocaleString()}
                      </span>
                    </p>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Interview / offer status */}
          <div className="flex flex-wrap gap-4 text-xs">
            {review.interview && (
              <span className="rounded-lg bg-neutral-100 px-3 py-1.5 text-neutral-600 dark:bg-neutral-800 dark:text-neutral-300">
                Interview:{" "}
                {new Date(review.interview.scheduled_at).toLocaleString()} ·{" "}
                {review.interview.mode} ·{" "}
                {review.interview.interviewer_name ?? "no host"} —{" "}
                <span className="capitalize">
                  {review.interview.status.replace(/_/g, " ")}
                </span>
              </span>
            )}
            {review.offer && (
              <span className="rounded-lg bg-neutral-100 px-3 py-1.5 text-neutral-600 dark:bg-neutral-800 dark:text-neutral-300">
                Offer: {review.offer.salary_currency}{" "}
                {review.offer.salary_amount ?? "—"} ·{" "}
                <span className="capitalize">{review.offer.status}</span>
              </span>
            )}
          </div>

          {/* Workflow actions */}
          {LIVE_STATUSES.has(selected.status) && (
            <div className="flex flex-wrap gap-2 border-t border-neutral-100 pt-4 text-sm dark:border-neutral-800">
              <button
                onClick={() => setOpenPanel(openPanel === "interview" ? "" : "interview")}
                className="rounded-lg border border-neutral-300 px-3 py-1.5 text-neutral-600 hover:bg-neutral-50 dark:border-neutral-700 dark:text-neutral-300 dark:hover:bg-neutral-800"
              >
                Schedule interview
              </button>
              <button
                onClick={() => setOpenPanel(openPanel === "doc" ? "" : "doc")}
                className="rounded-lg border border-neutral-300 px-3 py-1.5 text-neutral-600 hover:bg-neutral-50 dark:border-neutral-700 dark:text-neutral-300 dark:hover:bg-neutral-800"
              >
                Request document
              </button>
              {!review.offer && (
                <button
                  onClick={() => setOpenPanel(openPanel === "offer" ? "" : "offer")}
                  className="rounded-lg bg-emerald-600 px-3 py-1.5 font-medium text-white hover:bg-emerald-500"
                >
                  Create offer
                </button>
              )}
              {review.offer && review.offer.status === "draft" && (
                <button
                  disabled={busy}
                  onClick={() => sendOffer(review.offer!.id)}
                  className="rounded-lg bg-emerald-600 px-3 py-1.5 font-medium text-white hover:bg-emerald-500 disabled:opacity-50"
                >
                  Send offer
                </button>
              )}
            </div>
          )}

          {openPanel === "interview" && (
            <div className="grid gap-3 rounded-lg border border-neutral-200 p-4 md:grid-cols-3 dark:border-neutral-800">
              <div>
                <label className={labelCls}>Date &amp; time *</label>
                <input
                  type="datetime-local"
                  className={inputCls}
                  value={form.when}
                  onChange={(e) => setForm({ ...form, when: e.target.value })}
                />
              </div>
              <div>
                <label className={labelCls}>Interviewer</label>
                <input
                  className={inputCls}
                  value={form.interviewer}
                  onChange={(e) => setForm({ ...form, interviewer: e.target.value })}
                />
              </div>
              <div>
                <label className={labelCls}>Duration (min)</label>
                <input
                  type="number"
                  className={inputCls}
                  value={form.duration}
                  onChange={(e) => setForm({ ...form, duration: e.target.value })}
                />
              </div>
              <div className="md:col-span-3">
                <button
                  disabled={busy || !form.when}
                  onClick={scheduleInterview}
                  className="rounded-lg bg-indigo-600 px-3 py-1.5 font-medium text-white hover:bg-indigo-500 disabled:opacity-50"
                >
                  Schedule (video)
                </button>
              </div>
            </div>
          )}

          {openPanel === "doc" && (
            <div className="grid gap-3 rounded-lg border border-neutral-200 p-4 md:grid-cols-3 dark:border-neutral-800">
              <div>
                <label className={labelCls}>Document type *</label>
                <input
                  className={inputCls}
                  value={form.docType}
                  onChange={(e) => setForm({ ...form, docType: e.target.value })}
                  placeholder="e.g. degree certificate"
                />
              </div>
              <div className="md:col-span-2">
                <label className={labelCls}>Why it&apos;s needed</label>
                <input
                  className={inputCls}
                  value={form.purpose}
                  onChange={(e) => setForm({ ...form, purpose: e.target.value })}
                />
              </div>
              <div className="md:col-span-3">
                <button
                  disabled={busy || !form.docType}
                  onClick={requestDocument}
                  className="rounded-lg bg-indigo-600 px-3 py-1.5 font-medium text-white hover:bg-indigo-500 disabled:opacity-50"
                >
                  Request (candidate must approve)
                </button>
              </div>
            </div>
          )}

          {openPanel === "offer" && (
            <div className="grid gap-3 rounded-lg border border-neutral-200 p-4 md:grid-cols-4 dark:border-neutral-800">
              <div>
                <label className={labelCls}>Salary *</label>
                <input
                  type="number"
                  className={inputCls}
                  value={form.salary}
                  onChange={(e) => setForm({ ...form, salary: e.target.value })}
                />
              </div>
              <div>
                <label className={labelCls}>Currency</label>
                <select
                  className={inputCls}
                  value={form.currency}
                  onChange={(e) => setForm({ ...form, currency: e.target.value })}
                >
                  <option>USD</option>
                  <option>AED</option>
                  <option>EUR</option>
                  <option>GBP</option>
                  <option>NGN</option>
                </select>
              </div>
              <div>
                <label className={labelCls}>Start date</label>
                <input
                  type="date"
                  className={inputCls}
                  value={form.startDate}
                  onChange={(e) => setForm({ ...form, startDate: e.target.value })}
                />
              </div>
              <div>
                <label className={labelCls}>Terms (short)</label>
                <input
                  className={inputCls}
                  value={form.terms}
                  onChange={(e) => setForm({ ...form, terms: e.target.value })}
                />
              </div>
              <div className="md:col-span-4">
                <button
                  disabled={busy}
                  onClick={createOffer}
                  className="rounded-lg bg-emerald-600 px-3 py-1.5 font-medium text-white hover:bg-emerald-500 disabled:opacity-50"
                >
                  Create draft offer
                </button>
                <p className="mt-1 text-xs text-neutral-400">
                  Offers start as drafts — you review and send them; the candidate
                  accepts or declines in their Offer Center.
                </p>
              </div>
            </div>
          )}

          {/* Document request state for this candidate */}
          {(() => {
            const mine = docRequests.filter((r) => r.application_id === selected.id);
            return (
              <div className="border-t border-neutral-100 pt-3 dark:border-neutral-800">
                <h3 className="text-xs uppercase tracking-wide text-neutral-400">
                  Document requests
                </h3>
                <div className="mt-2 flex flex-wrap gap-2 text-xs">
                  {mine.length === 0 && (
                    <span className="text-neutral-400">None for this candidate.</span>
                  )}
                  {mine.map((r) => (
                    <span
                      key={r.id}
                      className="rounded-lg bg-neutral-100 px-2.5 py-1 text-neutral-600 dark:bg-neutral-800 dark:text-neutral-300"
                    >
                      {r.document_type} —{" "}
                      <span className="capitalize">{r.status}</span>
                      {r.status === "pending" && " (awaiting candidate)"}
                    </span>
                  ))}
                </div>
              </div>
            );
          })()}

          {/* Offer state for this candidate */}
          {(() => {
            const mine = offers.filter((o) => o.application_id === selected.id);
            return (
              <div className="border-t border-neutral-100 pt-3 dark:border-neutral-800">
                <h3 className="text-xs uppercase tracking-wide text-neutral-400">
                  Offers
                </h3>
                <div className="mt-2 flex flex-wrap gap-2 text-xs">
                  {mine.length === 0 && (
                    <span className="text-neutral-400">None for this candidate.</span>
                  )}
                  {mine.map((o) => (
                    <span
                      key={o.id}
                      className="rounded-lg bg-neutral-100 px-2.5 py-1 text-neutral-600 dark:bg-neutral-800 dark:text-neutral-300"
                    >
                      {o.salary_currency} {o.salary_amount ?? "—"} —{" "}
                      <span className="capitalize">{o.status}</span>
                      {o.status === "draft" && (
                        <button
                          disabled={busy}
                          onClick={() => sendOffer(o.id)}
                          className="ml-2 font-medium text-emerald-600 hover:underline dark:text-emerald-400"
                        >
                          send
                        </button>
                      )}
                    </span>
                  ))}
                </div>
              </div>
            );
          })()}
        </section>
      )}
    </div>
  );
}
