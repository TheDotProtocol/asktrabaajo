"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";

import {
  EmptyState,
  ErrorBanner,
  LoadingState,
  PageHeader,
  StatusPill,
  btnCls,
  cardCls,
  ghostBtnCls,
  inputCls,
} from "@/components/candidate/ui";
import { useOrg } from "@/context/OrgContext";
import { api } from "@/lib/api/session";

interface OrgMember {
  user_id: string;
  email: string;
  full_name: string;
  role: string;
  created_at: string;
}

export default function MembersPage() {
  const { organizationId } = useOrg();
  const [members, setMembers] = useState<OrgMember[] | null>(null);
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("recruiter");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const load = useCallback(async () => {
    if (!organizationId) return;
    try {
      const data = await api.get<{ members: OrgMember[] }>(`/organizations/${organizationId}/members`);
      setMembers(data.members);
      setError("");
    } catch (e) {
      setError(String((e as Error).message ?? e));
    }
  }, [organizationId]);

  useEffect(() => {
    void load();
  }, [load]);

  async function add(event: FormEvent) {
    event.preventDefault();
    if (!organizationId) return;
    try {
      await api.post(`/organizations/${organizationId}/members`, { user_email: email, role });
      setNotice("Member added. They must already have an AskTrabaajo account.");
      setEmail("");
      await load();
    } catch (e) {
      setError(String((e as Error).message ?? e));
    }
  }

  async function changeRole(userId: string, next: string) {
    if (!organizationId) return;
    try {
      await api.patch(`/organizations/${organizationId}/members/${userId}`, { role: next });
      await load();
    } catch (e) {
      setError(String((e as Error).message ?? e));
    }
  }

  async function remove(userId: string) {
    if (!organizationId || !window.confirm("Remove this member from the organization?")) return;
    try {
      await api.delete(`/organizations/${organizationId}/members/${userId}`);
      await load();
    } catch (e) {
      setError(String((e as Error).message ?? e));
    }
  }

  if (!organizationId) {
    return <EmptyState title="Select an organization" body="Membership is organization-scoped." actionHref="/company" actionLabel="Command center" />;
  }
  if (error && !members) return <ErrorBanner message={error} onRetry={() => void load()} />;
  if (!members) return <LoadingState />;

  return (
    <div className="space-y-8">
      <PageHeader
        kicker="Workforce"
        title="Organization members"
        subtitle="Roles come from canonical RBAC. This page cannot invent permissions — the backend decides what each role may do."
      />
      {error && <ErrorBanner message={error} />}
      {notice && <p className="text-sm text-emerald-400">{notice}</p>}

      <form onSubmit={add} className={`${cardCls} grid gap-3 sm:grid-cols-3`}>
        <input className={inputCls} type="email" required placeholder="Existing user email" value={email} onChange={(e) => setEmail(e.target.value)} />
        <select className={inputCls} value={role} onChange={(e) => setRole(e.target.value)}>
          <option value="org_admin">org_admin</option>
          <option value="recruiter">recruiter</option>
          <option value="hiring_manager">hiring_manager</option>
          <option value="interviewer">interviewer</option>
        </select>
        <button type="submit" className={btnCls}>Add member</button>
      </form>

      {members.length === 0 ? (
        <EmptyState title="No members returned" body="You may lack members.read, or the organization is empty." />
      ) : (
        <ul className="space-y-3">
          {members.map((m) => (
            <li key={m.user_id} className={`${cardCls} flex flex-wrap items-center justify-between gap-3`}>
              <div>
                <p className="font-medium">{m.full_name}</p>
                <p className="text-xs text-[#9ca3af]">{m.email}</p>
              </div>
              <div className="flex items-center gap-2">
                <StatusPill status={m.role} />
                <select className={`${inputCls} w-auto`} value={m.role} onChange={(e) => void changeRole(m.user_id, e.target.value)}>
                  <option value="org_admin">org_admin</option>
                  <option value="recruiter">recruiter</option>
                  <option value="hiring_manager">hiring_manager</option>
                  <option value="interviewer">interviewer</option>
                </select>
                <button type="button" className={ghostBtnCls} onClick={() => void remove(m.user_id)}>Remove</button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
