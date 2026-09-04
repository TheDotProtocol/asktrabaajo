"use client";
/**
 * Opportunity discovery — catalogue search plus Career Advisor match modes.
 * Matching is never recomputed in the browser.
 */
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import {
  EmptyState,
  ErrorBanner,
  LoadingState,
  PageHeader,
  btnCls,
  cardCls,
  ghostBtnCls,
  inputCls,
} from "@/components/candidate/ui";
import { api } from "@/lib/api/session";
import {
  CareerAdvisorOpportunities,
  OpportunityList,
  OpportunityMatch,
} from "@/lib/api/types";

const MODES = [
  { id: "all", label: "All active" },
  { id: "strong", label: "Strong" },
  { id: "potential", label: "Potential" },
  { id: "transition", label: "Career transition" },
  { id: "explore", label: "Explore" },
] as const;

type Mode = (typeof MODES)[number]["id"];

export default function OpportunitiesPage() {
  const [list, setList] = useState<OpportunityList | null>(null);
  const [recs, setRecs] = useState<CareerAdvisorOpportunities | null>(null);
  const [query, setQuery] = useState("");
  const [workMode, setWorkMode] = useState("");
  const [mode, setMode] = useState<Mode>("all");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [appliedIds, setAppliedIds] = useState<Set<string>>(new Set());
  const [selected, setSelected] = useState<Set<string>>(new Set());

  const loadCatalog = useCallback(async (q = "", wm = "") => {
    setBusy(true);
    setError("");
    try {
      const params = new URLSearchParams();
      if (q) params.set("q", q);
      if (wm) params.set("work_mode", wm);
      const qs = params.toString();
      const result = await api.get<OpportunityList>(`/jobseeker/opportunities${qs ? `?${qs}` : ""}`);
      setList(result);
      setAppliedIds(new Set(result.items.filter((i) => i.applied).map((i) => i.opportunity_id)));
    } catch (e) {
      setError(String((e as Error).message ?? e));
    } finally {
      setBusy(false);
    }
  }, []);

  const loadMode = useCallback(async (next: Exclude<Mode, "all">) => {
    setBusy(true);
    setError("");
    try {
      setRecs(await api.get<CareerAdvisorOpportunities>(`/career-advisor/opportunities?mode=${next}&limit=20`));
    } catch (e) {
      setError(String((e as Error).message ?? e));
    } finally {
      setBusy(false);
    }
  }, []);

  useEffect(() => {
    if (mode === "all") void loadCatalog(query, workMode);
    else void loadMode(mode);
    // query/workMode are applied only when Search is clicked or mode returns to all
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode, loadCatalog, loadMode]);

  async function apply(id: string, title?: string | null) {
    setError("");
    if (!window.confirm(`Submit an application to ${title || "this opportunity"}?`)) return;
    try {
      await api.post("/jobseeker/applications", {
        opportunity_id: id,
        cover_note: "Submitted from the AskTrabaajo Candidate OS.",
      });
      setNotice(`Applied to ${title || "the opportunity"}.`);
      setAppliedIds((prev) => new Set(prev).add(id));
    } catch (e) {
      setError(String((e as Error).message ?? e));
    }
  }

  async function save(id: string) {
    try {
      await api.post(`/jobseeker/opportunities/${id}/save`);
      if (mode === "all") await loadCatalog(query, workMode);
    } catch (e) {
      setError(String((e as Error).message ?? e));
    }
  }

  async function batchApply() {
    const ids = Array.from(selected);
    if (ids.length < 1) return;
    const typed = window.prompt(
      `High-risk batch apply. Type the exact number of selected IDs (${ids.length}) to confirm.\n\n${ids.join("\n")}`
    );
    if (typed !== String(ids.length)) {
      setError("Batch apply cancelled — confirmation did not match the selected count.");
      return;
    }
    try {
      const result = await api.post<{ applied: unknown[]; failed: unknown[] }>("/jobseeker/applications/batch", {
        opportunity_ids: ids,
      });
      setNotice(`Batch apply recorded: ${result.applied?.length ?? 0} applied, ${result.failed?.length ?? 0} failed.`);
      setSelected(new Set());
      if (mode === "all") await loadCatalog(query, workMode);
    } catch (e) {
      setError(String((e as Error).message ?? e));
    }
  }

  const catalogItems = list?.items ?? [];
  const recItems = recs?.items ?? [];
  const empty = mode === "all" ? catalogItems.length === 0 : recItems.length === 0;

  return (
    <div className="space-y-6">
      <PageHeader
        kicker="Talent Graph"
        title="Opportunities"
        subtitle="Search the live catalogue or switch to a Career Advisor mode. Matching stays on the server."
      />

      <div className="flex flex-wrap gap-2">
        {MODES.map((item) => (
          <button key={item.id} type="button" className={mode === item.id ? btnCls : ghostBtnCls} onClick={() => setMode(item.id)}>
            {item.label}
          </button>
        ))}
      </div>

      {mode === "all" && (
        <div className="flex flex-wrap gap-2">
          <input
            className={`${inputCls} max-w-sm`}
            placeholder="Search roles, companies, skills…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && void loadCatalog(query, workMode)}
          />
          <input
            className={`${inputCls} max-w-[10rem]`}
            placeholder="work mode"
            value={workMode}
            onChange={(e) => setWorkMode(e.target.value)}
          />
          <button type="button" className={btnCls} onClick={() => void loadCatalog(query, workMode)} disabled={busy}>
            Search
          </button>
          {selected.size > 0 && (
            <button type="button" className={ghostBtnCls} onClick={() => void batchApply()}>
              Batch apply ({selected.size})
            </button>
          )}
        </div>
      )}

      {recs?.note && mode !== "all" && <p className="text-sm text-[#9ca3af]">{recs.note}</p>}
      {notice && <p className="text-sm text-emerald-400">{notice}</p>}
      {error && <ErrorBanner message={error} />}
      {busy && empty && <LoadingState label="Matching…" />}

      {mode === "all" && !empty && (
        <div className="grid gap-4 lg:grid-cols-2">
          {catalogItems.map((item) => {
            const opp = item.opportunity;
            const already = appliedIds.has(item.opportunity_id);
            return (
              <article key={item.opportunity_id} className={cardCls}>
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <Link href={`/jobseeker/opportunities/${item.opportunity_id}`} className="font-semibold hover:text-[#d4af37]">
                      {opp?.title}
                    </Link>
                    <p className="text-sm text-[#9ca3af]">
                      {opp?.company_name}
                      {opp?.city ? ` · ${opp.city}` : ""}
                      {opp?.work_mode ? ` · ${opp.work_mode}` : ""}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-xl font-semibold text-[#d4af37]">{item.percent}%</p>
                    <p className="font-mono text-[10px] uppercase text-[#6b7280]">match</p>
                  </div>
                </div>
                <MatchBits strengths={item.strengths} gaps={item.gaps} missing={item.missing_skills} />
                <Actions
                  already={already}
                  saved={item.saved}
                  onApply={() => void apply(item.opportunity_id, opp?.title)}
                  onSave={() => void save(item.opportunity_id)}
                  selected={selected.has(item.opportunity_id)}
                  onSelect={() =>
                    setSelected((prev) => {
                      const next = new Set(prev);
                      if (next.has(item.opportunity_id)) next.delete(item.opportunity_id);
                      else next.add(item.opportunity_id);
                      return next;
                    })
                  }
                />
              </article>
            );
          })}
        </div>
      )}

      {mode !== "all" && !empty && (
        <div className="grid gap-4 lg:grid-cols-2">
          {recItems.map((item) => (
            <article key={item.opportunity_id} className={cardCls}>
              <div className="flex items-start justify-between gap-3">
                <div>
                  <Link href={`/jobseeker/opportunities/${item.opportunity_id}`} className="font-semibold hover:text-[#d4af37]">
                    {item.title}
                  </Link>
                  <p className="text-sm text-[#9ca3af]">{item.company}{item.location ? ` · ${item.location}` : ""}</p>
                </div>
                <p className="text-xl font-semibold text-[#d4af37]">{item.percent}%</p>
              </div>
              {item.career_signal?.signals?.[0] && (
                <p className="mt-2 text-xs text-[#9ca3af]">{item.career_signal.signals[0]}</p>
              )}
              <MatchBits strengths={item.strengths} gaps={[]} missing={item.missing_skills} />
              <Actions
                already={appliedIds.has(item.opportunity_id)}
                saved={false}
                onApply={() => void apply(item.opportunity_id, item.title)}
                onSave={() => void save(item.opportunity_id)}
              />
            </article>
          ))}
        </div>
      )}

      {!busy && empty && (
        <EmptyState
          title="No opportunities in this view"
          body="The catalogue is empty or your Work ID does not yet produce matches. Complete your identity, then return — we will not invent roles."
          actionHref="/id/work-id"
          actionLabel="Complete Work ID"
        />
      )}
    </div>
  );
}

function MatchBits({ strengths, gaps, missing }: { strengths: string[]; gaps: string[]; missing: string[] }) {
  return (
    <>
      <div className="mt-3 space-y-1 text-xs">
        {strengths.slice(0, 2).map((s, i) => (
          <p key={`s-${i}`} className="text-emerald-400">✓ {s}</p>
        ))}
        {gaps.slice(0, 2).map((g, i) => (
          <p key={`g-${i}`} className="text-[#d4af37]">▲ {g}</p>
        ))}
      </div>
      {missing.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1">
          {missing.slice(0, 3).map((ms) => (
            <span key={ms} className="rounded-full border border-[#23272a] px-2 py-0.5 text-[11px] text-[#9ca3af]">
              − {ms}
            </span>
          ))}
        </div>
      )}
    </>
  );
}

function Actions({
  already,
  saved,
  onApply,
  onSave,
  selected,
  onSelect,
}: {
  already: boolean;
  saved: boolean;
  onApply: () => void;
  onSave: () => void;
  selected?: boolean;
  onSelect?: () => void;
}) {
  return (
    <div className="mt-4 flex flex-wrap gap-2">
      {already ? (
        <span className="rounded bg-emerald-500/10 px-3 py-1.5 text-sm font-medium text-emerald-400">Applied</span>
      ) : (
        <>
          <button type="button" className={btnCls} onClick={onApply}>Apply</button>
          <button type="button" className={ghostBtnCls} onClick={onSave}>{saved ? "Saved" : "Save"}</button>
          {onSelect && (
            <button type="button" className={ghostBtnCls} onClick={onSelect}>
              {selected ? "Selected" : "Select"}
            </button>
          )}
        </>
      )}
    </div>
  );
}

export type { OpportunityMatch };
