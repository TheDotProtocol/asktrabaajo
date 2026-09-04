"use client";
/**
 * Governance teams (Phase 10 proof).
 *
 * Teams organize the queue and workload — they are not an authorization
 * mechanism (platform roles + reports.* permissions stay authoritative).
 * Workload views exist for routing, never productivity policing.
 */
import { useCallback, useEffect, useState } from "react";

import { api } from "@/lib/api/session";
import {
  GovernanceModeratorRow,
  GovernanceTeamDetail,
  GovernanceTeamRow,
} from "@/lib/api/types";

import { PageHeader, cardCls, ghostBtnCls, inputCls } from "@/components/candidate/ui";
const ghostBtn = ghostBtnCls;
const dangerBtn =
  "rounded border border-red-200 px-2 py-0.5 text-xs text-red-600 hover:bg-red-50 dark:border-red-900 dark:text-red-400";

export default function GovernanceTeamsPage() {
  const [teams, setTeams] = useState<GovernanceTeamRow[]>([]);
  const [detail, setDetail] = useState<GovernanceTeamDetail | null>(null);
  const [moderators, setModerators] = useState<GovernanceModeratorRow[]>([]);
  const [picker, setPicker] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [forbidden, setForbidden] = useState(false);

  const load = useCallback(async () => {
    setError("");
    try {
      const [t, m] = await Promise.all([
        api.get<{ items: GovernanceTeamRow[] }>("/governance/teams"),
        api.get<{ items: GovernanceModeratorRow[] }>("/governance/moderators"),
      ]);
      setTeams(t.items);
      setModerators(m.items);
    } catch (e) {
      const err = e as { status?: number; message?: string };
      if (err.status === 403) setForbidden(true);
      setError(String(err.message ?? e));
    }
  }, []);

  const openDetail = useCallback(async (teamId: string) => {
    setDetail(null);
    try {
      const d = await api.get<GovernanceTeamDetail>(`/governance/teams/${teamId}`);
      setDetail(d);
    } catch (e) {
      setError(String((e as Error).message ?? e));
    }
  }, []);

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

  async function addMember(teamId: string) {
    const userId = picker[teamId];
    if (!userId) return;
    setBusy(true);
    setError("");
    try {
      await api.post(`/governance/teams/${teamId}/members`, { user_id: userId });
      setPicker((p) => ({ ...p, [teamId]: "" }));
      await Promise.all([load(), detail && openDetail(teamId)]);
    } catch (e) {
      setError(String((e as Error).message ?? e));
    } finally {
      setBusy(false);
    }
  }

  async function removeMember(teamId: string, userId: string) {
    setBusy(true);
    setError("");
    try {
      await api.delete(`/governance/teams/${teamId}/members/${userId}`);
      await Promise.all([load(), openDetail(teamId)]);
    } catch (e) {
      setError(String((e as Error).message ?? e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        kicker="Teams"
        title="Governance teams"
        subtitle="Operational routing and workload only. Authorization stays on platform roles and reports.* permissions."
      />

      {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {teams.map((team) => (
          <div key={team.id} className={`${cardCls} flex flex-col gap-2`}>
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm font-semibold">{team.name}</p>
                <p className="text-[11px] text-neutral-400">{team.slug}</p>
              </div>
              <button
                onClick={() => openDetail(team.id)}
                disabled={busy}
                className={ghostBtn}
              >
                Open
              </button>
            </div>
            <p className="line-clamp-2 text-xs text-neutral-500">
              {team.description}
            </p>
            <div className="mt-auto flex gap-3 text-xs text-neutral-500">
              <span>
                <span className="font-semibold text-neutral-700 dark:text-neutral-200">
                  {team.open_cases}
                </span>{" "}
                open
              </span>
              <span>
                <span className="font-semibold text-neutral-700 dark:text-neutral-200">
                  {team.member_count}
                </span>{" "}
                members
              </span>
            </div>
            {detail?.id === team.id ? null : (
              <div className="flex gap-1.5">
                <select
                  value={picker[team.id] ?? ""}
                  onChange={(e) =>
                    setPicker((p) => ({ ...p, [team.id]: e.target.value }))
                  }
                  className={`${inputCls} min-w-0 flex-1 py-1 text-xs`}
                >
                  <option value="">Add member…</option>
                  {moderators.map((m) => (
                    <option key={m.user_id} value={m.user_id}>
                      {m.full_name}
                    </option>
                  ))}
                </select>
                <button
                  onClick={() => addMember(team.id)}
                  disabled={busy || !picker[team.id]}
                  className={ghostBtn}
                >
                  Add
                </button>
              </div>
            )}
          </div>
        ))}
      </div>

      {detail && (
        <div className={`${cardCls} space-y-4`}>
          <div className="flex flex-wrap items-center gap-3">
            <h2 className="text-lg font-semibold">{detail.name}</h2>
            <span className="rounded bg-neutral-100 px-2 py-0.5 text-xs text-neutral-500 dark:bg-neutral-800">
              {detail.slug}
            </span>
            <button
              onClick={() => setDetail(null)}
              className="ml-auto text-xs text-neutral-500 hover:text-neutral-800 dark:hover:text-neutral-200"
            >
              Close
            </button>
          </div>

          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {[
              { label: "Open", value: detail.counts.open },
              { label: "Urgent", value: detail.counts.urgent },
              { label: "Breached", value: detail.counts.breached },
              { label: "Unresolved", value: detail.counts.unresolved },
            ].map((stat) => (
              <div
                key={stat.label}
                className="rounded-lg border border-neutral-200 p-3 dark:border-neutral-800"
              >
                <div className="text-xl font-semibold">{stat.value}</div>
                <div className="text-xs text-neutral-500">{stat.label}</div>
              </div>
            ))}
          </div>

          <div>
            <p className="text-xs font-medium text-neutral-500">Members</p>
            {detail.members.length === 0 && (
              <p className="mt-1 text-sm text-neutral-400">No members yet.</p>
            )}
            <ul className="mt-2 space-y-1.5">
              {detail.members.map((member) => (
                <li
                  key={member.user_id}
                  className="flex items-center gap-2 text-sm"
                >
                  <span className="h-2 w-2 rounded-full bg-indigo-400" />
                  {member.full_name}
                  <span className="text-xs text-neutral-400">
                    {member.user_id.slice(0, 8)}…
                  </span>
                  <button
                    onClick={() => removeMember(detail.id, member.user_id)}
                    disabled={busy}
                    className={`${dangerBtn} ml-auto`}
                  >
                    Remove
                  </button>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}
