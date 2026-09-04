"use client";
/**
 * Enforcement action detail (Phase 11 proof).
 *
 * Shows WHY the action exists (controlled reason code + sanitized note),
 * the related case, target and scope, the deterministic lifecycle window,
 * approval state, and the audit timeline. Approve/reject/revoke run with the
 * server-enforced separation of duties (creator != approver for severe types).
 */
import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";

import { btnCls, cardCls, ghostBtnCls, inputCls } from "@/components/candidate/ui";
import { api } from "@/lib/api/session";
import { EnforcementActionRow } from "@/lib/api/types";

const statusStyle: Record<string, string> = {
  proposed: "bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-300",
  approved: "bg-indigo-100 text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300",
  active: "bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300",
  expired: "bg-neutral-100 text-neutral-500 dark:bg-neutral-800 dark:text-neutral-400",
  revoked: "bg-neutral-100 text-neutral-600 dark:bg-neutral-800 dark:text-neutral-300",
  rejected: "bg-neutral-100 text-neutral-600 dark:bg-neutral-800 dark:text-neutral-300",
};

const primaryBtn = btnCls;
const ghostBtn = ghostBtnCls;
const dangerBtn =
  "rounded bg-red-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-40";

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

export default function EnforcementActionDetailPage() {
  const params = useParams();
  const actionId = String(params?.id ?? "");
  const [action, setAction] = useState<EnforcementActionRow | null>(null);
  const [approvalNote, setApprovalNote] = useState("");
  const [rejectionNote, setRejectionNote] = useState("");
  const [revokeNote, setRevokeNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [forbidden, setForbidden] = useState(false);

  const load = useCallback(async () => {
    if (!actionId) return;
    setError("");
    try {
      const row = await api.get<EnforcementActionRow>(
        `/enforcement/actions/${actionId}`
      );
      setAction(row);
    } catch (e) {
      const err = e as { status?: number; message?: string };
      if (err.status === 403) setForbidden(true);
      setError(String(err.message ?? e));
    }
  }, [actionId]);

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

  if (!action) {
    return (
      <p className="text-sm text-neutral-500">
        {error ? `Could not load action: ${error}` : "Loading action…"}
      </p>
    );
  }

  async function run(fn: () => Promise<unknown>) {
    setBusy(true);
    setError("");
    try {
      await fn();
      await load();
    } catch (e) {
      setError(String((e as Error).message ?? e));
    } finally {
      setBusy(false);
    }
  }

  async function approve() {
    await run(() =>
      api.post(`/enforcement/actions/${actionId}/approve`, {
        approval_note: approvalNote.trim() || null,
      })
    );
    setApprovalNote("");
  }

  async function reject() {
    await run(() =>
      api.post(`/enforcement/actions/${actionId}/reject`, {
        rejection_note: rejectionNote.trim() || null,
      })
    );
    setRejectionNote("");
  }

  async function revoke() {
    await run(() =>
      api.post(`/enforcement/actions/${actionId}/revoke`, {
        revoke_note: revokeNote.trim() || null,
      })
    );
    setRevokeNote("");
  }

  const canApprove = action.status === "proposed";
  const canRevoke = action.status === "active" || action.status === "approved";

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-3">
        <Link
          href="/admin/governance/enforcement"
          className="text-sm text-neutral-500 hover:text-neutral-800 dark:hover:text-neutral-200"
        >
          ← Enforcement queue
        </Link>
        <span
          className={`rounded px-2 py-0.5 text-xs font-medium ${statusStyle[action.status] ?? ""}`}
        >
          {titleCase(action.status)}
        </span>
        {action.governance_case_id && (
          <Link
            href={`/admin/governance/${action.governance_case_id}`}
            className="text-sm text-[#d4af37] hover:underline"
          >
            Case {short(action.governance_case_id)}
          </Link>
        )}
      </div>

      <div>
        <h1 className="text-xl font-semibold tracking-tight">
          {titleCase(action.action_type)}
          <span className="ml-2 text-sm font-normal text-neutral-500">
            · scope {titleCase(action.scope)}
          </span>
        </h1>
        <p className="mt-1 text-sm text-neutral-500">
          Reason: <span className="font-medium">{titleCase(action.reason_code)}</span>
          {action.note ? ` — ${action.note}` : ""}
        </p>
      </div>

      {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}

      <div className="grid gap-4 lg:grid-cols-3">
        <div className={`${cardCls} space-y-4 lg:col-span-2`}>
          <h2 className="text-sm font-semibold text-neutral-700 dark:text-neutral-200">
            Action details
          </h2>
          <dl className="grid grid-cols-2 gap-x-4 gap-y-3 text-sm">
            <div>
              <dt className="text-neutral-400">Target user</dt>
              <dd className="font-mono text-xs text-neutral-600 dark:text-neutral-300">
                {short(action.target_user_id)}
              </dd>
            </div>
            <div>
              <dt className="text-neutral-400">Target organization</dt>
              <dd className="font-mono text-xs text-neutral-600 dark:text-neutral-300">
                {short(action.target_organization_id)}
              </dd>
            </div>
            <div>
              <dt className="text-neutral-400">Effective at</dt>
              <dd className="text-neutral-700 dark:text-neutral-200">
                {fmt(action.effective_at)}
              </dd>
            </div>
            <div>
              <dt className="text-neutral-400">Expires at</dt>
              <dd className="text-neutral-700 dark:text-neutral-200">
                {fmt(action.expires_at)}
              </dd>
            </div>
            <div>
              <dt className="text-neutral-400">Approved by</dt>
              <dd className="font-mono text-xs text-neutral-600 dark:text-neutral-300">
                {short(action.approved_by)}
              </dd>
            </div>
            <div>
              <dt className="text-neutral-400">Supersedes</dt>
              <dd className="font-mono text-xs text-neutral-600 dark:text-neutral-300">
                {short(action.supersedes_id)}
              </dd>
            </div>
          </dl>

          <div className="border-t border-neutral-100 pt-4 dark:border-neutral-800">
            <h3 className="mb-2 text-sm font-semibold text-neutral-700 dark:text-neutral-200">
              Audit timeline
            </h3>
            <ol className="space-y-3">
              {(action.audit ?? []).map((entry) => (
                <li key={`${entry.action}-${entry.created_at}`} className="text-sm">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-mono text-xs text-[#d4af37]">
                      {entry.action}
                    </span>
                    <span className="text-xs text-neutral-400">
                      {fmt(entry.created_at)}
                    </span>
                    <span className="font-mono text-[10px] text-neutral-400">
                      actor {short(entry.actor_id)}
                    </span>
                  </div>
                  {entry.payload && Object.keys(entry.payload).length > 0 && (
                    <div className="mt-1 font-mono text-xs text-neutral-500">
                      {JSON.stringify(entry.payload)}
                    </div>
                  )}
                </li>
              ))}
              {(action.audit ?? []).length === 0 && (
                <li className="text-neutral-400">No recorded events yet.</li>
              )}
            </ol>
          </div>
        </div>

        <div className="space-y-4">
          {canApprove && (
            <div className={`${cardCls} space-y-2`}>
              <h2 className="text-sm font-semibold text-neutral-700 dark:text-neutral-200">
                Approval (separation enforced server-side)
              </h2>
              <input
                className={inputCls}
                placeholder="Approval note (optional)"
                value={approvalNote}
                onChange={(e) => setApprovalNote(e.target.value)}
              />
              <div className="flex gap-2">
                <button className={primaryBtn} disabled={busy} onClick={approve}>
                  Approve
                </button>
                <button className={ghostBtn} disabled={busy} onClick={reject}>
                  Reject
                </button>
              </div>
            </div>
          )}
          {canRevoke && (
            <div className={`${cardCls} space-y-2`}>
              <h2 className="text-sm font-semibold text-neutral-700 dark:text-neutral-200">
                Revoke
              </h2>
              <input
                className={inputCls}
                placeholder="Revoke note (optional)"
                value={revokeNote}
                onChange={(e) => setRevokeNote(e.target.value)}
              />
              <button className={dangerBtn} disabled={busy} onClick={revoke}>
                Revoke action
              </button>
            </div>
          )}
          {!canApprove && !canRevoke && (
            <div className={`${cardCls} text-sm text-neutral-500`}>
              This action has reached a terminal state — no further lifecycle
              transitions are available.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
