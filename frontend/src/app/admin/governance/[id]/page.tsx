"use client";
/**
 * Governance report detail (Phase 9 proof).
 *
 * Moderator surface: report metadata, internal notes, and the audit timeline.
 * It never fabricates access to the target's Work ID — inspecting a private
 * Work ID requires a separate platform permission with a legitimate purpose.
 */
import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";

import { api } from "@/lib/api/session";
import { GovernanceReportRow } from "@/lib/api/types";

const statusStyle: Record<string, string> = {
  open: "bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-300",
  in_review: "bg-indigo-100 text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300",
  assigned: "bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300",
  resolved: "bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-400",
  closed: "bg-neutral-100 text-neutral-600 dark:bg-neutral-800 dark:text-neutral-300",
};

const severityStyle: Record<string, string> = {
  low: "bg-neutral-100 text-neutral-600 dark:bg-neutral-800 dark:text-neutral-300",
  medium: "bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-300",
  high: "bg-orange-100 text-orange-700 dark:bg-orange-950 dark:text-orange-300",
  critical: "bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300",
};

const cardCls =
  "rounded-xl border border-neutral-200 bg-white p-5 dark:border-neutral-800 dark:bg-neutral-900";
const primaryBtn =
  "rounded bg-indigo-500 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-600 disabled:opacity-40";
const ghostBtn =
  "rounded border border-neutral-300 px-3 py-1.5 text-sm text-neutral-600 hover:border-indigo-400 dark:border-neutral-700 dark:text-neutral-300";
const inputCls =
  "w-full rounded border border-neutral-300 bg-white px-3 py-2 text-sm dark:border-neutral-700 dark:bg-neutral-900";

