"use client";
/**
 * Appeal detail (Phase 11 proof).
 *
 * Reviewer surface (appeals.manage/decide): the original enforcement action,
 * the appellant's sanitized statement, status/assignment, decision controls
 * and the audit timeline. The reviewer's internal note is governance-only;
 * the appellant-visible outcome is the bounded decision_note.
 */
import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";

import { api } from "@/lib/api/session";
import { AppealRow } from "@/lib/api/types";

const statusStyle: Record<string, string> = {
  submitted: "bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-300",
  assigned: "bg-indigo-100 text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300",
  under_review: "bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300",
  decided: "bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-400",
  withdrawn: "bg-neutral-100 text-neutral-600 dark:bg-neutral-800 dark:text-neutral-300",
};

const cardCls =
  "rounded-xl border border-neutral-200 bg-white p-5 dark:border-neutral-800 dark:bg-neutral-900";
const primaryBtn =
  "rounded bg-indigo-500 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-600 disabled:opacity-40";
const ghostBtn =
  "rounded border border-neutral-300 px-3 py-1.5 text-sm text-neutral-600 hover:border-indigo-400 dark:border-neutral-700 dark:text-neutral-300";
const selectCls =
  "rounded border border-neutral-300 bg-white px-2 py-1.5 text-sm dark:border-neutral-700 dark:bg-neutral-900";
const inputCls =
  "w-full rounded border border-neutral-300 bg-white px-3 py-2 text-sm dark:border-neutral-700 dark:bg-neutral-900";
const labelCls =
  "block text-xs font-medium uppercase tracking-wide text-neutral-400";

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

