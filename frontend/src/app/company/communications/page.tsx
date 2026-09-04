"use client";
/**
 * Company Communication Center (Phase 8 proof).
 *
 * An Employment Communication OS, not a chat app: outreach requests, active
 * conversations tied to opportunities/applications, per-conversation threads
 * and unread state. Every conversation exists because of a legitimate
 * relationship — never because a candidate is merely discoverable.
 */
import { useCallback, useEffect, useRef, useState } from "react";

import { EmptyState, ErrorBanner, PageHeader, cardCls } from "@/components/candidate/ui";
import { api } from "@/lib/api/session";
import {
  CompanyApplication,
  ConversationRow,
  EventsFeed,
  OutreachRequestRow,
} from "@/lib/api/types";
import { useOrg } from "@/context/OrgContext";
const primaryBtn =
  "rounded bg-indigo-500 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-600 disabled:opacity-40";
const ghostBtn =
  "rounded border border-neutral-300 px-3 py-1.5 text-sm text-neutral-600 hover:border-indigo-400 dark:border-neutral-700 dark:text-neutral-300";
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

export default function CompanyCommunicationsPage() {
  const { organizationId } = useOrg();
  const [orgId, setOrgId] = useState("");
  const [outreach, setOutreach] = useState<OutreachRequestRow[]>([]);
  const [conversations, setConversations] = useState<ConversationRow[]>([]);
  const [applications, setApplications] = useState<CompanyApplication[]>([]);
  const [selected, setSelected] = useState<ConversationRow | null>(null);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [newAppId, setNewAppId] = useState("");
  const [live, setLive] = useState(false);
  const cursorRef = useRef<string | null>(null);

  const load = useCallback(async () => {
    if (!orgId) return;
    try {
      const [out, convs] = await Promise.all([
        api.get<OutreachRequestRow[]>(`/talent/${orgId}/outreach`),
        api.get<ConversationRow[]>(`/talent/${orgId}/communications`),
      ]);
      setOutreach(out);
      setConversations(convs);
      setError("");
    } catch (e) {
      setError(String((e as Error).message ?? e));
    }
  }, [orgId]);

  useEffect(() => {
    setOrgId(organizationId);
    if (!organizationId) return;
    api
      .get<CompanyApplication[]>(`/company/${organizationId}/applications`)
      .then(setApplications)
      .catch(() => setApplications([]));
  }, [organizationId]);

  useEffect(() => {
    if (orgId) void load();
  }, [orgId, load]);

  // Phase 9 realtime foundation: poll the canonical event feed. Events carry
  // whitelisted metadata only (never message bodies), so a refresh of the
  // existing views is all that is needed. A WebSocket/SSE transport replaces
  // this loop later without touching the views.
  useEffect(() => {
    if (!orgId) return;
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
  }, [orgId, load]);

  async function cancelRequest(request: OutreachRequestRow) {
    setBusy(true);
    setError("");
    try {
      await api.post(`/talent/${orgId}/outreach/${request.id}/cancel`);
      await load();
    } catch (e) {
      setError(String((e as Error).message ?? e));
    } finally {
      setBusy(false);
    }
  }

  async function openConversation(conv: ConversationRow) {
    setSelected(null);
    try {
      const detail = await api.get<ConversationRow>(
        `/talent/${orgId}/communications/${conv.id}`
      );
      setSelected(detail);
      await api.post(`/talent/${orgId}/communications/${conv.id}/read`);
      void load();
    } catch (e) {
      setError(String((e as Error).message ?? e));
    }
  }

  async function openFromApplication() {
    if (!newAppId) return;
    setBusy(true);
    setError("");
    try {
      const conv = await api.post<ConversationRow>(
        `/talent/${orgId}/communications`,
        { application_id: newAppId }
      );
      setNewAppId("");
      setSelected(conv);
      await load();
    } catch (e) {
      setError(String((e as Error).message ?? e));
    } finally {
      setBusy(false);
    }
  }

  async function sendMessage() {
    if (!selected || !draft.trim()) return;
    setBusy(true);
    setError("");
    try {
      await api.post(`/talent/${orgId}/communications/${selected.id}/messages`, {
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

  async function closeConversation() {
    if (!selected) return;
    setBusy(true);
    try {
      const closed = await api.post<ConversationRow>(
        `/talent/${orgId}/communications/${selected.id}/close`
      );
      setSelected(closed);
      await load();
    } catch (e) {
      setError(String((e as Error).message ?? e));
    } finally {
      setBusy(false);
    }
  }

  const activeConversations = conversations.filter((c) => c.status === "active");
  const unreadTotal = conversations.reduce((s, c) => s + c.unread_count, 0);

  return (
    <div className="space-y-6">
      <PageHeader
        kicker="Messages"
        title="Communications"
        subtitle="Outreach and conversations only exist after a legitimate relationship. Raw personal contact details are never shown here."
        actions={
          <div className="flex items-center gap-3 text-sm">
            {live && (
              <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-800 px-2.5 py-1 text-xs text-emerald-400">
                Updated
              </span>
            )}
            <span className="rounded-lg border border-[#23272a] px-3 py-1.5">{outreach.length} outreach</span>
            <span className="rounded-lg border border-[#23272a] px-3 py-1.5">{activeConversations.length} active</span>
            <span className="rounded-lg border border-[#23272a] px-3 py-1.5">{unreadTotal} unread</span>
          </div>
        }
      />

      {error && <ErrorBanner message={error} />}

      {!orgId && (
        <EmptyState
          title="Select an organization"
          body="Communications are tenant-scoped."
          actionHref="/company"
          actionLabel="Command center"
        />
      )}

      {/* Outreach requests sent by this organization */}
      <section className={cardCls}>
        <h2 className="text-sm font-semibold">Outreach requests</h2>
        {outreach.length === 0 && (
          <p className="mt-3 text-sm text-neutral-400">
            No outreach sent yet. Open a candidate profile and use “Request
            contact” — the candidate decides.
          </p>
        )}
        <div className="mt-3 space-y-3">
          {outreach.map((request) => (
            <div
              key={request.id}
              className="flex flex-wrap items-start justify-between gap-3 rounded-lg border border-neutral-200 p-3 dark:border-neutral-800"
            >
              <div className="min-w-0">
                <p className="text-sm font-medium">
                  {request.candidate?.name ?? "Candidate"}
                  <span className="font-normal text-neutral-400">
                    {" "}
                    {request.candidate?.headline
                      ? `— ${request.candidate.headline}`
                      : ""}
                  </span>
                </p>
                <p className="mt-0.5 text-xs text-neutral-400">
                  {request.opportunity_title ?? "No specific job"}
                  {" · "}
                  {fmt(request.created_at)}
                </p>
                <p className="mt-1 text-sm text-neutral-600 dark:text-neutral-300">
                  “{request.message}”
                </p>
              </div>
              <div className="flex items-center gap-2">
                <span
                  className={`rounded-full px-2.5 py-1 text-xs capitalize ${statusStyle[request.status] ?? ""}`}
                >
                  {request.status}
                </span>
                {["sent", "viewed"].includes(request.status) && (
                  <button
                    className="text-xs text-neutral-400 underline-offset-2 hover:text-red-500 hover:underline"
                    onClick={() => cancelRequest(request)}
                  >
                    Cancel
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Conversations */}
      <section className={cardCls}>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-sm font-semibold">Conversations</h2>
          <div className="flex flex-wrap items-center gap-2 text-sm">
            <select
              value={newAppId}
              onChange={(e) => setNewAppId(e.target.value)}
              className="rounded border border-neutral-300 px-2 py-1.5 dark:border-neutral-700 dark:bg-neutral-900"
            >
              <option value="">Open from an application…</option>
              {applications.map((app) => (
                <option key={app.id} value={app.id}>
                  {app.candidate_name} — {app.job_title ?? "Job"}
                </option>
              ))}
            </select>
            <button className={ghostBtn} onClick={openFromApplication}>
              Open thread
            </button>
          </div>
        </div>

        {conversations.length === 0 && (
          <p className="mt-4 text-sm text-neutral-400">
            No conversations yet. They open when a candidate accepts your
            outreach, or when you open one on an application.
          </p>
        )}

        {conversations.length > 0 && (
          <div className="mt-4 grid gap-4 lg:grid-cols-[300px_1fr]">
            <div className="space-y-2">
              {conversations.map((conv) => (
                <button
                  key={conv.id}
                  onClick={() => openConversation(conv)}
                  className={`w-full rounded-lg border p-3 text-left text-sm transition ${
                    selected?.id === conv.id
                      ? "border-indigo-400 bg-indigo-50 dark:bg-indigo-950/40"
                      : "border-neutral-200 hover:border-indigo-300 dark:border-neutral-800"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-medium">{conv.candidate.name}</span>
                    {conv.unread_count > 0 && (
                      <span className="rounded-full bg-indigo-500 px-1.5 py-0.5 text-[10px] font-medium text-white">
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
                  Select a conversation to read or reply.
                </p>
              )}
              {selected && (
                <>
                  <div className="flex items-start justify-between gap-2 border-b border-neutral-200 pb-3 dark:border-neutral-800">
                    <div>
                      <p className="font-medium">{selected.candidate.name}</p>
                      <p className="text-xs text-neutral-400">
                        {selected.opportunity_title ?? "Opportunity"}
                        {selected.application_id
                          ? " · linked to an application"
                          : ""}
                        {selected.status === "closed"
                          ? " · conversation closed"
                          : ` · speaking with ${selected.counterpart ?? "the candidate"}`}
                      </p>
                    </div>
                    {selected.status === "active" && (
                      <button
                        className="text-xs text-neutral-400 underline-offset-2 hover:underline"
                        onClick={closeConversation}
                      >
                        Close
                      </button>
                    )}
                  </div>

                  <div className="flex-1 space-y-3 overflow-y-auto py-4">
                    {(selected.messages ?? []).map((m) => {
                      const mine = m.sender_side === "recruiter";
                      return (
                        <div
                          key={m.id}
                          className={`max-w-[80%] rounded-lg px-3 py-2 text-sm ${
                            mine
                              ? "ml-auto bg-indigo-100 text-indigo-900 dark:bg-indigo-950 dark:text-indigo-100"
                              : "bg-neutral-100 text-neutral-800 dark:bg-neutral-800 dark:text-neutral-100"
                          }`}
                        >
                          <p className="mb-0.5 text-[10px] text-neutral-500 dark:text-neutral-400">
                            {m.sender_name ?? (mine ? "You" : "Candidate")}
                          </p>
                          <p className="whitespace-pre-wrap">{m.body}</p>
                        </div>
                      );
                    })}
                    {(selected.messages ?? []).length === 0 && (
                      <p className="text-center text-sm text-neutral-400">
                        No messages yet — introduce your opportunity.
                      </p>
                    )}
                  </div>

                  {selected.status === "active" && (
                    <div className="flex gap-2 border-t border-neutral-200 pt-3 dark:border-neutral-800">
                      <textarea
                        value={draft}
                        onChange={(e) => setDraft(e.target.value)}
                        rows={2}
                        placeholder="Message in-platform. Documents and private data still need explicit consent."
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
