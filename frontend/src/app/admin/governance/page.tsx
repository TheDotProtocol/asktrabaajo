"use client";
/**
 * Platform governance report queue (Phase 9 proof).
 *
 * Least-privilege by design: this screen renders report metadata, category,
 * severity, status and references — never the target's private Work ID data
 * or documents. Employers, recruiters, candidates and government roles get
 * 403 before reaching this page's data.
 */
import { useCallback, useEffect, useState } from "react";
import Link from "next/link";

import { api } from "@/lib/api/session";
import {
  GovernanceDashboard,
  GovernanceQueue,
  GovernanceReportRow,
} from "@/lib/api/types";

const STATUSES = ["open", "in_review", "assigned", "resolved", "closed"];
const SEVERITIES = ["low", "medium", "high", "critical"];

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
const selectCls =
  "rounded border border-neutral-300 bg-white px-2 py-1.5 text-sm dark:border-neutral-700 dark:bg-neutral-900";

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

export default function GovernanceQueuePage() {
  const [queue, setQueue] = useState<GovernanceQueue | null>(null);
  const [dash, setDash] = useState<GovernanceDashboard | null>(null);
  const [status, setStatus] = useState("");
  const [severity, setSeverity] = useState("");
  const [page, setPage] = useState(1);
  const [error, setError] = useState("");
  const [forbidden, setForbidden] = useState(false);

  const load = useCallback(async () => {
    setError("");
    const params = new URLSearchParams({ page: String(page), page_size: "25" });
    if (status) params.set("status", status);
    if (severity) params.set("severity", severity);
    try {
      const [q, d] = await Promise.all([
        api.get<GovernanceQueue>(`/governance/reports?${params.toString()}`),
        api.get<GovernanceDashboard>("/governance/dashboard"),
      ]);
      setQueue(q);
      setDash(d);
    } catch (e) {
      const err = e as { status?: number; message?: string };
      if (err.status === 403) setForbidden(true);
      setError(String(err.message ?? e));
    }
  }, [page, status, severity]);

  useEffect(() => {
    void load();
  }, [load]);

  if (forbidden) {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50 p-6 text-sm text-red-700 dark:border-red-900 dark:bg-red-950 dark:text-red-300">
        Your account does not hold a platform governance role. If you believe
        this is wrong, contact platform administration.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">Governance</h1>
        <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
          Platform report queue. References only — private Work ID data and
          documents are never surfaced here.
        </p>
      </div>

      {dash && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <div className={cardCls}>
            <div className="text-2xl font-semibold">{dash.total}</div>
            <div className="text-xs text-neutral-500">Total reports</div>
          </div>
          <div className={cardCls}>
            <div className="text-2xl font-semibold text-blue-600">{dash.open}</div>
            <div className="text-xs text-neutral-500">Open / in review</div>
          </div>
          <div className={cardCls}>
            <div className="text-2xl font-semibold text-orange-600">
              {(dash.by_severity.high ?? 0) + (dash.by_severity.critical ?? 0)}
            </div>
            <div className="text-xs text-neutral-500">High + critical</div>
          </div>
          <div className={cardCls}>
            <div className="text-2xl font-semibold text-emerald-600">
              {dash.by_status.resolved ?? 0}
            </div>
            <div className="text-xs text-neutral-500">Resolved</div>
          </div>
        </div>
      )}

      <div className={`${cardCls} space-y-4`}>
        <div className="flex flex-wrap items-center gap-2">
          <select
            value={status}
            onChange={(e) => {
              setStatus(e.target.value);
              setPage(1);
            }}
            className={selectCls}
          >
            <option value="">All statuses</option>
            {STATUSES.map((s) => (
              <option key={s} value={s}>
                {titleCase(s)}
              </option>
            ))}
          </select>
          <select
            value={severity}
            onChange={(e) => {
              setSeverity(e.target.value);
              setPage(1);
            }}
            className={selectCls}
          >
            <option value="">All severities</option>
            {SEVERITIES.map((s) => (
              <option key={s} value={s}>
                {titleCase(s)}
              </option>
            ))}
          </select>
          <span className="ml-auto text-xs text-neutral-500">
            {queue ? `${queue.total} report${queue.total === 1 ? "" : "s"}` : "…"}
          </span>
        </div>

        {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}

        <div className="space-y-2">
          {(queue?.items ?? []).length === 0 && !error && (
            <p className="text-sm text-neutral-500">No reports match these filters.</p>
          )}
          {queue?.items.map((report: GovernanceReportRow) => (
            <Link
              key={report.id}
              href={`/admin/governance/${report.id}`}
              className="block rounded-lg border border-neutral-200 p-4 transition hover:border-indigo-400 dark:border-neutral-800"
            >
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
                <span className="ml-auto text-xs text-neutral-400">
                  {fmt(report.created_at)}
                </span>
              </div>
              <p className="mt-2 line-clamp-2 text-sm text-neutral-700 dark:text-neutral-200">
                {report.description}
              </p>
              <p className="mt-1 text-xs text-neutral-500">
                Target: {report.target_type} · {report.target_id.slice(0, 8)}… ·{" "}
                {report.organization_name ?? "no organization"}
                {report.assigned_moderator_name
                  ? ` · Assigned: ${report.assigned_moderator_name}`
                  : ""}
              </p>
            </Link>
          ))}
        </div>

        {queue && queue.total > queue.page_size && (
          <div className="flex items-center justify-between text-sm">
            <button
              disabled={page <= 1}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              className="rounded border border-neutral-300 px-3 py-1.5 disabled:opacity-40 dark:border-neutral-700"
            >
              Previous
            </button>
            <span className="text-xs text-neutral-500">
              Page {queue.page} of {Math.max(1, Math.ceil(queue.total / queue.page_size))}
            </span>
            <button
              disabled={page * queue.page_size >= queue.total}
              onClick={() => setPage((p) => p + 1)}
              className="rounded border border-neutral-300 px-3 py-1.5 disabled:opacity-40 dark:border-neutral-700"
            >
              Next
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
