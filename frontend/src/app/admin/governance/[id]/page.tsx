"use client";
/**
 * Governance case detail (Phase 10 proof).
 *
 * Moderator surface: case header (case ref, category, severity, priority,
 * status, SLA state, team, assignee), summary, lifecycle actions (assign,
 * change priority, route to team, escalate, add notes, resolve, reopen),
 * linked reports, and the audit timeline. It never fabricates access to the
 * target's Work ID — and escalation reasons never enter audit/event payloads.
 */
import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";

import { api } from "@/lib/api/session";
import {
  GovernanceReportRow,
  GovernanceTeamRow,
  GovernanceModeratorRow,
} from "@/lib/api/types";

const STATUSES = ["open", "in_review", "assigned", "escalated", "resolved", "closed"];
const PRIORITIES = ["low", "normal", "high", "urgent", "critical"];

const statusStyle: Record<string, string> = {
  open: "bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-300",
  in_review: "bg-indigo-100 text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300",
  assigned: "bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300",
  escalated: "bg-purple-100 text-purple-700 dark:bg-purple-950 dark:text-purple-300",
  resolved: "bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-400",
  closed: "bg-neutral-100 text-neutral-600 dark:bg-neutral-800 dark:text-neutral-300",
};

const slaStyle: Record<string, string> = {
  on_track: "bg-emerald-50 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-400",
  due_soon: "bg-amber-50 text-amber-700 dark:bg-amber-950 dark:text-amber-300",
  breached: "bg-red-50 text-red-700 dark:bg-red-950 dark:text-red-300",
};

const cardCls =
  "rounded-xl border border-neutral-200 bg-white p-5 dark:border-neutral-800 dark:bg-neutral-900";
const primaryBtn =
  "rounded bg-indigo-500 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-600 disabled:opacity-40";
const ghostBtn =
  "rounded border border-neutral-300 px-3 py-1.5 text-sm text-neutral-600 hover:border-indigo-400 dark:border-neutral-700 dark:text-neutral-300";
const inputCls =
  "w-full rounded border border-neutral-300 bg-white px-3 py-2 text-sm dark:border-neutral-700 dark:bg-neutral-900";
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

