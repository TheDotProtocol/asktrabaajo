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
  contextLabel,
  degradedLinks,
  parseAthenaFrom,
  phaseLabel,
  providerStateLabel,
  sessionPurpose,
  suggestedPrompts,
} from "@/lib/athena/context";

type ItemState = "information" | "recommendation" | "proposed" | "confirming" | "executing" | "completed" | "failed";

type ChatItem = {
  id: string;
  role: "user" | "athena";
  text: string;
  at: string;
  results?: AthenaToolResult[];
  state?: ItemState;
};

const STATE_LABEL: Record<ItemState, string> = {
  information: "Information",
  recommendation: "Recommendation",
  proposed: "Proposed action",
  confirming: "Confirmation required",
  executing: "Executing",
  completed: "Completed",
  failed: "Failed",
};

function stateTone(state: ItemState): string {
  if (state === "failed") return "border-red-900/80 bg-red-950/20 text-red-200";
  if (state === "completed") return "border-emerald-900/60 bg-emerald-950/20 text-emerald-300";
  if (state === "proposed" || state === "confirming") return "border-[#d4af37]/40 bg-[#d4af37]/5 text-[#d4af37]";
  if (state === "recommendation") return "border-[#d4af37]/25 bg-[#111315] text-[#d4af37]";
  if (state === "executing") return "border-[#23272a] bg-[#111315] text-[#9ca3af]";
  return "border-[#23272a] bg-[#111315] text-[#9ca3af]";
}

function humanError(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.code === "ai.provider_unavailable") {
      return "Athena intelligence is currently unavailable. The Employment OS remains available.";
    }
    if (error.status === 401) return "Your session expired. Sign in again to continue.";
    if (error.status === 403) return "Athena is not allowed to do that with your current permissions.";
    if (error.status === 429) return "Athena usage limit reached for now. Try again later.";
    return error.message;
  }
  return String((error as Error).message ?? error);
}

