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
import { EventsFeed, PlatformEventRow, UserNotification } from "@/lib/api/types";

export default function AdminNotificationsPage() {
  const [items, setItems] = useState<UserNotification[] | null>(null);
  const [events, setEvents] = useState<PlatformEventRow[]>([]);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      const [notes, feed] = await Promise.all([
        api.get<UserNotification[]>("/jobseeker/notifications"),
        api.get<EventsFeed>("/events?limit=40").catch(() => ({ items: [], count: 0, next_after: null })),
      ]);
      setItems(notes);
      setEvents(feed.items);
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
    <div className="space-y-8">
      <PageHeader
        kicker="Inbox"
        title="Notifications"
        subtitle="Caller-scoped notifications and operational events. No fabricated governance alerts."
        actions={
          items.length > 0 ? (
            <button type="button" className={btnCls} onClick={() => void api.post("/jobseeker/notifications/read-all").then(load)}>
              Mark all read
            </button>
          ) : null
        }
      />
      {error && <ErrorBanner message={error} />}
      {items.length === 0 ? (
        <EmptyState title="No account notifications" body="Governance and finance activity appears here only when the backend writes a notification for this user." />
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
      <section className="space-y-3">
        <h2 className="text-lg font-semibold">Operational events</h2>
        {events.length === 0 ? (
          <p className="text-sm text-[#9ca3af]">No events in the authorized feed.</p>
        ) : (
          events.map((row) => (
            <article key={row.id} className={cardCls}>
              <p className="font-medium">{row.event_type}</p>
              <p className="text-xs text-[#9ca3af]">
                {row.resource_type} · {row.created_at ? new Date(row.created_at).toLocaleString() : ""}
              </p>
            </article>
          ))
        )}
      </section>
    </div>
  );
}
