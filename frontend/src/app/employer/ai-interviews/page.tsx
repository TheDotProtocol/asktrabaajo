"use client";
/**
 * AI Interviews (employer side) — org-scoped session list, structured
 * report and the human decision step. The AI never decides; this screen is
 * the authorized human's review surface. Candidate narratives are not
 * stored — the report shows structured evidence only.
 */
import { useCallback, useEffect, useState } from "react";

import { PageHeader, btnCls, cardCls } from "@/components/candidate/ui";
import { api } from "@/lib/api/session";
import { useOrg } from "@/context/OrgContext";

interface SessionRow {
  session_id: string;
  candidate_person_id: string;
  interview_type: string;
  status: string;
  question_count: number;
  consent_granted: boolean;
  started_at: string | null;
  completed_at: string | null;
  evaluations_count: number;
  integrity_signals_count: number;
  decision: string | null;
  created_at: string | null;
}

interface Report {
  session_id: string;
  summary: string;
  strengths?: string[];
  improvement_areas?: string[];
  unanswered_areas?: string[];
  interview_quality?: {
    answered: number;
    total_questions: number;
    completion_pct: number;
    average_dimension_score: number | null;
    note: string;
  };
  integrity_signals?: Array<Record<string, string>>;
  disclaimer: string;
  decision?: string | null;
}

const STATUS_LABEL: Record<string, string> = {
  scheduled: "Scheduled",
  consent_required: "Awaiting consent",
  ready: "Ready",
  in_progress: "In progress",
  paused: "Paused",
  completed: "Completed",
  cancelled: "Cancelled",
  expired: "Expired",
  failed: "Failed",
};

