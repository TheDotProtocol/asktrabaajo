"use client";

import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";

import { AthenaConfirm } from "@/components/athena/AthenaConfirm";
import { AthenaResults } from "@/components/athena/AthenaResults";
import {
  ErrorBanner,
  LoadingState,
  StatusPill,
  btnCls,
  cardCls,
  ghostBtnCls,
  inputCls,
} from "@/components/candidate/ui";
import { api } from "@/lib/api/session";
import { ApiError } from "@/lib/api/types";
import {
  AthenaConfirmOut,
  AthenaMessageOut,
  AthenaPendingConfirmation,
  AthenaSession,
  AthenaStatus,
  AthenaToolMeta,
  AthenaToolResult,
} from "@/lib/api/types";
import {
  AthenaFrom,
  AthenaPortal,
  degradedLinks,
  parseAthenaFrom,
  providerStateLabel,
  sessionPurpose,
  suggestedPrompts,
} from "@/lib/athena/context";

type ChatItem = {
  id: string;
  role: "user" | "athena";
  text: string;
  at: string;
  results?: AthenaToolResult[];
  state?: "information" | "proposed" | "confirming" | "executing" | "completed" | "failed";
};

function humanError(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.code === "ai.provider_unavailable") {
      return "Athena's live intelligence service is not connected. Deterministic AskTrabaajo tools remain available.";
    }
    if (error.status === 401) return "Your session expired. Sign in again to continue.";
    if (error.status === 403) return "Athena is not allowed to do that with your current permissions.";
    if (error.status === 429) return "Athena usage limit reached for now. Try again later.";
    return error.message;
  }
  return String((error as Error).message ?? error);
}