function StateMark({ state }: { state: ItemState }) {
  return (
    <span className={`inline-flex rounded-full border px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider ${stateTone(state)}`}>
      {STATE_LABEL[state]}
    </span>
  );
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
  const [phase, setPhase] = useState<"idle" | "understanding" | "preparing" | "confirming" | "executing">("idle");
  const [error, setError] = useState("");
  const [pending, setPending] = useState<AthenaPendingConfirmation | null>(null);
  const scroller = useRef<HTMLDivElement>(null);
  const prompts = suggestedPrompts(portal, from);
  const links = degradedLinks(portal);
  const surface = contextLabel(from);

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
      setError("Athena intelligence is currently unavailable. Use the Employment OS instead of a simulated reply.");
      return;
    }
    setBusy(true);
    setPhase("understanding");
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
      setPhase("preparing");
      const out = await api.post<AthenaMessageOut>("/athena/message", {
        session_id: current.session_id,
        message,
      });
      const nextPending = out.pending_confirmations[0] ?? null;
      setPending(nextPending);
      const hasResults = (out.tool_results?.length ?? 0) > 0;
      setItems((prev) => [
        ...prev,
        {
          id: `a-${Date.now()}`,
          role: "athena",
          text: out.reply,
          at: new Date().toISOString(),
          results: out.tool_results,
          state: nextPending ? "proposed" : hasResults ? "recommendation" : "information",
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
            ? `Completed: ${out.tool ?? "confirmed action"}. Athena only reports what the backend executed.`
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
  const livePhase = phaseLabel(phase);

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-5 lg:min-h-[70vh] lg:flex-row lg:gap-8">
      <section className="flex min-w-0 flex-1 flex-col">
        <header className="mb-4 flex flex-wrap items-start justify-between gap-4">
          <div className="flex items-start gap-3">
            <span className="mt-1 size-[18px] shrink-0 rounded-[3px] bg-[#d4af37] shadow-[0_0_8px_#d4af37]" aria-hidden />
            <div>
              <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-[#d4af37]">Athena</p>
              <h1 className="mt-1 text-3xl font-semibold tracking-tight text-white sm:text-4xl">
                {portal === "candidate" ? "Career intelligence" : "Hiring intelligence"}
              </h1>
              <p className="mt-2 max-w-xl text-sm text-[#9ca3af]">
                {portal === "candidate"
                  ? "Athena sits on the Candidate OS — career, skills, opportunities, applications, and interviews."
                  : "Athena sits on the Employer OS — jobs, talent, pipeline, interviews, and offers."}
              </p>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <StatusPill status={portal === "candidate" ? "Candidate" : "Employer"} tone="gold" />
            <StatusPill
              status={providerStateLabel(status?.state ?? "limited")}
              tone={available ? "green" : "muted"}
            />
            <button type="button" className={ghostBtnCls} onClick={() => void resetConversation()}>
              New conversation
            </button>
          </div>
        </header>

        <div className="mb-4 rounded-xl border border-[#d4af37]/20 bg-[#111315] px-4 py-3">
          <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-[#d4af37]">Ask Athena</p>
          <p className="mt-1 text-sm text-white">
            Context: <span className="text-[#e5e7eb]">{surface}</span>
          </p>
          <p className="mt-1 text-xs text-[#6b7280]">
            Athena receives a professional digest from the backend. This page does not serialize extra personal data.
          </p>
        </div>

        {error && (
          <div className="mb-4">
            <ErrorBanner message={error} onRetry={() => void loadStatus()} />
          </div>
        )}
        {!modeAllowed && status && <ErrorBanner message="This Athena mode is not available on this account." />}

        <p className="sr-only" aria-live="polite">
          {livePhase}
        </p>

        <div
          ref={scroller}
          className="min-h-[22rem] flex-1 space-y-5 overflow-y-auto overflow-x-hidden rounded-xl border border-[#23272a] bg-[#0b0c0d] p-4 sm:p-6"
          aria-live="polite"
        >
          {items.length === 0 && (
            <div className="flex h-full flex-col justify-center gap-6 py-8">
              {available ? (
                <>
                  <div className="max-w-lg">
                    <p className="text-xl font-semibold text-white sm:text-2xl">
                      {portal === "candidate"
                        ? "Tell Athena what you want to accomplish."
                        : "Tell Athena what you need to get done."}
                    </p>
                    <p className="mt-2 text-sm text-[#9ca3af]">
                      Starter actions map to registered Athena tools. Nothing here is a previous conversation.
                    </p>
                  </div>
                  <div className="grid gap-2 sm:grid-cols-2">
                    {prompts.map((prompt) => (
                      <button
                        key={prompt.label}
                        type="button"
                        className={`${ghostBtnCls} h-auto justify-start px-4 py-3 text-left`}
                        onClick={() => void send(prompt.message)}
                      >
                        {prompt.label}
                      </button>
                    ))}
                  </div>
                </>
              ) : (
                <>
                  <div className="max-w-lg">
                    <p className="text-xl font-semibold text-white sm:text-2xl">
                      Athena intelligence is currently unavailable.
                    </p>
                    <p className="mt-2 text-sm text-[#9ca3af]">
                      Live conversation is not simulated. The {portal === "candidate" ? "Candidate" : "Employer"} OS
                      remains available.
                    </p>
                  </div>
                  <div className="grid gap-3 sm:grid-cols-2">
                    {links.map((link) => (
                      <Link key={link.href} href={link.href} className={`${cardCls} hover:border-[#d4af37]/40`}>
                        <p className="font-medium text-white">{link.label}</p>
                        <p className="mt-1 text-xs text-[#9ca3af]">{link.body}</p>
                      </Link>
                    ))}
                  </div>
                </>
              )}
            </div>
          )}

          {items.map((item) =>
            item.role === "user" ? (
              <p key={item.id} className="text-right text-sm text-[#9ca3af]">
                <span className="font-mono text-[10px] uppercase tracking-wider text-[#6b7280]">You · </span>
                {item.text}
              </p>
            ) : (
              <article key={item.id} className="space-y-3">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="font-mono text-[10px] uppercase tracking-wider text-[#6b7280]">Athena</p>
                  {item.state && <StateMark state={item.state} />}
                </div>
                <p className="max-w-2xl whitespace-pre-wrap text-sm leading-relaxed text-[#e5e7eb]">{item.text}</p>
                {item.results && item.results.length > 0 && (
                  <div className="rounded-xl border border-[#d4af37]/15 bg-[#111315]/60 p-3 sm:p-4">
                    <AthenaResults results={item.results} portal={portal} />
                  </div>
                )}
              </article>
            )
          )}

          {busy && livePhase && (
            <p className="font-mono text-[11px] uppercase tracking-[0.14em] text-[#d4af37]">{livePhase}</p>
          )}
        </div>

        <nav className="mt-3 flex gap-2 overflow-x-auto pb-1 lg:hidden" aria-label="Operate in the OS">
          {links.map((link) => (
            <Link key={link.href} href={link.href} className={`${ghostBtnCls} shrink-0`}>
              {link.label}
            </Link>
          ))}
        </nav>

        {available && modeAllowed ? (
          <form onSubmit={onSubmit} className="mt-4 flex flex-col gap-2 sm:flex-row sm:items-end">
            <label className="sr-only" htmlFor="athena-composer">
              Message Athena
            </label>
            <textarea
              id="athena-composer"
              className={`${inputCls} min-h-[3rem] flex-1`}
              rows={2}
              value={draft}
              disabled={busy}
              placeholder={
                portal === "candidate"
                  ? "Tell Athena what you want to accomplish."
                  : "Tell Athena what you need to get done."
              }
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  void send(draft);
                }
              }}
            />
            <button type="submit" className={`${btnCls} sm:min-w-[6rem]`} disabled={busy || !draft.trim()}>
              Ask
            </button>
          </form>
        ) : (
          <div className={`${cardCls} mt-4 border-[#d4af37]/25`}>
            <p className="text-sm text-white">Athena intelligence is currently unavailable.</p>
            <p className="mt-1 text-sm text-[#9ca3af]">
              This screen will not simulate a conversation. Continue in the operating system.
            </p>
          </div>
        )}
      </section>

      <aside className="hidden w-60 shrink-0 space-y-4 lg:block">
        <section className={cardCls}>
          <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-[#9ca3af]">Operate in the OS</p>
          <ul className="mt-3 space-y-3 text-sm">
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
          <details className={cardCls}>
            <summary className="cursor-pointer font-mono text-[11px] uppercase tracking-[0.18em] text-[#9ca3af]">
              Registered capabilities
            </summary>
            <ul className="mt-3 space-y-2 text-xs text-[#9ca3af]">
              {tools.slice(0, 8).map((tool) => (
                <li key={tool.name}>
                  <span className="text-white">{tool.name.replaceAll("_", " ")}</span>
                  {tool.confirmation_required && " · confirmation"}
                </li>
              ))}
            </ul>
          </details>
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