function fmt(ts: string | null): string {
  if (!ts) return "";
  try {
    return new Date(ts).toLocaleString(undefined, {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return ts;
  }
}

function titleCase(value: string): string {
  return value
    .split(/[_\s]+/)
    .map((w) => (w ? w[0].toUpperCase() + w.slice(1) : w))
    .join(" ");
}

export default function GovernanceReportDetailPage() {
  const params = useParams();
  const reportId = String(params?.id ?? "");
  const [report, setReport] = useState<GovernanceReportRow | null>(null);
  const [note, setNote] = useState("");
  const [resolution, setResolution] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [forbidden, setForbidden] = useState(false);

  const load = useCallback(async () => {
    if (!reportId) return;
    setError("");
    try {
      const r = await api.get<GovernanceReportRow>(`/governance/reports/${reportId}`);
      setReport(r);
    } catch (e) {
      const err = e as { status?: number; message?: string };
      if (err.status === 403) setForbidden(true);
      setError(String(err.message ?? e));
    }
  }, [reportId]);

  useEffect(() => {
    void load();
  }, [load]);

  if (forbidden) {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50 p-6 text-sm text-red-700 dark:border-red-900 dark:bg-red-950 dark:text-red-300">
        Your account does not hold a platform governance role.
      </div>
    );
  }

  if (!report) {
    return (
      <p className="text-sm text-neutral-500">
        {error ? `Could not load report: ${error}` : "Loading report…"}
      </p>
    );
  }

  const isResolved = report.status === "resolved" || report.status === "closed";

  async function run(action: () => Promise<unknown>) {
    setBusy(true);
    setError("");
    try {
      await action();
      await load();
    } catch (e) {
      setError(String((e as Error).message ?? e));
    } finally {
      setBusy(false);
    }
  }

  async function changeStatus(status: string) {
    await run(() =>
      api.patch(`/governance/reports/${reportId}/status`, { status })
    );
  }

  async function assignToMe() {
    await run(() => api.post(`/governance/reports/${reportId}/assign`, {}));
  }

  async function addNote() {
    const body = note.trim();
    if (!body) return;
    await run(async () => {
      await api.post(`/governance/reports/${reportId}/notes`, { body });
      setNote("");
    });
  }

  async function resolve() {
    const body = resolution.trim();
    if (body.length < 10) {
      setError("Resolution must be at least 10 characters.");
      return;
    }
    await run(async () => {
      await api.post(`/governance/reports/${reportId}/resolve`, { resolution: body });
      setResolution("");
    });
  }

  async function reopen() {
    await run(() => api.post(`/governance/reports/${reportId}/reopen`));
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start gap-3">
        <Link
          href="/admin/governance"
          className="mt-1 text-sm text-neutral-500 hover:text-neutral-800 dark:hover:text-neutral-200"
        >
          ← Queue
        </Link>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span
              className={`rounded px-1.5 py-0.5 text-xs font-medium ${statusStyle[report.status] ?? ""}`}
            >
              {titleCase(report.status)}
            </span>
            <span
              className={`rounded px-1.5 py-0.5 text-xs font-medium ${severityStyle[report.severity] ?? ""}`}
            >
              {titleCase(report.severity)}
            </span>
            <span className="rounded bg-neutral-100 px-1.5 py-0.5 text-xs text-neutral-600 dark:bg-neutral-800 dark:text-neutral-300">
              {titleCase(report.category)}
            </span>
            {report.reopened_count > 0 && (
              <span className="rounded bg-amber-100 px-1.5 py-0.5 text-xs text-amber-700 dark:bg-amber-950 dark:text-amber-300">
                Reopened ×{report.reopened_count}
              </span>
            )}
          </div>
          <h1 className="mt-2 text-xl font-semibold tracking-tight">
            {titleCase(report.target_type)} report
          </h1>
          <p className="text-sm text-neutral-500">
            Filed {fmt(report.created_at)} ·{" "}
            {report.organization_name ?? "no organization"} · Target{" "}
            <code className="rounded bg-neutral-100 px-1 py-0.5 text-xs dark:bg-neutral-800">
              {report.target_id}
            </code>
          </p>
        </div>
      </div>

      {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}

      <div className="grid gap-4 lg:grid-cols-2">
        <div className={`${cardCls} space-y-4`}>
          <h2 className="text-sm font-semibold text-neutral-700 dark:text-neutral-200">
            Report
          </h2>
          <p className="text-sm leading-relaxed text-neutral-700 dark:text-neutral-300">
            {report.description}
          </p>
          {report.evidence_refs.length > 0 && (
            <div>
              <p className="text-xs font-medium text-neutral-500">Evidence references</p>
              <ul className="mt-1 space-y-1">
                {report.evidence_refs.map((ref, i) => (
                  <li key={i} className="text-xs text-neutral-600 dark:text-neutral-300">
                    <code className="rounded bg-neutral-100 px-1 py-0.5 dark:bg-neutral-800">
                      {ref.type}:{ref.id.slice(0, 12)}…
                    </code>
                    {ref.note ? ` — ${ref.note}` : ""}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {report.resolution && (
            <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800 dark:border-emerald-900 dark:bg-emerald-950 dark:text-emerald-300">
              <span className="font-medium">Resolution: </span>
              {report.resolution}
            </div>
          )}

          <div className="flex flex-wrap gap-2 border-t border-neutral-200 pt-4 dark:border-neutral-800">
            {!isResolved && (
              <button onClick={assignToMe} disabled={busy} className={ghostBtn}>
                Assign to me
              </button>
            )}
            {report.status !== "in_review" && !isResolved && (
              <button
                onClick={() => changeStatus("in_review")}
                disabled={busy}
                className={ghostBtn}
              >
                Mark in review
              </button>
            )}
            {isResolved && (
              <button onClick={reopen} disabled={busy} className={ghostBtn}>
                Reopen
              </button>
            )}
          </div>
          {!isResolved && (
            <div className="flex flex-wrap items-end gap-2">
              <div className="flex-1">
                <label className="text-xs font-medium text-neutral-500">
                  Resolution
                </label>
                <textarea
                  value={resolution}
                  onChange={(e) => setResolution(e.target.value)}
                  rows={2}
                  placeholder="Record the resolution action…"
                  className={`${inputCls} mt-1`}
                />
              </div>
              <button onClick={resolve} disabled={busy} className={primaryBtn}>
                Resolve
              </button>
            </div>
          )}
        </div>

        <div className={`${cardCls} space-y-4`}>
          <h2 className="text-sm font-semibold text-neutral-700 dark:text-neutral-200">
            Internal notes
          </h2>
          {(report.notes ?? []).length === 0 && (
            <p className="text-sm text-neutral-500">No internal notes yet.</p>
          )}
          <ul className="space-y-2">
            {(report.notes ?? []).map((n) => (
              <li
                key={n.id}
                className="rounded-lg bg-neutral-50 p-3 text-sm dark:bg-neutral-950"
              >
                <p className="text-neutral-700 dark:text-neutral-300">{n.body}</p>
                <p className="mt-1 text-xs text-neutral-400">
                  {n.author_user_id.slice(0, 8)}… · {fmt(n.created_at)}
                </p>
              </li>
            ))}
          </ul>
          <div className="flex gap-2">
            <input
              value={note}
              onChange={(e) => setNote(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") void addNote();
              }}
              placeholder="Add an internal note…"
              className={inputCls}
            />
            <button onClick={addNote} disabled={busy || !note.trim()} className={primaryBtn}>
              Add
            </button>
          </div>
        </div>
      </div>

      <div className={`${cardCls} space-y-3`}>
        <h2 className="text-sm font-semibold text-neutral-700 dark:text-neutral-200">
          Audit timeline
        </h2>
        {(report.audit ?? []).length === 0 && (
          <p className="text-sm text-neutral-500">No governance actions recorded yet.</p>
        )}
        <ol className="space-y-0">
          {(report.audit ?? []).map((a, i) => (
            <li key={i} className="flex gap-3 text-sm">
              <div className="flex flex-col items-center">
                <span className="mt-1.5 h-2 w-2 rounded-full bg-indigo-400" />
                {i < (report.audit?.length ?? 0) - 1 && (
                  <span className="h-full w-px bg-neutral-200 dark:bg-neutral-800" />
                )}
              </div>
              <div className="pb-3">
                <p className="text-neutral-700 dark:text-neutral-300">
                  <code className="rounded bg-neutral-100 px-1 py-0.5 text-xs dark:bg-neutral-800">
                    {a.action}
                  </code>{" "}
                  {a.actor_id ? `by ${a.actor_id.slice(0, 8)}…` : ""}
                  <span className="text-neutral-400"> · {fmt(a.created_at)}</span>
                </p>
                {a.payload && Object.keys(a.payload).length > 0 && (
                  <p className="mt-0.5 text-xs text-neutral-500">
                    {JSON.stringify(a.payload)}
                  </p>
                )}
              </div>
            </li>
          ))}
        </ol>
      </div>
    </div>
  );
}
