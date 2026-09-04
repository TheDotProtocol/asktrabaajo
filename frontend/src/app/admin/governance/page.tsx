"use client";
/**
 * Platform Control Room (Phase 10 proof).
 *
 * The first screen answers "what requires my attention right now?" — open /
 * urgent / critical / unassigned / mine / breached / due soon / escalated —
 * with quick queue views behind it. Least privilege holds: this surface
 * renders case metadata and references only, never private Work ID data or
 * documents. Integrity signals are neutral activity markers, not accusations.
 */
import { useCallback, useEffect, useState } from "react";
import Link from "next/link";

import { ErrorBanner, PageHeader, cardCls, inputCls } from "@/components/candidate/ui";
import { api } from "@/lib/api/session";
import {
  GovernanceDashboard,
  GovernanceQueue,
  GovernanceReportRow,
  IntegritySignalRow,
} from "@/lib/api/types";

const STATUSES = ["open", "in_review", "assigned", "escalated", "resolved", "closed"];
const SEVERITIES = ["low", "medium", "high", "critical"];
const PRIORITIES = ["low", "normal", "high", "urgent", "critical"];
const VIEWS: Array<{ key: string; label: string }> = [
  { key: "", label: "All" },
  { key: "mine", label: "My cases" },
  { key: "unassigned", label: "Unassigned" },
  { key: "escalated", label: "Escalated" },
  { key: "breached", label: "SLA breached" },
  { key: "due", label: "Due soon" },
];

const statusStyle: Record<string, string> = {
  open: "bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-300",
  in_review: "bg-indigo-100 text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300",
  assigned: "bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300",
  escalated: "bg-purple-100 text-purple-700 dark:bg-purple-950 dark:text-purple-300",
  resolved: "bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-400",
  closed: "bg-neutral-100 text-neutral-600 dark:bg-neutral-800 dark:text-neutral-300",
};

const severityStyle: Record<string, string> = {
  low: "bg-neutral-100 text-neutral-600 dark:bg-neutral-800 dark:text-neutral-300",
  medium: "bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-300",
  high: "bg-orange-100 text-orange-700 dark:bg-orange-950 dark:text-orange-300",
  critical: "bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300",
};

const priorityStyle: Record<string, string> = {
  low: "bg-neutral-100 text-neutral-500 dark:bg-neutral-800 dark:text-neutral-400",
  normal: "bg-neutral-100 text-neutral-600 dark:bg-neutral-800 dark:text-neutral-300",
  high: "bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300",
  urgent: "bg-orange-100 text-orange-700 dark:bg-orange-950 dark:text-orange-300",
  critical: "bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300",
};

const slaStyle: Record<string, string> = {
  on_track: "bg-emerald-50 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-400",
  due_soon: "bg-amber-50 text-amber-700 dark:bg-amber-950 dark:text-amber-300",
  breached: "bg-red-50 text-red-700 dark:bg-red-950 dark:text-red-300",
};

const selectCls = inputCls;
const chipCls = (active: boolean) =>
  `rounded px-2.5 py-1 text-xs font-medium transition ${
    active ? "bg-[#d4af37] text-black" : "border border-[#23272a] text-[#9ca3af] hover:text-white"
  }`;

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

