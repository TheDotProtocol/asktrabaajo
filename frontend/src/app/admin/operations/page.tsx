"use client";

import { useCallback, useEffect, useState } from "react";

import {
  ErrorBanner,
  LoadingState,
  PageHeader,
  StatusPill,
  cardCls,
} from "@/components/candidate/ui";
import { api } from "@/lib/api/session";
import { AthenaStatus, EventsFeed, PlatformEventRow } from "@/lib/api/types";

export default function AdminOperationsPage() {
  const [status, setStatus] = useState<AthenaStatus | null>(null);
  const [events, setEvents] = useState<PlatformEventRow[]>([]);
  const [error, setError] = useState("");
  const [ready, setReady] = useState(false);

  const load = useCallback(async () => {
    setError("");
    try {
      const [athena, feed] = await Promise.all([
        api.get<AthenaStatus>("/athena/status").catch(() => null),
        api.get<EventsFeed>("/events?limit=30").catch(() => ({ items: [], count: 0, next_after: null })),
      ]);
      setStatus(athena);
      setEvents(feed.items);
    } catch (e) {
      setError(String((e as Error).message ?? e));
    } finally {
      setReady(true);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  if (!ready) return <LoadingState label="Checking platform operations…" />;

  return (
    <div className="space-y-8">
      <PageHeader
        kicker="Operations"
        title="System operations"
        subtitle="Honest provider and event visibility. Rate-limit internals and infrastructure credentials are not APIs and are not shown."
      />
      {error && <ErrorBanner message={error} onRetry={() => void load()} />}

      <div className="grid gap-3 md:grid-cols-2">
        <article className={cardCls}>
          <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-[#9ca3af]">Athena</p>
          <p className="mt-2 text-lg font-semibold">{status?.available ? "Available" : "Unavailable"}</p>
          <p className="mt-1 text-sm text-[#9ca3af]">
            State: {status?.state ?? "unknown"}. Platform-operator mode has no registered tools.
          </p>
        </article>
        <article className={cardCls}>
          <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-[#9ca3af]">Payments</p>
          <p className="mt-2 text-lg font-semibold">Not exposed as a status API</p>
          <p className="mt-1 text-sm text-[#9ca3af]">
            The product default is a mock payment provider. This screen will not pretend a live
            processor is connected.
          </p>
        </article>
        <article className={cardCls}>
          <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-[#9ca3af]">Rate limiting</p>
          <p className="mt-2 text-lg font-semibold">Policy exists, no operator status route</p>
          <p className="mt-1 text-sm text-[#9ca3af]">
            Limits are enforced in the API. There is no canonical rate-limit dashboard.
          </p>
        </article>
        <article className={cardCls}>
          <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-[#9ca3af]">Events</p>
          <p className="mt-2 text-lg font-semibold">{events.length} recent</p>
          <p className="mt-1 text-sm text-[#9ca3af]">Caller-scoped metadata only. No message bodies.</p>
        </article>
      </div>

      <section className="space-y-3">
        <h2 className="text-lg font-semibold">Your operational events</h2>
        {events.length === 0 ? (
          <p className="text-sm text-[#9ca3af]">No events in this feed.</p>
        ) : (
          events.map((row) => (
            <article key={row.id} className={cardCls}>
              <div className="flex items-center justify-between gap-3">
                <p className="font-medium">{row.event_type}</p>
                <StatusPill status={row.read ? "read" : "unread"} tone={row.read ? "muted" : "gold"} />
              </div>
              <p className="mt-1 text-xs text-[#9ca3af]">
                {row.resource_type} · {row.resource_id.slice(0, 8)}…
                {row.created_at ? ` · ${new Date(row.created_at).toLocaleString()}` : ""}
              </p>
            </article>
          ))
        )}
      </section>
    </div>
  );
}
