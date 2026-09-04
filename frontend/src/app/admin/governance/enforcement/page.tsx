"use client";
/**
 * Enforcement queue (Phase 11 proof).
 *
 * Platform-scope surface (enforcement.read): lists controlled enforcement
 * actions with their lifecycle state, target, scope and window. Actions are
 * granular by construction — no generic "admin action". Detail pages own the
 * approve/reject/revoke lifecycle with separation of duties.
 */
import { useCallback, useEffect, useState } from "react";
import Link from "next/link";

import { PageHeader, btnCls, cardCls, ghostBtnCls, inputCls } from "@/components/candidate/ui";
import { api } from "@/lib/api/session";
import { EnforcementActionList, EnforcementActionRow } from "@/lib/api/types";

const FILTERS = [
  { key: "", label: "All" },
  { key: "proposed", label: "Proposed" },
  { key: "approved", label: "Approved" },
  { key: "active", label: "Active" },
  { key: "expired", label: "Expired" },
  { key: "revoked", label: "Revoked" },
];

const typeStyle: Record<string, string> = {
  warning: "bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300",
  content_restriction:
    "bg-orange-100 text-orange-700 dark:bg-orange-950 dark:text-orange-300",
  communication_restriction:
    "bg-orange-100 text-orange-700 dark:bg-orange-950 dark:text-orange-300",
  account_restriction:
    "bg-rose-100 text-rose-700 dark:bg-rose-950 dark:text-rose-300",
  organization_restriction:
    "bg-rose-100 text-rose-700 dark:bg-rose-950 dark:text-rose-300",
  suspension: "bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300",
  reinstatement:
    "bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300",
};

const statusStyle: Record<string, string> = {
  proposed: "bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-300",
  approved: "bg-indigo-100 text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300",
  active: "bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300",
  expired: "bg-neutral-100 text-neutral-500 dark:bg-neutral-800 dark:text-neutral-400",
  revoked: "bg-neutral-100 text-neutral-600 dark:bg-neutral-800 dark:text-neutral-300",
  rejected: "bg-neutral-100 text-neutral-600 dark:bg-neutral-800 dark:text-neutral-300",
};

const chip = (active: boolean) =>
  active
    ? "rounded-full bg-[#d4af37] px-3 py-1 text-xs font-medium text-black"
    : "rounded-full border border-[#23272a] px-3 py-1 text-xs font-medium text-[#9ca3af] hover:text-white";

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