export function AthenaWorkspace({
  portal,
  from: fromProp,
  organizationId,
}: {
  portal: AthenaPortal;
  from?: string | null;
  organizationId?: string | null;
}) {
  const from: AthenaFrom = parseAthenaFrom(fromProp ?? null);
  const mode = portal === "employer" ? "employer" : "jobseeker";
  const [status, setStatus] = useState<AthenaStatus | null>(null);
  const [tools, setTools] = useState<AthenaToolMeta[]>([]);
  const [session, setSession] = useState<AthenaSession | null>(null);
  const [items, setItems] = useState<ChatItem[]>([]);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [phase, setPhase] = useState<"idle" | "preparing" | "confirming" | "executing">("idle");
  const [error, setError] = useState("");
  const [pending, setPending] = useState<AthenaPendingConfirmation | null>(null);
  const scroller = useRef<HTMLDivElement>(null);
  const prompts = suggestedPrompts(portal, from);
  const links = degradedLinks(portal);

  const loadStatus = useCallback(async () => {
    const next = await api.get<AthenaStatus>("/athena/status");
    setStatus(next);
    try {
      setTools(await api.get<AthenaToolMeta[]>(`/athena/tools?mode=${mode}`));
    } catch {
      setTools([]);
    }
  }, [mode]);

  useEffect(() => {
    loadStatus().catch((e) => setError(humanError(e)));
  }, [loadStatus]);

  useEffect(() => {
    scroller.current?.scrollTo({ top: scroller.current.scrollHeight, behavior: "smooth" });
  }, [items, busy]);

  async function ensureSession(): Promise<AthenaSession> {
    if (session && session.status === "active") return session;
    const created = await api.post<AthenaSession>("/athena/session", {
      mode,
      purpose: sessionPurpose(portal, from),
      organization_id: portal === "employer" ? organizationId || null : null,
    });
    setSession(created);
    return created;
  }

  async function send(text: string) {
    const message = text.trim();
    if (!message || busy) return;
    if (status && !status.available) {
      setError("Live Athena is not connected. Use the deterministic links instead of a simulated reply.");
      return;
    }
    setBusy(true);
    setPhase("preparing");
    setError("");
    setDraft("");
    const userItem: ChatItem = {
      id: `u-${Date.now()}`,
      role: "user",
      text: message,
      at: new Date().toISOString(),
    };
    setItems((prev) => [...prev, userItem]);
    try {
      const current = await ensureSession();
      const out = await api.post<AthenaMessageOut>("/athena/message", {
        session_id: current.session_id,
        message,
      });
      const nextPending = out.pending_confirmations[0] ?? null;
      setPending(nextPending);
      setItems((prev) => [
        ...prev,
        {
          id: `a-${Date.now()}`,
          role: "athena",
          text: out.reply,
          at: new Date().toISOString(),
          results: out.tool_results,
          state: nextPending ? "proposed" : "information",
        },
      ]);
      setPhase(nextPending ? "confirming" : "idle");
    } catch (e) {
      const msg = humanError(e);
      setError(msg);
      setItems((prev) => [
        ...prev,
        {
          id: `e-${Date.now()}`,
          role: "athena",
          text: msg,
          at: new Date().toISOString(),
          state: "failed",
        },
      ]);
      setPhase("idle");
    } finally {
      setBusy(false);
    }
  }

  async function decide(approve: boolean) {
    if (!pending) return;
    setBusy(true);
    setPhase(approve ? "executing" : "idle");
    try {
      const out = await api.post<AthenaConfirmOut>("/athena/confirm", {
        confirmation_id: pending.confirmation_id,
        approve,
      });
      setPending(null);
      setItems((prev) => [
        ...prev,
        {
          id: `c-${Date.now()}`,
          role: "athena",
          text: approve
            ? `Action completed: ${out.tool ?? "confirmed action"}. Athena only reports what the backend executed.`
            : "You cancelled the proposed action. Nothing was sent or applied.",
          at: new Date().toISOString(),
          results: out.result ? [{ status: out.status, tool: out.tool ?? undefined, result: out.result }] : [],
          state: approve ? "completed" : "information",
        },
      ]);
    } catch (e) {
      setError(humanError(e));
      setItems((prev) => [
        ...prev,
        {
          id: `cf-${Date.now()}`,
          role: "athena",
          text: humanError(e),
          at: new Date().toISOString(),
          state: "failed",
        },
      ]);
    } finally {
      setBusy(false);
      setPhase("idle");
    }
  }

  async function resetConversation() {
    if (session) {
      try {
        await api.post(`/athena/session/${session.session_id}/close`);
      } catch {
        /* closing a stale session is not fatal */
      }
    }
    setSession(null);
    setItems([]);
    setPending(null);
    setError("");
    setPhase("idle");
  }

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    void send(draft);
  }

  if (!status && !error) return <LoadingState label="Opening Athena…" />;

  const available = Boolean(status?.available);
  const modeAllowed = Boolean(status?.modes.includes(mode));

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-6 lg:min-h-[70vh] lg:flex-row">
      <section className="flex min-w-0 flex-1 flex-col">
        <header className="mb-6 flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-[#d4af37]">Athena</p>
            <h1 className="mt-1 text-3xl font-semibold tracking-tight text-white sm:text-4xl">
              {portal === "candidate" ? "Employment intelligence" : "Hiring intelligence"}
            </h1>
            <p className="mt-2 max-w-xl text-sm text-[#9ca3af]">
              Athena orchestrates AskTrabaajo. It does not invent facts, and it never executes a
              consequential action without an exact confirmation.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <StatusPill status={mode} tone="gold" />
            <StatusPill
              status={providerStateLabel(status?.state ?? "limited")}
              tone={available ? "green" : "muted"}
            />
            <button type="button" className={ghostBtnCls} onClick={() => void resetConversation()}>
              New conversation
            </button>
          </div>
        </header>

        {error && <div className="mb-4"><ErrorBanner message={error} onRetry={() => void loadStatus()} /></div>}
        {!modeAllowed && status && (
          <ErrorBanner message="This Athena mode is not available on this account." />
        )}

        <div
          ref={scroller}
          className="min-h-[22rem] flex-1 space-y-4 overflow-y-auto rounded-xl border border-[#23272a] bg-[#0b0c0d] p-4 sm:p-6"
          aria-live="polite"
        >
          {items.length === 0 && (
            <div className="flex h-full flex-col justify-center gap-6 py-10 text-center">
              <div>
                <p className="text-lg font-semibold text-white">
                  {portal === "candidate"
                    ? "Tell Athena what you want to accomplish."
                    : "Tell Athena what you need to get done."}
                </p>
                <p className="mx-auto mt-2 max-w-md text-sm text-[#9ca3af]">
                  {available
                    ? "Starter prompts map to registered Athena tools. Nothing here is a previous conversation."
                    : "Live intelligence is not connected. Use the operating system itself — Athena will not invent a reply."}
                </p>
              </div>
              <div className="flex flex-wrap justify-center gap-2">
                {available
                  ? prompts.map((prompt) => (
                      <button
                        key={prompt.label}
                        type="button"
                        className={ghostBtnCls}
                        onClick={() => void send(prompt.message)}
                      >
                        {prompt.label}
                      </button>
                    ))
                  : links.map((link) => (
                      <Link key={link.href} href={link.href} className={ghostBtnCls}>
                        {link.label}
                      </Link>
                    ))}
              </div>
            </div>
          )}

          {items.map((item) => (
            <article
              key={item.id}
              className={`max-w-[40rem] rounded-xl border px-4 py-3 text-sm ${
                item.role === "user"
                  ? "ml-auto border-[#d4af37]/30 bg-[#111315] text-white"
                  : "border-[#23272a] bg-[#111315] text-[#e5e7eb]"
              }`}
            >
              <p className="font-mono text-[10px] uppercase tracking-wider text-[#6b7280]">
                {item.role === "user" ? "You" : "Athena"}
                {item.state && item.state !== "information" ? ` · ${item.state}` : ""}
              </p>
              <p className="mt-2 whitespace-pre-wrap leading-relaxed">{item.text}</p>
              {item.results && item.results.length > 0 && (
                <div className="mt-3">
                  <AthenaResults results={item.results} portal={portal} />
                </div>
              )}
            </article>
          ))}

          {busy && phase === "preparing" && (
            <p className="text-sm text-[#9ca3af]">Athena is working with authorized tools…</p>
          )}
        </div>

        {available && modeAllowed ? (
          <form onSubmit={onSubmit} className="mt-4 flex flex-col gap-2 sm:flex-row">
            <label className="sr-only" htmlFor="athena-composer">
              Message Athena
            </label>
            <textarea
              id="athena-composer"
              className={`${inputCls} min-h-[3rem] flex-1`}
              rows={2}
              value={draft}
              disabled={busy}
              placeholder="Ask about work, hiring, or the next action…"
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  void send(draft);
                }
              }}
            />
            <button type="submit" className={btnCls} disabled={busy || !draft.trim()}>
              Send
            </button>
          </form>
        ) : (
          <div className={`${cardCls} mt-4 border-[#d4af37]/25`}>
            <p className="text-sm text-[#9ca3af]">
              Live Athena is {providerStateLabel(status?.state ?? "not_configured").toLowerCase()}.
              This screen will not simulate a conversation.
            </p>
          </div>
        )}
      </section>

      <aside className="w-full shrink-0 space-y-4 lg:w-72">
        <section className={cardCls}>
          <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-[#9ca3af]">Context</p>
          <p className="mt-2 text-sm text-white">{from.replaceAll("-", " ")}</p>
          <p className="mt-1 text-xs text-[#6b7280]">
            Athena receives a professional digest from the backend. This page does not serialize extra personal data.
          </p>
        </section>
        <section className={cardCls}>
          <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-[#9ca3af]">Operate in the OS</p>
          <ul className="mt-3 space-y-2 text-sm">
            {links.map((link) => (
              <li key={link.href}>
                <Link href={link.href} className="text-[#d4af37] hover:underline">
                  {link.label}
                </Link>
                <p className="text-xs text-[#6b7280]">{link.body}</p>
              </li>
            ))}
          </ul>
        </section>
        {tools.length > 0 && (
          <section className={cardCls}>
            <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-[#9ca3af]">Registered capabilities</p>
            <ul className="mt-3 space-y-2 text-xs text-[#9ca3af]">
              {tools.slice(0, 8).map((tool) => (
                <li key={tool.name}>
                  <span className="text-white">{tool.name.replaceAll("_", " ")}</span>
                  {tool.confirmation_required && " · confirmation"}
                </li>
              ))}
            </ul>
          </section>
        )}
      </aside>

      {pending && (
        <AthenaConfirm
          pending={pending}
          busy={busy}
          onApprove={() => void decide(true)}
          onCancel={() => void decide(false)}
        />
      )}
    </div>
  );
}
