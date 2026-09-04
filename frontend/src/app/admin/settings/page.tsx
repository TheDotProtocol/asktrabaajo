"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

import { PageHeader, cardCls, ghostBtnCls } from "@/components/candidate/ui";
import { useCanonicalAuth } from "@/context/AuthContext";
import { api } from "@/lib/api/session";

export default function AdminSettingsPage() {
  const { me } = useCanonicalAuth();
  const [sessions, setSessions] = useState<Array<{ id?: string; created_at?: string; user_agent?: string }>>([]);

  useEffect(() => {
    api
      .get<Array<{ id?: string; created_at?: string; user_agent?: string }>>("/auth/sessions")
      .then(setSessions)
      .catch(() => setSessions([]));
  }, []);

  return (
    <div className="space-y-8">
      <PageHeader
        kicker="Account"
        title="Settings"
        subtitle="This surface shows the permissions the backend already granted. It cannot escalate them."
      />
      <section className={cardCls}>
        <p className="font-medium text-white">{me?.full_name}</p>
        <p className="mt-1 text-sm text-[#9ca3af]">{me?.email}</p>
        <p className="mt-2 font-mono text-[10px] uppercase text-[#6b7280]">
          Super admin: {me?.super_admin ? "yes" : "no"}
        </p>
        <Link href="/id" className={`${ghostBtnCls} mt-4`}>
          Open account security
        </Link>
      </section>
      <section className={cardCls}>
        <p className="font-medium text-white">Granted permissions</p>
        <ul className="mt-3 flex flex-wrap gap-2">
          {(me?.permissions ?? []).map((code) => (
            <li key={code} className="rounded border border-[#23272a] px-2 py-1 font-mono text-[10px] text-[#9ca3af]">
              {code}
            </li>
          ))}
        </ul>
      </section>
      <section className={cardCls}>
        <p className="font-medium text-white">Sessions</p>
        <p className="mt-1 text-sm text-[#9ca3af]">Your own sessions only. There is no platform-wide session browser.</p>
        <ul className="mt-3 space-y-2 text-sm text-[#9ca3af]">
          {sessions.length === 0 && <li>No session list returned for this account.</li>}
          {sessions.map((row, i) => (
            <li key={row.id || i}>
              {row.user_agent || "Session"} {row.created_at ? `· ${new Date(row.created_at).toLocaleString()}` : ""}
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