export default function EnforcementQueuePage() {
  // Read once at mount: query string is only ever a case filter link target.
  const [caseId] = useState(() => {
    if (typeof window === "undefined") return "";
    return new URLSearchParams(window.location.search).get("case_id") ?? "";
  });
  const [filter, setFilter] = useState("active");
  const [page, setPage] = useState(1);
  const [rows, setRows] = useState<EnforcementActionRow[]>([]);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState("");
  const [forbidden, setForbidden] = useState(false);
  const [showPropose, setShowPropose] = useState(false);
  const [busy, setBusy] = useState(false);
  const [propose, setPropose] = useState({
    action_type: "warning",
    scope: "account",
    reason_code: "policy_violation",
    target_user_id: "",
    case_id: "",
    note: "",
  });

  const load = useCallback(async () => {
    setError("");
    try {
      const params = new URLSearchParams();
      if (filter) params.set("status", filter);
      if (caseId) params.set("case_id", caseId);
      params.set("page", String(page));
      params.set("page_size", "20");
      const data = await api.get<EnforcementActionList>(
        `/enforcement/actions?${params.toString()}`
      );
      setRows(data.items);
      setTotal(data.total);
    } catch (e) {
      const err = e as { status?: number; message?: string };
      if (err.status === 403) setForbidden(true);
      setError(String(err.message ?? e));
    }
  }, [filter, page, caseId]);

  useEffect(() => {
    void load();
  }, [load]);

  if (forbidden) {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50 p-6 text-sm text-red-700 dark:border-red-900 dark:bg-red-950 dark:text-red-300">
        Your account does not hold an enforcement role on this platform.
      </div>
    );
  }

  const pages = Math.max(1, Math.ceil(total / 20));

  return (
    <div className="space-y-5">
      <PageHeader
        kicker="Enforcement"
        title="Action lifecycle"
        subtitle="PROPOSED → APPROVED → ACTIVE → EXPIRED / REVOKED. Creator cannot approve their own severe actions."
        actions={
          <button type="button" className={ghostBtnCls} onClick={() => setShowPropose((v) => !v)}>
            {showPropose ? "Hide proposal" : "Propose action"}
          </button>
        }
      />
      {showPropose && (
        <form
          className={`${cardCls} grid gap-3 sm:grid-cols-2`}
          onSubmit={(e) => {
            e.preventDefault();
            setBusy(true);
            api
              .post("/enforcement/actions", {
                action_type: propose.action_type,
                scope: propose.scope,
                reason_code: propose.reason_code,
                target_user_id: propose.target_user_id || null,
                case_id: propose.case_id || caseId || null,
                note: propose.note || null,
                effective_at: new Date().toISOString(),
              })
              .then(() => {
                setShowPropose(false);
                return load();
              })
              .catch((err) => setError(String((err as Error).message ?? err)))
              .finally(() => setBusy(false));
          }}
        >
          <select className={inputCls} value={propose.action_type} onChange={(e) => setPropose((p) => ({ ...p, action_type: e.target.value }))}>
            <option value="warning">warning</option>
            <option value="communication_restriction">communication_restriction</option>
            <option value="account_restriction">account_restriction</option>
            <option value="suspension">suspension</option>
          </select>
          <select className={inputCls} value={propose.scope} onChange={(e) => setPropose((p) => ({ ...p, scope: e.target.value }))}>
            <option value="account">account</option>
            <option value="communications">communications</option>
            <option value="applications">applications</option>
            <option value="platform_access">platform_access</option>
          </select>
          <select className={inputCls} value={propose.reason_code} onChange={(e) => setPropose((p) => ({ ...p, reason_code: e.target.value }))}>
            <option value="policy_violation">policy_violation</option>
            <option value="harassment">harassment</option>
            <option value="outreach_abuse">outreach_abuse</option>
            <option value="suspicious_activity">suspicious_activity</option>
          </select>
          <input className={inputCls} placeholder="Target user UUID" value={propose.target_user_id} onChange={(e) => setPropose((p) => ({ ...p, target_user_id: e.target.value }))} />
          <input className={inputCls} placeholder="Linked case UUID (optional)" value={propose.case_id} onChange={(e) => setPropose((p) => ({ ...p, case_id: e.target.value }))} />
          <input className={inputCls} placeholder="Sanitized note" value={propose.note} onChange={(e) => setPropose((p) => ({ ...p, note: e.target.value }))} />
          <button type="submit" className={btnCls} disabled={busy || !propose.target_user_id}>
            Submit proposal
          </button>
        </form>
      )}
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-sm text-[#9ca3af]">{total} total</span>
        {caseId && (
          <Link
            href="/admin/governance"
            className="rounded bg-neutral-100 px-2 py-0.5 text-xs text-neutral-600 hover:bg-neutral-200 dark:bg-neutral-800 dark:text-neutral-300"
          >
            Case {short(caseId)} filter · clear
          </Link>
        )}
      </div>

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
                <th className="px-4 py-2.5 font-medium">Action</th>
                <th className="px-4 py-2.5 font-medium">Target</th>
                <th className="px-4 py-2.5 font-medium">Scope</th>
                <th className="px-4 py-2.5 font-medium">Status</th>
                <th className="px-4 py-2.5 font-medium">Effective</th>
                <th className="px-4 py-2.5 font-medium">Expires</th>
                <th className="px-4 py-2.5 font-medium">Created</th>
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
                      href={`/admin/governance/enforcement/${row.id}`}
                      className="font-medium text-[#d4af37] hover:underline"
                    >
                      {titleCase(row.action_type)}
                    </Link>
                    <span
                      className={`ml-1.5 rounded px-1.5 py-0.5 text-[10px] font-medium ${typeStyle[row.action_type] ?? ""}`}
                    >
                      {titleCase(row.reason_code)}
                    </span>
                  </td>
                  <td className="px-4 py-2.5 font-mono text-xs text-neutral-500">
                    {row.target_user_id
                      ? `user ${short(row.target_user_id)}`
                      : row.target_organization_id
                        ? `org ${short(row.target_organization_id)}`
                        : "—"}
                  </td>
                  <td className="px-4 py-2.5 text-xs text-neutral-500">
                    {titleCase(row.scope)}
                  </td>
                  <td className="px-4 py-2.5">
                    <span
                      className={`rounded px-1.5 py-0.5 text-xs font-medium ${statusStyle[row.status] ?? ""}`}
                    >
                      {titleCase(row.status)}
                    </span>
                  </td>
                  <td className="px-4 py-2.5 text-xs text-neutral-500">
                    {fmt(row.effective_at)}
                  </td>
                  <td className="px-4 py-2.5 text-xs text-neutral-500">
                    {fmt(row.expires_at)}
                  </td>
                  <td className="px-4 py-2.5 text-xs text-neutral-500">
                    {fmt(row.created_at)}
                  </td>
                </tr>
              ))}
              {rows.length === 0 && (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center text-neutral-400">
                    No enforcement actions in this view.
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
