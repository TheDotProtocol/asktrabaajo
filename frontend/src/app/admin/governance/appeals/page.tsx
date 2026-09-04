"use client";
/**
 * Appeals queue (Phase 11 proof).
 *
 * Governance surface (appeals.read): enforcement targets contest an eligible
 * action; reviewers assign, review and decide. Internal review notes travel
 * with the governance copy but are NEVER exposed to the appellant — the
 * appellant-visible detail is a separate view.
 */
import { useCallback, useEffect, useState } from "react";
import Link from "next/link";

import { PageHeader, cardCls } from "@/components/candidate/ui";
import { api } from "@/lib/api/session";
import { AppealList, AppealRow } from "@/lib/api/types";

const FILTERS = [
  { key: "", label: "All" },
  { key: "submitted", label: "Submitted" },
  { key: "assigned", label: "Assigned" },
  { key: "under_review", label: "Under review" },
  { key: "decided", label: "Decided" },
  { key: "withdrawn", label: "Withdrawn" },
];

const statusStyle: Record<string, string> = {
  submitted: "bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-300",
  assigned: "bg-indigo-100 text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300",
  under_review: "bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300",
  decided: "bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-400",
  withdrawn: "bg-neutral-100 text-neutral-600 dark:bg-neutral-800 dark:text-neutral-300",
};

const decisionStyle: Record<string, string> = {
  accepted: "bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-400",
  partially_granted:
    "bg-lime-100 text-lime-700 dark:bg-lime-950 dark:text-lime-300",
  rejected: "bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300",
};

const chip = (active: boolean) =>
  active
    ? "rounded-full bg-[#d4af37] px-3 py-1 text-xs font-medium text-black"
    : "rounded-full border border-[#23272a] px-3 py-1 text-xs font-medium text-[#9ca3af]";

function titleCase(value: string): string {
  return value
    .split(/[_\\s]+/)
    .map((w) => (w ? w[0].toUpperCase() + w.slice(1) : w))
    .join(" ");
}

function short(id: string | null): string {
  return id ? id.slice(0, 8) : "—";
}

function fmt(ts: string | null): string {
  if (!ts) return "—";
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

export default function AppealsQueuePage() {
  const [filter, setFilter] = useState("");
  const [page, setPage] = useState(1);
  const [rows, setRows] = useState<AppealRow[]>([]);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState("");
  const [forbidden, setForbidden] = useState(false);

  const load = useCallback(async () => {
    setError("");
    try {
      const params = new URLSearchParams();
      if (filter) params.set("status", filter);
      params.set("page", String(page));
      params.set("page_size", "20");
      const data = await api.get<AppealList>(`/enforcement/appeals?${params}`);
      setRows(data.items);
      setTotal(data.total);
    } catch (e) {
      const err = e as { status?: number; message?: string };
      if (err.status === 403) setForbidden(true);
      setError(String(err.message ?? e));
    }
  }, [filter, page]);

  useEffect(() => {
    void load();
  }, [load]);

  if (forbidden) {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50 p-6 text-sm text-red-700 dark:border-red-900 dark:bg-red-950 dark:text-red-300">
        Your account does not hold an appeals role on this platform.
      </div>
    );
  }

  const pages = Math.max(1, Math.ceil(total / 20));

  return (
    <div className="space-y-5">
      <PageHeader
        kicker="Appeals"
        title="Appeals control room"
        subtitle={`${total} authorized records. Decisions can create a superseding reinstatement — the backend owns that relationship.`}
      />

      <div className="flex flex-wrap items-center gap-1.5">
        {FILTERS.map((f) => (
          <button
            key={f.key}
            className={chip(filter === f.key)}
            onClick={() => {
              setFilter(f.key);
              setPage(1);
            }}
          >
            {f.label}
          </button>
        ))}
      </div>

      {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}

      <div className={`${cardCls} overflow-hidden p-0`}>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-neutral-200 text-xs uppercase tracking-wide text-neutral-400 dark:border-neutral-800">
                <th className="px-4 py-2.5 font-medium">Appeal</th>
                <th className="px-4 py-2.5 font-medium">Appellant</th>
                <th className="px-4 py-2.5 font-medium">Status</th>
                <th className="px-4 py-2.5 font-medium">Reviewer</th>
                <th className="px-4 py-2.5 font-medium">Decision</th>
                <th className="px-4 py-2.5 font-medium">Submitted</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr
                  key={row.id}
                  className="border-b border-neutral-100 last:border-0 hover:bg-neutral-50 dark:border-neutral-800/60 dark:hover:bg-neutral-800/40"
                >
                  <td className="px-4 py-2.5">
                    <Link
                      href={`/admin/governance/appeals/${row.id}`}
                      className="font-medium text-[#d4af37] hover:underline"
                    >
                      {short(row.id)}
                    </Link>
                    <div className="text-xs text-neutral-400">
                      against {short(row.enforcement_action_id)}
                    </div>
                  </td>
                  <td className="px-4 py-2.5 font-mono text-xs text-neutral-500">
                    {short(row.appellant_user_id)}
                  </td>
                  <td className="px-4 py-2.5">
                    <span
                      className={`rounded px-1.5 py-0.5 text-xs font-medium ${statusStyle[row.status] ?? ""}`}
                    >
                      {titleCase(row.status)}
                    </span>
                  </td>
                  <td className="px-4 py-2.5 font-mono text-xs text-neutral-500">
                    {short(row.assigned_reviewer_id)}
                  </td>
                  <td className="px-4 py-2.5">
                    {row.decision ? (
                      <span
                        className={`rounded px-1.5 py-0.5 text-xs font-medium ${decisionStyle[row.decision] ?? ""}`}
                      >
                        {titleCase(row.decision)}
                      </span>
                    ) : (
                      <span className="text-neutral-400">—</span>
                    )}
                  </td>
                  <td className="px-4 py-2.5 text-xs text-neutral-500">
                    {fmt(row.created_at)}
                  </td>
                </tr>
              ))}
              {rows.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-neutral-400">
                    No appeals in this view.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {pages > 1 && (
        <div className="flex items-center gap-2 text-sm">
          <button
            disabled={page <= 1}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            className="rounded border border-neutral-300 px-2.5 py-1 text-neutral-600 disabled:opacity-40 dark:border-neutral-700 dark:text-neutral-300"
          >
            ← Prev
          </button>
          <span className="text-neutral-500">
            Page {page} of {pages}
          </span>
          <button
            disabled={page >= pages}
            onClick={() => setPage((p) => Math.min(pages, p + 1))}
            className="rounded border border-neutral-300 px-2.5 py-1 text-neutral-600 disabled:opacity-40 dark:border-neutral-700 dark:text-neutral-300"
          >
            Next →
          </button>
        </div>
      )}
    </div>
  );
}