export default function AppealDetailPage() {
  const params = useParams();
  const appealId = String(params?.id ?? "");
  const [appeal, setAppeal] = useState<AppealRow | null>(null);
  const [reviewerId, setReviewerId] = useState("");
  const [decision, setDecision] = useState("accepted");
  const [decisionNote, setDecisionNote] = useState("");
  const [reviewNote, setReviewNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [forbidden, setForbidden] = useState(false);

  const load = useCallback(async () => {
    if (!appealId) return;
    setError("");
    try {
      const row = await api.get<AppealRow>(`/enforcement/appeals/${appealId}`);
      setAppeal(row);
    } catch (e) {
      const err = e as { status?: number; message?: string };
      if (err.status === 403) setForbidden(true);
      setError(String(err.message ?? e));
    }
  }, [appealId]);

  useEffect(() => {
    void load();
  }, [load]);

  if (forbidden) {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50 p-6 text-sm text-red-700 dark:border-red-900 dark:bg-red-950 dark:text-red-300">
        You cannot view this appeal.
      </div>
    );
  }

  if (!appeal) {
    return (
      <p className="text-sm text-neutral-500">
        {error ? `Could not load appeal: ${error}` : "Loading appeal…"}
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

  async function assign() {
    if (!reviewerId.trim()) {
      setError("A reviewer user id is required.");
      return;
    }
    await run(() =>
      api.post(`/enforcement/appeals/${appealId}/assign`, {
        reviewer_id: reviewerId.trim(),
      })
    );
    setReviewerId("");
  }

  async function beginReview() {
    await run(() => api.post(`/enforcement/appeals/${appealId}/review`));
  }

  async function decide() {
    const note = decisionNote.trim();
    if (note.length < 1) {
      setError("A decision note is required (this is the appellant-visible outcome).");
      return;
    }
    await run(async () => {
      await api.post(`/enforcement/appeals/${appealId}/decide`, {
        decision,
        decision_note: note,
        review_note: reviewNote.trim() || null,
      });
      setDecisionNote("");
      setReviewNote("");
    });
  }

  const open = ["submitted", "assigned", "under_review"].includes(appeal.status);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-3">
        <Link
          href="/admin/governance/appeals"
          className="text-sm text-neutral-500 hover:text-neutral-800 dark:hover:text-neutral-200"
        >
          ← Appeals queue
        </Link>
        <span
          className={`rounded px-2 py-0.5 text-xs font-medium ${statusStyle[appeal.status] ?? ""}`}
        >
          {titleCase(appeal.status)}
        </span>
        {appeal.decision && (
          <span className="rounded bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300">
            {titleCase(appeal.decision)}
          </span>
        )}
      </div>

      <div>
        <h1 className="text-xl font-semibold tracking-tight">
          Appeal {short(appeal.id)}
        </h1>
        <p className="mt-1 text-sm text-neutral-500">
          by {short(appeal.appellant_user_id)} · reason{" "}
          <span className="font-medium">{titleCase(appeal.reason_code)}</span> · filed{" "}
          {fmt(appeal.created_at)}
        </p>
      </div>

      {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}

      <div className="grid gap-4 lg:grid-cols-3">
        <div className="space-y-4 lg:col-span-2">
          <div className={`${cardCls} space-y-3`}>
            <h2 className="text-sm font-semibold text-neutral-700 dark:text-neutral-200">
              Original enforcement action
            </h2>
            <Link
              href={`/admin/governance/enforcement/${appeal.enforcement_action_id}`}
              className="text-sm font-medium text-indigo-600 hover:underline dark:text-indigo-400"
            >
              Action {short(appeal.enforcement_action_id)}
            </Link>
            {appeal.superseding_action_id && (
              <div className="text-sm">
                <span className="text-neutral-400">Superseded by </span>
                <Link
                  href={`/admin/governance/enforcement/${appeal.superseding_action_id}`}
                  className="font-medium text-emerald-600 hover:underline dark:text-emerald-400"
                >
                  {short(appeal.superseding_action_id)}
                </Link>
              </div>
            )}
          </div>

          <div className={`${cardCls} space-y-2`}>
            <h2 className="text-sm font-semibold text-neutral-700 dark:text-neutral-200">
              Appellant statement
            </h2>
            <p className="rounded-lg bg-neutral-50 p-3 text-sm leading-relaxed text-neutral-700 dark:bg-neutral-950 dark:text-neutral-300">
              {appeal.statement}
            </p>
            {appeal.decision_note && (
              <>
                <h3 className="pt-2 text-sm font-semibold text-neutral-700 dark:text-neutral-200">
                  Outcome (appellant-visible)
                </h3>
                <p className="rounded-lg bg-emerald-50 p-3 text-sm leading-relaxed text-emerald-800 dark:bg-emerald-950 dark:text-emerald-200">
                  {appeal.decision_note}
                </p>
              </>
            )}
            {appeal.review_note && (
              <>
                <h3 className="pt-2 text-sm font-semibold text-neutral-700 dark:text-neutral-200">
                  Internal review note (governance only)
                </h3>
                <p className="rounded-lg bg-amber-50 p-3 text-sm leading-relaxed text-amber-800 dark:bg-amber-950 dark:text-amber-200">
                  {appeal.review_note}
                </p>
              </>
            )}
          </div>

          <div className={`${cardCls} space-y-3`}>
            <h2 className="text-sm font-semibold text-neutral-700 dark:text-neutral-200">
              Audit timeline
            </h2>
            <ol className="space-y-3">
              {(appeal.audit ?? []).map((entry) => (
                <li key={`${entry.action}-${entry.created_at}`} className="text-sm">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-mono text-xs text-indigo-600 dark:text-indigo-400">
                      {entry.action}
                    </span>
                    <span className="text-xs text-neutral-400">
                      {fmt(entry.created_at)}
                    </span>
                    <span className="font-mono text-[10px] text-neutral-400">
                      actor {short(entry.actor_id)}
                    </span>
                  </div>
                </li>
              ))}
              {(appeal.audit ?? []).length === 0 && (
                <li className="text-neutral-400">No recorded events yet.</li>
              )}
            </ol>
          </div>
        </div>

        <div className="space-y-4">
          <div className={`${cardCls} space-y-2`}>
            <h2 className="text-sm font-semibold text-neutral-700 dark:text-neutral-200">
              Assignment
            </h2>
            <label className={labelCls}>Reviewer user id</label>
            <input
              className={inputCls}
              placeholder={appeal.assigned_reviewer_id ?? "uuid"}
              value={reviewerId}
              onChange={(e) => setReviewerId(e.target.value)}
            />
            <div className="flex gap-2">
              <button className={ghostBtn} disabled={busy || !open} onClick={assign}>
                Assign reviewer
              </button>
              {appeal.status === "assigned" && (
                <button className={ghostBtn} disabled={busy} onClick={beginReview}>
                  Begin review
                </button>
              )}
            </div>
            <p className="text-xs text-neutral-400">
              Assigned to {short(appeal.assigned_reviewer_id)} · decided by{" "}
              {short(appeal.decided_by)}
            </p>
          </div>

          {open && appeal.status !== "submitted" && (
            <div className={`${cardCls} space-y-2`}>
              <h2 className="text-sm font-semibold text-neutral-700 dark:text-neutral-200">
                Decision
              </h2>
              <label className={labelCls}>Decision</label>
              <select
                className={selectCls}
                value={decision}
                onChange={(e) => setDecision(e.target.value)}
              >
                <option value="accepted">Accepted</option>
                <option value="partially_granted">Partially granted</option>
                <option value="rejected">Rejected</option>
              </select>
              <label className={labelCls}>
                Decision note (shown to the appellant)
              </label>
              <textarea
                className={inputCls}
                rows={3}
                placeholder="Sanitized outcome wording…"
                value={decisionNote}
                onChange={(e) => setDecisionNote(e.target.value)}
              />
              <label className={labelCls}>Internal review note</label>
              <textarea
                className={inputCls}
                rows={2}
                placeholder="Internal only — never exposed to the appellant"
                value={reviewNote}
                onChange={(e) => setReviewNote(e.target.value)}
              />
              <button className={primaryBtn} disabled={busy} onClick={decide}>
                Record decision
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
