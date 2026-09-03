"use client";
/**
 * Jobseeker Communication Center (Phase 8 proof).
 *
 * The candidate always knows WHO contacted them, WHY, WHICH opportunity it
 * relates to — and that their private contact details were never shared.
 * Accepting only opens an AskTrabaajo-controlled conversation.
 */
import { useCallback, useEffect, useRef, useState } from "react";

import { api } from "@/lib/api/session";
import {
  CommunicationsInbox,
  ConversationRow,
  EventsFeed,
  OutreachRequestRow,
} from "@/lib/api/types";

const cardCls =
  "rounded-xl border border-neutral-200 bg-white p-5 dark:border-neutral-800 dark:bg-neutral-900";
const primaryBtn =
  "rounded bg-amber-500 px-3 py-1.5 text-sm font-medium text-white hover:bg-amber-600 disabled:opacity-40";
const ghostBtn =
  "rounded border border-neutral-300 px-3 py-1.5 text-sm text-neutral-600 hover:border-amber-500 dark:border-neutral-700 dark:text-neutral-300";
const inputCls =
  "w-full rounded border border-neutral-300 bg-white px-3 py-2 text-sm dark:border-neutral-700 dark:bg-neutral-900";

const statusStyle: Record<string, string> = {
  sent: "bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-300",
  viewed: "bg-indigo-100 text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300",
  accepted: "bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-400",
  declined: "bg-neutral-100 text-neutral-600 dark:bg-neutral-800 dark:text-neutral-300",
  expired: "bg-neutral-100 text-neutral-500 dark:bg-neutral-800 dark:text-neutral-400",
  cancelled: "bg-neutral-100 text-neutral-500 dark:bg-neutral-800 dark:text-neutral-400",
  blocked: "bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300",
};

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