export default function GovernanceCaseDetailPage() {
  const params = useParams();
  const caseId = String(params?.id ?? "");
  const [report, setReport] = useState<GovernanceReportRow | null>(null);
  const [teams, setTeams] = useState<GovernanceTeamRow[]>([]);
  const [moderators, setModerators] = useState<GovernanceModeratorRow[]>([]);
  const [note, setNote] = useState("");
  const [resolution, setResolution] = useState("");
  const [linkId, setLinkId] = useState("");
  const [escalateReason, setEscalateReason] = useState("");
  const [escalatePriority, setEscalatePriority] = useState("high");
  const [escalateTeam, setEscalateTeam] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [forbidden, setForbidden] = useState(false);

  const load = useCallback(async () => {
    if (!caseId) return;
    setError("");
    try {
      const [r, t, m] = await Promise.all([
        api.get<GovernanceReportRow>(`/governance/reports/${caseId}`),
        api.get<{ items: GovernanceTeamRow[] }>("/governance/teams"),
        api.get<{ items: GovernanceModeratorRow[] }>("/governance/moderators"),
      ]);
      setReport(r);
      setTeams(t.items);
      setModerators(m.items);
    } catch (e) {
      const err = e as { status?: number; message?: string };
      if (err.status === 403) setForbidden(true);
      setError(String(err.message ?? e));
    }
  }, [caseId]);

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
        {error ? `Could not load case: ${error}` : "Loading case…"}
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
    await run(() => api.patch(`/governance/reports/${caseId}/status`, { status }));
  }

  async function changePriority(priority: string) {
    await run(() => api.post(`/governance/reports/${caseId}/priority`, { priority }));
  }

  async function routeTeam(teamId: string) {
    await run(() =>
      api.post(`/governance/reports/${caseId}/team`, {
        team_id: teamId || null,
      })
    );
  }

  async function assignTo(userId: string) {
    await run(() =>
      api.post(`/governance/reports/${caseId}/assign`, {
        moderator_user_id: userId || null,
      })
    );
  }

  async function escalate() {
    const reason = escalateReason.trim();
    if (reason.length < 10) {
      setError("An escalation reason of at least 10 characters is required.");
      return;
    }
    await run(async () => {
      await api.post(`/governance/reports/${caseId}/escalate`, {
        reason,
        priority: escalatePriority,
        team_id: escalateTeam || null,
      });
      setEscalateReason("");
      setEscalatePriority("high");
      setEscalateTeam("");
    });
  }

  async function addNote() {
    const body = note.trim();
    if (!body) return;
    await run(async () => {
      await api.post(`/governance/reports/${caseId}/notes`, { body });
      setNote("");
    });
  }

  async function addLink() {
    if (!linkId.trim()) return;
    await run(async () => {
      await api.post(`/governance/reports/${caseId}/links`, {
        report_id: linkId.trim(),
        reason: "Linked during investigation to avoid duplicate work.",
      });
      setLinkId("");
    });
  }

  async function removeLink(linkId: string) {
    await run(() => api.delete(`/governance/reports/${caseId}/links/${linkId}`));
  }

  async function resolve() {
    const body = resolution.trim();
    if (body.length < 10) {
      setError("Resolution must be at least 10 characters.");
      return;
    }
    await run(async () => {
      await api.post(`/governance/reports/${caseId}/resolve`, { resolution: body });
      setResolution("");
    });
  }

  async function reopen() {
    await run(() => api.post(`/governance/reports/${caseId}/reopen`));
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start gap-3">
        <Link
          href="/admin/governance"
          className="mt-1 text-sm text-neutral-500 hover:text-neutral-800 dark:hover:text-neutral-200"
        >
          ← Control room
        </Link>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="text-sm font-medium text-neutral-400">
              {report.case_ref ?? report.id.slice(0, 8)}
            </span>
            <span
              className={`rounded px-1.5 py-0.5 text-xs font-medium ${statusStyle[report.status] ?? ""}`}
            >
              {titleCase(report.status)}
            </span>
            {report.sla_state && (
              <span
                className={`rounded px-1.5 py-0.5 text-xs font-medium ${slaStyle[report.sla_state] ?? ""}`}
              >
                SLA {titleCase(report.sla_state)}
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
            {report.reopened_count > 0 && (
              <span className="rounded bg-amber-100 px-1.5 py-0.5 text-xs text-amber-700 dark:bg-amber-950 dark:text-amber-300">
                Reopened ×{report.reopened_count}
              </span>
            )}
          </div>
          <h1 className="mt-2 text-xl font-semibold tracking-tight">
            {titleCase(report.target_type)} case
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

      <div className="grid gap-4 lg:grid-cols-3">
        <div className={`${cardCls} space-y-4 lg:col-span-2`}>
          <h2 className="text-sm font-semibold text-neutral-700 dark:text-neutral-200">
            Case summary
          </h2>
          <p className="text-sm leading-relaxed text-neutral-700 dark:text-neutral-300">
            {report.description}
          </p>
          {report.evidence_refs.length > 0 && (
            <div>
              <p className="text-xs font-medium text-neutral-500">
                Evidence references
              </p>
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

          <div className="grid gap-3 border-t border-neutral-200 pt-4 sm:grid-cols-2 dark:border-neutral-800">
            <div>
              <label className="text-xs font-medium text-neutral-500">
                Assignee
              </label>
              <select
                value={report.assigned_moderator_id ?? ""}
                onChange={(e) => assignTo(e.target.value)}
                disabled={busy}
                className={`${selectCls} mt-1 w-full`}
              >
                <option value="">Unassigned</option>
                {moderators.map((m) => (
                  <option key={m.user_id} value={m.user_id}>
                    {m.full_name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs font-medium text-neutral-500">Team</label>
              <select
                value={report.team_id ?? ""}
                onChange={(e) => routeTeam(e.target.value)}
                disabled={busy}
                className={`${selectCls} mt-1 w-full`}
              >
                <option value="">No team</option>
                {teams.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs font-medium text-neutral-500">
                Priority (restarts SLA clock)
              </label>
              <select
                value={report.priority ?? "normal"}
                onChange={(e) => changePriority(e.target.value)}
                disabled={busy || isResolved}
                className={`${selectCls} mt-1 w-full`}
              >
                {PRIORITIES.map((p) => (
                  <option key={p} value={p}>
                    {titleCase(p)}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs font-medium text-neutral-500">Status</label>
              <select
                value={report.status}
                onChange={(e) => changeStatus(e.target.value)}
                disabled={busy}
                className={`${selectCls} mt-1 w-full`}
              >
                {STATUSES.filter((s) => s !== "escalated").map((s) => (
                  <option key={s} value={s}>
                    {titleCase(s)}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {report.sla_resolution_due_at && !isResolved && (
            <p className="text-xs text-neutral-500">
              Response due {fmt(report.sla_response_due_at)} · Resolution due{" "}
              {fmt(report.sla_resolution_due_at)}
              {report.first_responded_at
                ? ` · First response ${fmt(report.first_responded_at)}`
                : " · No first response yet"}
            </p>
          )}

          {!isResolved && (
            <div className="rounded-lg border border-purple-200 bg-purple-50 p-3 dark:border-purple-900 dark:bg-purple-950/40">
              <p className="text-xs font-medium text-purple-700 dark:text-purple-300">
                Escalate
              </p>
              <div className="mt-2 flex flex-wrap items-end gap-2">
                <select
                  value={escalatePriority}
                  onChange={(e) => setEscalatePriority(e.target.value)}
                  className={selectCls}
                >
                  {PRIORITIES.map((p) => (
                    <option key={p} value={p}>
                      {titleCase(p)}
                    </option>
                  ))}
                </select>
                <select
                  value={escalateTeam}
                  onChange={(e) => setEscalateTeam(e.target.value)}
                  className={selectCls}
                >
                  <option value="">Keep team</option>
                  {teams.map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.name}
                    </option>
                  ))}
                </select>
                <input
                  value={escalateReason}
                  onChange={(e) => setEscalateReason(e.target.value)}
                  placeholder="Escalation reason (recorded, never logged verbatim)"
                  className={`${inputCls} min-w-52 flex-1`}
                />
                <button onClick={escalate} disabled={busy} className={ghostBtn}>
                  Escalate
                </button>
              </div>
            </div>
          )}

          <div className="flex flex-wrap gap-2 border-t border-neutral-200 pt-4 dark:border-neutral-800">
            {!isResolved && (
              <button
                onClick={resolve}
                disabled={busy || resolution.trim().length < 10}
                className={primaryBtn}
              >
                Resolve
              </button>
            )}
            {isResolved && (
              <button onClick={reopen} disabled={busy} className={ghostBtn}>
                Reopen
              </button>
            )}
          </div>
          {!isResolved && (
            <textarea
              value={resolution}
              onChange={(e) => setResolution(e.target.value)}
              rows={2}
              placeholder="Resolution action (recorded in the case and audit)…"
              className={inputCls}
            />
          )}
        </div>

        <div className="space-y-4">
          <div className={`${cardCls} space-y-3`}>
            <h2 className="text-sm font-semibold text-neutral-700 dark:text-neutral-200">
              Linked reports
            </h2>
            {(report.links ?? []).length === 0 && (
              <p className="text-sm text-neutral-500">No linked reports.</p>
            )}
            <ul className="space-y-1.5">
              {(report.links ?? []).map((link) => (
                <li
                  key={link.link_id}
                  className="flex items-center gap-2 rounded-lg bg-neutral-50 p-2 text-xs dark:bg-neutral-950"
                >
                  <Link
                    href={`/admin/governance/${link.report_id}`}
                    className="font-medium text-indigo-600 hover:underline dark:text-indigo-400"
                  >
                    {link.case_ref}
                  </Link>
                  <span className="text-neutral-400">{link.category}</span>
                  <button
                    onClick={() => removeLink(link.link_id)}
                    className="ml-auto text-neutral-400 hover:text-red-600"
                  >
                    Remove
                  </button>
                </li>
              ))}
            </ul>
            <div className="flex gap-2">
              <input
                value={linkId}
                onChange={(e) => setLinkId(e.target.value)}
                placeholder="Report UUID to link…"
                className={inputCls}
              />
              <button
                onClick={addLink}
                disabled={busy || !linkId.trim()}
                className={ghostBtn}
              >
                Link
              </button>
            </div>
          </div>

          <div className={`${cardCls} space-y-3`}>
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
              <button
                onClick={addNote}
                disabled={busy || !note.trim()}
                className={primaryBtn}
              >
                Add
              </button>
            </div>
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
