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

export default function NotificationsPage() {
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

  async function markOne(id: string) {
    await api.post(`/jobseeker/notifications/${id}/read`);
    await load();
  }

  async function markAll() {
    await api.post("/jobseeker/notifications/read-all");
    await load();
  }

  if (error && !items) return <ErrorBanner message={error} onRetry={() => void load()} />;
  if (!items) return <LoadingState />;

  return (
    <div className="space-y-6">
      <PageHeader
        kicker="Inbox"
        title="Notifications"
        subtitle="These records come from the platform. Nothing here is invented in the browser."
        actions={
          items.length > 0 ? (
            <button type="button" className={btnCls} onClick={() => void markAll()}>
              Mark all read
            </button>
          ) : null
        }
      />
      {error && <ErrorBanner message={error} />}
      {items.length === 0 ? (
        <EmptyState
          title="You are all caught up"
          body="When applications, interviews, or document requests move, they will appear here."
          actionHref="/jobseeker/opportunities"
          actionLabel="Browse opportunities"
        />
      ) : (
        <ul className="space-y-3">
          {items.map((item) => (
            <li key={item.id} className={`${cardCls} ${item.read_at ? "opacity-70" : ""}`}>
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="font-medium">{item.title}</p>
                  {item.body && <p className="mt-1 text-sm text-[#9ca3af]">{item.body}</p>}
                  <p className="mt-2 font-mono text-[10px] uppercase text-[#6b7280]">
                    {item.kind} · {new Date(item.created_at).toLocaleString()}
                  </p>
                </div>
                {!item.read_at && (
                  <button type="button" className="text-xs text-[#d4af37]" onClick={() => void markOne(item.id)}>
                    Mark read
                  </button>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