export default function JobseekerCommunicationsPage() {
  const [inbox, setInbox] = useState<CommunicationsInbox | null>(null);
  const [selected, setSelected] = useState<ConversationRow | null>(null);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [live, setLive] = useState(false);
  const cursorRef = useRef<string | null>(null);

  const load = useCallback(async () => {
    try {
      const data = await api.get<CommunicationsInbox>("/jobseeker/communications");
      setInbox(data);
      setError("");
    } catch (e) {
      setError(String((e as Error).message ?? e));
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  // Phase 9 realtime foundation: poll the canonical event feed (metadata only
  // — never message bodies) and refresh the inbox on new events. A managed
  // WebSocket/SSE transport replaces this loop later without UI changes.
  useEffect(() => {
    let disposed = false;
    const poll = async () => {
      try {
        const params = new URLSearchParams({ limit: "25" });
        if (cursorRef.current) params.set("after", cursorRef.current);
        const feed = await api.get<EventsFeed>(`/events?${params.toString()}`);
        if (disposed) return;
        if (feed.items.length > 0) {
          cursorRef.current = feed.next_after;
          setLive(true);
          window.setTimeout(() => setLive(false), 4000);
          void load();
        }
      } catch {
        /* transient poll failure — the next tick retries */
      }
    };
    const timer = window.setInterval(poll, 12_000);
    return () => {
      disposed = true;
      window.clearInterval(timer);
    };
  }, [load]);

  async function openConversation(conv: ConversationRow) {
    setSelected(null);
    try {
      const detail = await api.get<ConversationRow>(
        `/jobseeker/communications/${conv.id}`
      );
      setSelected(detail);
      await api.post(`/jobseeker/communications/${conv.id}/read`);
      void load();
    } catch (e) {
      setError(String((e as Error).message ?? e));
    }
  }

  async function sendMessage() {
    if (!selected || !draft.trim()) return;
    setBusy(true);
    setError("");
    try {
      await api.post(`/jobseeker/communications/${selected.id}/messages`, {
        body: draft.trim(),
      });
      setDraft("");
      await openConversation(selected);
    } catch (e) {
      setError(String((e as Error).message ?? e));
    } finally {
      setBusy(false);
    }
  }

  async function outreachAction(
    request: OutreachRequestRow,
    action: "accept" | "decline" | "report"
  ) {
    setBusy(true);
    setError("");
    try {
      await api.post(`/jobseeker/outreach/${request.id}/${action}`, {});
      await load();
    } catch (e) {
      setError(String((e as Error).message ?? e));
    } finally {
      setBusy(false);
    }
  }

  async function closeConversation() {
    if (!selected) return;
    setBusy(true);
    try {
      const closed = await api.post<ConversationRow>(
        `/jobseeker/communications/${selected.id}/close`
      );
      setSelected(closed);
      await load();
    } catch (e) {
      setError(String((e as Error).message ?? e));
    } finally {
      setBusy(false);
    }
  }

  const outreach = inbox?.outreach ?? [];
  const conversations = inbox?.conversations ?? [];
  const pending = outreach.filter((r) =>
    ["sent", "viewed"].includes(r.status)
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-2xl font-semibold tracking-tight">Messages</h1>
        {live && (
          <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-100 px-2.5 py-1 text-xs font-medium text-emerald-700 dark:bg-emerald-950 dark:text-emerald-400">
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-500" />
            Updated
          </span>
        )}
      </div>
      <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
        Communication with employers happens here, through AskTrabaajo — your
        contact details are never shared with them.
      </p>

      {error && (
        <div className="rounded-lg border border-red-300 bg-red-50 px-4 py-2 text-sm text-red-700 dark:border-red-900 dark:bg-red-950 dark:text-red-300">
          {error}
        </div>
      )}

      {/* Outreach requests — candidate controls acceptance */}
      <section className={cardCls}>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-sm font-semibold">New opportunities</h2>
          <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-700 dark:bg-amber-950 dark:text-amber-400">
            {pending.length} awaiting your decision
          </span>
        </div>

        {outreach.length === 0 && (
          <p className="mt-4 text-sm text-neutral-400">
            No outreach yet. Companies who find your public profile may request
            contact — you stay in control.
          </p>
        )}

        <div className="mt-4 space-y-4">
          {outreach.map((request) => {
            const actionable = ["sent", "viewed"].includes(request.status);
            return (
              <div
                key={request.id}
                className="rounded-lg border border-neutral-200 p-4 dark:border-neutral-800"
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="font-medium">
                      {request.organization?.name ?? "Company"}
                      {request.opportunity?.title
                        ? ` · ${request.opportunity.title}`
                        : ""}
                    </p>
                    {request.opportunity?.company && (
                      <p className="text-xs text-neutral-400">
                        {request.opportunity.company}
                      </p>
                    )}
                    <p className="mt-2 text-sm text-neutral-600 dark:text-neutral-300">
                      “{request.message}”
                    </p>
                    {request.context && (
                      <p className="mt-1 text-xs text-neutral-400">
                        {request.context}
                      </p>
                    )}
                    <p className="mt-2 text-xs text-neutral-400">
                      Received {fmt(request.created_at)}
                      {request.expires_at ? ` · responds by ${fmt(request.expires_at)}` : ""}
                    </p>
                  </div>
                  <div className="flex flex-col items-end gap-2">
                    <span
                      className={`rounded-full px-2.5 py-1 text-xs capitalize ${statusStyle[request.status] ?? ""}`}
                    >
                      {request.status}
                    </span>
                    {actionable && (
                      <div className="flex gap-2">
                        <button
                          className={primaryBtn}
                          disabled={busy}
                          onClick={() => outreachAction(request, "accept")}
                        >
                          Accept contact
                        </button>
                        <button
                          className={ghostBtn}
                          disabled={busy}
                          onClick={() => outreachAction(request, "decline")}
                        >
                          Decline
                        </button>
                        <button
                          className="text-xs text-red-500 hover:underline disabled:opacity-40"
                          disabled={busy}
                          onClick={() => outreachAction(request, "report")}
                          title="Decline and block this organization from contacting you again"
                        >
                          Block & report
                        </button>
                      </div>
                    )}
                    {request.conversation_id && (
                      <p className="text-xs text-emerald-600 dark:text-emerald-400">
                        Conversation open — accepting created a secure thread.
                      </p>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* Conversations */}
      <section className={cardCls}>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-sm font-semibold">Active conversations</h2>
          {inbox && inbox.unread.unread_messages > 0 && (
            <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-700 dark:bg-amber-950 dark:text-amber-400">
              {inbox.unread.unread_messages} unread
            </span>
          )}
        </div>

        {conversations.length === 0 && (
          <p className="mt-4 text-sm text-neutral-400">
            No conversations yet. Accepting an outreach request (or applying to
            a company) is what opens one.
          </p>
        )}

        {conversations.length > 0 && (
          <div className="mt-4 grid gap-4 lg:grid-cols-[280px_1fr]">
            <div className="space-y-2">
              {conversations.map((conv) => (
                <button
                  key={conv.id}
                  onClick={() => openConversation(conv)}
                  className={`w-full rounded-lg border p-3 text-left text-sm transition ${
                    selected?.id === conv.id
                      ? "border-amber-400 bg-amber-50 dark:bg-amber-950/40"
                      : "border-neutral-200 hover:border-amber-300 dark:border-neutral-800"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-medium">
                      {conv.organization.name ?? "Company"}
                    </span>
                    {conv.unread_count > 0 && (
                      <span className="rounded-full bg-amber-500 px-1.5 py-0.5 text-[10px] font-medium text-white">
                        {conv.unread_count}
                      </span>
                    )}
                  </div>
                  <p className="mt-0.5 truncate text-neutral-500 dark:text-neutral-400">
                    {conv.opportunity_title ?? "Conversation"}
                  </p>
                  <p className="text-[10px] uppercase tracking-wide text-neutral-400">
                    {conv.status}
                  </p>
                </button>
              ))}
            </div>

            <div className="flex min-h-[320px] flex-col rounded-lg border border-neutral-200 p-4 dark:border-neutral-800">
              {!selected && (
                <p className="m-auto text-sm text-neutral-400">
                  Select a conversation to read and reply.
                </p>
              )}
              {selected && (
                <>
                  <div className="flex items-start justify-between gap-2 border-b border-neutral-200 pb-3 dark:border-neutral-800">
                    <div>
                      <p className="font-medium">
                        {selected.organization.name ?? "Company"}
                      </p>
                      <p className="text-xs text-neutral-400">
                        {selected.opportunity_title ?? "Opportunity"}
                        {selected.status === "closed"
                          ? " · conversation closed"
                          : ` · speaking with ${selected.counterpart ?? "recruiter"}`}
                      </p>
                    </div>
                    {selected.status === "active" && (
                      <button
                        className="text-xs text-neutral-400 underline-offset-2 hover:underline"
                        onClick={closeConversation}
                      >
                        Close conversation
                      </button>
                    )}
                  </div>

                  <div className="flex-1 space-y-3 overflow-y-auto py-4">
                    {(selected.messages ?? []).map((m) => {
                      const mine = m.sender_side === "candidate";
                      return (
                        <div
                          key={m.id}
                          className={`max-w-[80%] rounded-lg px-3 py-2 text-sm ${
                            mine
                              ? "ml-auto bg-amber-100 text-amber-900 dark:bg-amber-950 dark:text-amber-100"
                              : "bg-neutral-100 text-neutral-800 dark:bg-neutral-800 dark:text-neutral-100"
                          }`}
                        >
                          <p className="mb-0.5 text-[10px] text-neutral-500 dark:text-neutral-400">
                            {m.sender_name ?? (mine ? "You" : "Recruiter")}
                          </p>
                          <p className="whitespace-pre-wrap">{m.body}</p>
                        </div>
                      );
                    })}
                    {(selected.messages ?? []).length === 0 && (
                      <p className="text-center text-sm text-neutral-400">
                        No messages yet — say hello.
                      </p>
                    )}
                  </div>

                  {selected.status === "active" && (
                    <div className="flex gap-2 border-t border-neutral-200 pt-3 dark:border-neutral-800">
                      <textarea
                        value={draft}
                        onChange={(e) => setDraft(e.target.value)}
                        rows={2}
                        placeholder="Write through AskTrabaajo — your contact details stay private."
                        className={inputCls}
                      />
                      <button
                        className={primaryBtn}
                        disabled={busy || !draft.trim()}
                        onClick={sendMessage}
                      >
                        Send
                      </button>
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
