"use client";

import { useCallback, useEffect, useState } from "react";

import {
  EmptyState,
  ErrorBanner,
  LoadingState,
  PageHeader,
  btnCls,
  cardCls,
} from "@/components/candidate/ui";
import { api } from "@/lib/api/session";
import { UserNotification } from "@/lib/api/types";

export default function CompanyNotificationsPage() {
  const [items, setItems] = useState<UserNotification[] | null>(null);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      setItems(await api.get<UserNotification[]>("/jobseeker/notifications"));
      setError("");
    } catch (e) {
      setError(String((e as Error).message ?? e));
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  if (error && !items) return <ErrorBanner message={error} onRetry={() => void load()} />;
  if (!items) return <LoadingState />;

  return (
    <div className="space-y-6">
      <PageHeader
        kicker="Inbox"
        title="Notifications"
        subtitle="User-scoped platform records. The same canonical notification API used by the Candidate OS — nothing is invented for employers."
        actions={
          items.length > 0 ? (
            <button type="button" className={btnCls} onClick={() => void api.post("/jobseeker/notifications/read-all").then(load)}>
              Mark all read
            </button>
          ) : null
        }
      />
      {items.length === 0 ? (
        <EmptyState title="No notifications" body="Application, interview, offer, and outreach events will appear here when the backend records them." />
      ) : (
        <ul className="space-y-3">
          {items.map((item) => (
            <li key={item.id} className={`${cardCls} ${item.read_at ? "opacity-70" : ""}`}>
              <p className="font-medium">{item.title}</p>
              {item.body && <p className="mt-1 text-sm text-[#9ca3af]">{item.body}</p>}
              <p className="mt-2 font-mono text-[10px] uppercase text-[#6b7280]">
                {item.kind} · {new Date(item.created_at).toLocaleString()}
              </p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