export default function EmployerAiInterviewsPage() {
  const { organizationId: orgId, memberships, selectOrganization } = useOrg();
  const orgs = memberships.map((m) => ({
    organization_id: m.organization_id,
    name: m.organization_name,
  }));
  const [rows, setRows] = useState<SessionRow[]>([]);
  const [report, setReport] = useState<Report | null>(null);
  const [selected, setSelected] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    if (!orgId) return;
    setBusy(true);
    setError("");
    setReport(null);
    setSelected("");
    try {
      const data = await api.get<{ interviews: SessionRow[] }>(
        `/ai-interviews?organization_id=${encodeURIComponent(orgId)}`
      );
      setRows(data.interviews);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }, [orgId]);

  useEffect(() => {
    if (orgId) load();
  }, [orgId, load]);

  const openReport = async (sessionId: string) => {
    setSelected(sessionId);
    setBusy(true);
    try {
      const r = await api.get<Report>(
        `/ai-interviews/${sessionId}/report?organization_id=${encodeURIComponent(orgId)}`
      );
      setReport(r);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const decide = async (decision: string) => {
    if (!selected) return;
    setBusy(true);
    try {
      const note =
        decision === "reject"
          ? "Candidate informed through the standard workflow."
          : "Reviewer decision recorded.";
      await api.post(
        `/ai-interviews/${selected}/decision?organization_id=${encodeURIComponent(orgId)}`,
        { decision, note }
      );
      setReport({ ...(report as Report), decision });
      await load();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        kicker="AI Interview Engine"
        title="AI Interviews"
        subtitle="AI-assisted assessment. A human records the hiring decision. Integrity signals are review inputs, not automatic penalties."
      />

      {error && (
        <div className="rounded border border-red-300 bg-red-50 p-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-300">
          {error}
        </div>
      )}

      <div className="flex items-center gap-3">
        <select
          className="rounded border border-neutral-300 px-3 py-2 text-sm dark:border-neutral-700 dark:bg-neutral-900"
          value={orgId}
          onChange={(e) => selectOrganization(e.target.value)}
        >
          {orgs.length === 0 && <option value="">No employer organizations</option>}
          {orgs.map((o) => (
            <option key={o.organization_id} value={o.organization_id}>
              {o.name}
            </option>
          ))}
        </select>
        <button className={btnCls} onClick={load} disabled={busy}>
          Refresh
        </button>
      </div>

      <div className={`${cardCls} overflow-x-auto`}>
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b text-xs uppercase text-neutral-500">
              <th className="py-2 pr-3">Type</th>
              <th className="py-2 pr-3">Status</th>
              <th className="py-2 pr-3">Evaluated</th>
              <th className="py-2 pr-3">Signals</th>
              <th className="py-2 pr-3">Decision</th>
              <th className="py-2" />
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.session_id} className="border-b last:border-0">
                <td className="py-2 pr-3 capitalize">{r.interview_type}</td>
                <td className="py-2 pr-3">
                  {STATUS_LABEL[r.status] ?? r.status}
                </td>
                <td className="py-2 pr-3">{r.evaluations_count}</td>
                <td className="py-2 pr-3">{r.integrity_signals_count}</td>
                <td className="py-2 pr-3">{r.decision ?? "—"}</td>
                <td className="py-2">
                  {r.status === "completed" && (
                    <button
                      className="text-amber-600 hover:underline dark:text-amber-400"
                      onClick={() => openReport(r.session_id)}
                    >
                      Report
                    </button>
                  )}
                </td>
              </tr>
            ))}
            {rows.length === 0 && (
              <tr>
                <td colSpan={6} className="py-4 text-neutral-500">
                  No AI interviews for this organization yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {report && (
        <div className={`${cardCls} space-y-4`}>
          <div className="flex items-center justify-between">
            <h2 className="font-medium">Interview report</h2>
            <span className="text-xs text-neutral-500">
              {report.decision ? `Decision: ${report.decision}` : "No decision yet"}
            </span>
          </div>
          <p className="text-sm text-neutral-600 dark:text-neutral-300">
            {report.summary}
          </p>

          {report.interview_quality && (
            <div className="grid grid-cols-2 gap-2 text-sm sm:grid-cols-4">
              <div className="rounded bg-neutral-50 p-2 dark:bg-neutral-800">
                <div className="text-xs text-neutral-500">Answered</div>
                <div className="font-medium">
                  {report.interview_quality.answered}/
                  {report.interview_quality.total_questions}
                </div>
              </div>
              <div className="rounded bg-neutral-50 p-2 dark:bg-neutral-800">
                <div className="text-xs text-neutral-500">Completion</div>
                <div className="font-medium">
                  {report.interview_quality.completion_pct}%
                </div>
              </div>
              <div className="rounded bg-neutral-50 p-2 dark:bg-neutral-800">
                <div className="text-xs text-neutral-500">Avg. dimension</div>
                <div className="font-medium">
                  {report.interview_quality.average_dimension_score ?? "—"}/5
                </div>
              </div>
              <div className="rounded bg-neutral-50 p-2 dark:bg-neutral-800">
                <div className="text-xs text-neutral-500">Quality note</div>
                <div className="text-xs text-neutral-600 dark:text-neutral-300">
                  {report.interview_quality.note}
                </div>
              </div>
            </div>
          )}

          {report.strengths && report.strengths.length > 0 && (
            <div>
              <h3 className="text-sm font-medium">Strengths</h3>
              <ul className="list-inside list-disc text-sm text-neutral-600 dark:text-neutral-300">
                {report.strengths.map((s) => (
                  <li key={s}>{s}</li>
                ))}
              </ul>
            </div>
          )}
          {report.improvement_areas && report.improvement_areas.length > 0 && (
            <div>
              <h3 className="text-sm font-medium">Areas for further review</h3>
              <ul className="list-inside list-disc text-sm text-neutral-600 dark:text-neutral-300">
                {report.improvement_areas.map((s) => (
                  <li key={s}>{s}</li>
                ))}
              </ul>
            </div>
          )}
          {report.integrity_signals && report.integrity_signals.length > 0 && (
            <div className="rounded border border-amber-300 bg-amber-50 p-3 text-sm dark:border-amber-800 dark:bg-amber-950">
              <h3 className="font-medium">Review signals</h3>
              {report.integrity_signals.map((s, i) => (
                <p key={i} className="text-xs text-amber-800 dark:text-amber-300">
                  {String(s.type)} · {String(s.at)} — review signal only, not
                  proof of wrongdoing.
                </p>
              ))}
            </div>
          )}

          <div className="flex flex-wrap gap-2">
            {report.decision === null &&
              ["advance", "hold", "request_followup", "request_human_interview", "reject"].map(
                (d) => (
                  <button
                    key={d}
                    className="rounded border border-neutral-300 px-3 py-1.5 text-sm capitalize hover:bg-neutral-100 disabled:opacity-50 dark:border-neutral-700 dark:hover:bg-neutral-800"
                    onClick={() => decide(d)}
                    disabled={busy}
                  >
                    {d.replace("_", " ")}
                  </button>
                )
              )}
          </div>
          <p className="text-xs text-neutral-400">{report.disclaimer}</p>
        </div>
      )}
    </div>
  );
}