export default function GovernanceControlRoomPage() {
  const [queue, setQueue] = useState<GovernanceQueue | null>(null);
  const [dash, setDash] = useState<GovernanceDashboard | null>(null);
  const [signals, setSignals] = useState<IntegritySignalRow[]>([]);
  const [view, setView] = useState("");
  const [status, setStatus] = useState("");
  const [severity, setSeverity] = useState("");
  const [priority, setPriority] = useState("");
  const [page, setPage] = useState(1);
  const [error, setError] = useState("");
  const [forbidden, setForbidden] = useState(false);

  const load = useCallback(async () => {
    setError("");
    const params = new URLSearchParams({ page: String(page), page_size: "25" });
    if (status) params.set("status", status);
    if (severity) params.set("severity", severity);
    if (priority) params.set("priority", priority);
    if (view === "mine") params.set("mine", "true");
    else if (view === "unassigned") params.set("unassigned", "true");
    else if (view === "escalated") params.set("escalated", "true");
    else if (view === "breached") params.set("sla", "breached");
    else if (view === "due") params.set("sla", "due_soon");
    try {
      const [q, d, s] = await Promise.all([
        api.get<GovernanceQueue>(`/governance/reports?${params.toString()}`),
        api.get<GovernanceDashboard>("/governance/dashboard"),
        api.get<{ items: IntegritySignalRow[] }>("/governance/signals"),
      ]);
      setQueue(q);
      setDash(d);
      setSignals(s.items);
    } catch (e) {
      const err = e as { status?: number; message?: string };
      if (err.status === 403) setForbidden(true);
      setError(String(err.message ?? e));
    }
  }, [page, status, severity, priority, view]);

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

  const statCards = dash
    ? [
        { label: "Open cases", value: dash.open, tone: "text-blue-600" },
        { label: "Urgent", value: dash.urgent, tone: "text-orange-600" },
        { label: "Critical", value: dash.critical, tone: "text-red-600" },
        { label: "Unassigned", value: dash.unassigned, tone: "text-neutral-700" },
        { label: "Mine", value: dash.mine, tone: "text-indigo-600" },
        { label: "SLA breached", value: dash.breached, tone: "text-red-600" },
        { label: "Due soon", value: dash.due_soon, tone: "text-amber-600" },
        { label: "Escalated", value: dash.escalated, tone: "text-purple-600" },
      ]
    : [];

  return (
    <div className="space-y-6">
      <PageHeader
        kicker="Governance"
        title="Case queue"
        subtitle="Operational queue for platform integrity. Case metadata and references only — private Work ID data is never surfaced here."
      />

      {dash && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-8">
          {statCards.map((card) => (
            <div key={card.label} className={cardCls}>
              <div className={`text-2xl font-semibold ${card.tone}`}>{card.value}</div>
              <div className="mt-0.5 text-[11px] leading-tight text-neutral-500">
                {card.label}
              </div>
            </div>
          ))}
        </div>
      )}

      {signals.length > 0 && (
        <div className={cardCls}>
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold">Integrity signals</h2>
            <span className="text-[11px] text-neutral-400">
              Activity patterns — review required, never proof of misconduct
            </span>
          </div>
          <div className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {signals.slice(0, 6).map((s) => (
              <div
                key={`${s.subject_id}-${s.signal_type}`}
                className="rounded-lg border border-neutral-200 p-3 dark:border-neutral-800"
              >
                <p className="text-xs font-medium text-neutral-700 dark:text-neutral-200">
                  {titleCase(s.signal_type)}
                  <span className="ml-2 rounded bg-neutral-100 px-1.5 py-0.5 text-[10px] text-neutral-500 dark:bg-neutral-800">
                    ×{s.count} / {s.window_days}d
                  </span>
                </p>
                <p className="mt-1 text-[11px] text-neutral-500">
                  {s.subject_name ?? `${s.subject_type} ${s.subject_id.slice(0, 8)}…`}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className={`${cardCls} space-y-4`}>
        <div className="flex flex-wrap items-center gap-1.5">
          {VIEWS.map((v) => (
            <button
              key={v.key}
              onClick={() => {
                setView(v.key);
                setPage(1);
              }}
              className={chipCls(view === v.key)}
            >
              {v.label}
            </button>
          ))}
        </div>

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
          <select
            value={priority}
            onChange={(e) => {
              setPriority(e.target.value);
              setPage(1);
            }}
            className={selectCls}
          >
            <option value="">All priorities</option>
            {PRIORITIES.map((s) => (
              <option key={s} value={s}>
                {titleCase(s)}
              </option>
            ))}
          </select>
          <span className="ml-auto text-xs text-neutral-500">
            {queue ? `${queue.total} case${queue.total === 1 ? "" : "s"}` : "…"}
          </span>
        </div>

        {error && <ErrorBanner message={error} onRetry={() => void load()} />}

        <div className="space-y-2">
          {(queue?.items ?? []).length === 0 && !error && (
            <p className="text-sm text-neutral-500">No cases match these filters.</p>
          )}
          {queue?.items.map((report: GovernanceReportRow) => (
            <Link
              key={report.id}
              href={`/admin/governance/${report.id}`}
              className="block rounded-lg border border-neutral-200 p-4 transition hover:border-indigo-400 dark:border-neutral-800"
            >
              <div className="flex flex-wrap items-center gap-1.5">
                <span className="text-xs font-medium text-neutral-400">
                  {report.case_ref ?? report.id.slice(0, 8)}
                </span>
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
                <span
                  className={`rounded px-1.5 py-0.5 text-xs font-medium ${priorityStyle[report.priority ?? "normal"] ?? ""}`}
                >
                  {titleCase(report.priority ?? "normal")}
                </span>
                {report.sla_state && (
                  <span
                    className={`rounded px-1.5 py-0.5 text-xs font-medium ${slaStyle[report.sla_state] ?? ""}`}
                  >
                    {titleCase(report.sla_state)}
                  </span>
                )}
                <span className="rounded bg-neutral-100 px-1.5 py-0.5 text-xs text-neutral-600 dark:bg-neutral-800 dark:text-neutral-300">
                  {titleCase(report.category)}
                </span>
                {report.team_name && (
                  <span className="rounded bg-purple-100 px-1.5 py-0.5 text-xs text-purple-700 dark:bg-purple-950 dark:text-purple-300">
                    {report.team_name}
                  </span>
                )}
                <span className="ml-auto text-xs text-neutral-400">
                  {fmt(report.created_at)}
                </span>
              </div>
              <p className="mt-2 line-clamp-2 text-sm text-neutral-700 dark:text-neutral-200">
                {report.description}
              </p>
              <p className="mt-1 text-xs text-neutral-500">
                Target: {report.target_type} · {report.target_id.slice(0, 8)}…
                {report.organization_name ? ` · ${report.organization_name}` : ""}
                {report.assigned_moderator_name
                  ? ` · Assigned: ${report.assigned_moderator_name}`
                  : " · Unassigned"}
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
