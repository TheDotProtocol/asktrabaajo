"use client";
/**
 * Candidate Discovery — the Talent Graph for employers.
 *
 * Only PUBLIC Work ID data ever appears: people who have NOT opted into
 * discovery are invisible here, private skills are never probed by filters,
 * and every match explains WHY (mode + strengths + gaps) — no bare scores.
 * Saved candidates and talent pools are private to this organization.
 */
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { AthenaAskLink } from "@/components/athena/AthenaAskLink";
import { EmptyState, ErrorBanner, PageHeader, btnCls, cardCls, ghostBtnCls, inputCls } from "@/components/candidate/ui";
import { api } from "@/lib/api/session";
import {
  CandidateSearchItem,
  CandidateSearchList,
  CompanyJob,
  MatchedCandidateList,
  SavedCandidate,
  TalentPool,
} from "@/lib/api/types";
import { useOrg } from "@/context/OrgContext";
const modeStyle: Record<string, string> = {
  strong: "bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-400",
  potential: "bg-indigo-100 text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300",
  career_transition:
    "bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-400",
  explore: "bg-neutral-100 text-neutral-600 dark:bg-neutral-800 dark:text-neutral-300",
};

type Tab = "search" | "saved" | "pools" | "matches";

export default function CompanyCandidatesPage() {
  const { organizationId } = useOrg();
  const [orgId, setOrgId] = useState("");
  const [tab, setTab] = useState<Tab>("search");

  const [query, setQuery] = useState("");
  const [skills, setSkills] = useState("");
  const [location, setLocation] = useState("");
  const [results, setResults] = useState<CandidateSearchList | null>(null);
  const [saved, setSaved] = useState<SavedCandidate[]>([]);
  const [pools, setPools] = useState<TalentPool[]>([]);
  const [jobs, setJobs] = useState<CompanyJob[]>([]);
  const [selectedJob, setSelectedJob] = useState("");
  const [matches, setMatches] = useState<MatchedCandidateList | null>(null);

  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const loadSaved = useCallback(async () => {
    if (!orgId) return;
    try {
      setSaved(await api.get<SavedCandidate[]>(`/talent/${orgId}/candidates/saved`));
    } catch {
      /* permission may be missing — handled by tab render */
    }
  }, [orgId]);

  const loadPools = useCallback(async () => {
    if (!orgId) return;
    try {
      setPools(await api.get<TalentPool[]>(`/talent/${orgId}/pools`));
    } catch {
      setPools([]);
    }
  }, [orgId]);

  const loadJobs = useCallback(async () => {
    if (!orgId) return;
    try {
      const rows = await api.get<CompanyJob[]>(`/company/${orgId}/jobs`);
      setJobs(rows.filter((j) => j.status === "published"));
    } catch {
      setJobs([]);
    }
  }, [orgId]);

  useEffect(() => {
    setOrgId(organizationId);
    if (organizationId) {
      loadSaved();
      loadPools();
      loadJobs();
    }
  }, [loadSaved, loadPools, loadJobs, organizationId]);

  async function runSearch(page = 1) {
    if (!orgId || busy) return;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const params = new URLSearchParams({ page: String(page), page_size: "20" });
      if (query.trim()) params.set("q", query.trim());
      if (skills.trim()) params.set("skills", skills.trim());
      if (location.trim()) params.set("location", location.trim());
      const result = await api.get<CandidateSearchList>(
        `/talent/${orgId}/candidates/search?${params.toString()}`
      );
      setResults(result);
    } catch (e) {
      setError(String((e as Error).message ?? e));
    } finally {
      setBusy(false);
    }
  }

  async function loadMatches() {
    if (!orgId || !selectedJob) return;
    setBusy(true);
    setError("");
    try {
      const job = jobs.find((j) => j.id === selectedJob);
      if (!job?.opportunity_id) throw new Error("This job has no published opportunity.");
      const result = await api.get<MatchedCandidateList>(
        `/talent/${orgId}/opportunities/${job.opportunity_id}/candidates`
      );
      setMatches(result);
      setTab("matches");
    } catch (e) {
      setError(String((e as Error).message ?? e));
    } finally {
      setBusy(false);
    }
  }

  async function toggleSave(personId: string) {
    if (!orgId) return;
    setError("");
    const isSaved = saved.some((s) => s.person_id === personId);
    try {
      if (isSaved) {
        await api.delete(`/talent/${orgId}/candidates/${personId}/saved`);
        setNotice("Removed from your saved list.");
      } else {
        await api.post(`/talent/${orgId}/candidates/${personId}/saved`, {
          note: "Saved from candidate discovery.",
        });
        setNotice("Candidate saved.");
      }
      await loadSaved();
    } catch (e) {
      setError(String((e as Error).message ?? e));
    }
  }

  function renderCandidate(item: CandidateSearchItem) {
    const isSaved = saved.some((s) => s.person_id === item.person_id);
    return (
      <article key={item.person_id} className={cardCls}>
        <div className="flex items-start justify-between gap-3">
          <Link href={`/company/candidates/${item.person_id}`} className="min-w-0">
            <h2 className="truncate font-semibold hover:text-indigo-600">
              {item.name ?? "Candidate"}
            </h2>
            {item.headline && (
              <p className="truncate text-sm text-neutral-500 dark:text-neutral-400">
                {item.headline}
              </p>
            )}
            <p className="mt-0.5 text-xs text-neutral-400">
              {item.location ?? "Location not disclosed"}
              {item.experience_years != null
                ? ` · ${item.experience_years}+ yrs`
                : ""}
              {item.latest_role
                ? ` · ${item.latest_role.title} @ ${item.latest_role.company_name}`
                : ""}
            </p>
          </Link>
          <button
            onClick={() => toggleSave(item.person_id)}
            className={ghostBtnCls}
          >
            {isSaved ? "Saved ✓" : "Save"}
          </button>
        </div>
        {item.skills.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-1">
            {item.skills.slice(0, 8).map((s) => (
              <span
                key={s.name}
                className="rounded-full bg-neutral-100 px-2 py-0.5 text-[11px] capitalize text-neutral-600 dark:bg-neutral-800 dark:text-neutral-300"
              >
                {s.name}
              </span>
            ))}
          </div>
        )}
        <p className="mt-3 text-[10px] uppercase tracking-wide text-neutral-400">
          Public profile only — private Work ID sections and documents require
          consent
        </p>
      </article>
    );
  }

  if (!orgId) {
    return (
      <EmptyState
        title="Select an organization"
        body="Talent Graph search is organization-scoped."
        actionHref="/company"
        actionLabel="Command center"
      />
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        kicker="Talent Graph"
        title="Candidate discovery"
        subtitle="Public professional data only. Hidden Work ID sections are never probed. Matching modes stay canonical."
        actions={
          <div className="flex flex-wrap items-center gap-3">
            <AthenaAskLink portal="employer" from="candidates" />
          <nav className="flex gap-1 rounded-lg border border-[#23272a] p-1 text-sm">
            {(["search", "saved", "pools", "matches"] as Tab[]).map((t) => (
              <button
                key={t}
                type="button"
                onClick={() => setTab(t)}
                className={`rounded-md px-3 py-1.5 capitalize ${
                  tab === t ? btnCls : ghostBtnCls
                }`}
              >
                {t === "matches" ? "Ranked matches" : t}
              </button>
            ))}
          </nav>
          </div>
        }
      />

      {notice && <p className="text-sm text-emerald-400">{notice}</p>}
      {error && <ErrorBanner message={error} />}

      {/* Search */}
      {tab === "search" && (
        <div className="space-y-4">
          <div className="grid gap-2 sm:grid-cols-4">
            <input
              className={inputCls}
              placeholder="Name, headline…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
            <input
              className={inputCls}
              placeholder="Skills (comma-separated)"
              value={skills}
              onChange={(e) => setSkills(e.target.value)}
            />
            <input
              className={inputCls}
              placeholder="Location"
              value={location}
              onChange={(e) => setLocation(e.target.value)}
            />
            <button className={btnCls} disabled={busy} onClick={() => runSearch()}>
              {busy ? "Searching…" : "Search"}
            </button>
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            {(results?.items ?? []).map(renderCandidate)}
          </div>
          {results && results.items.length === 0 && (
            <div className={cardCls}>
              <p className="text-center text-sm text-neutral-400">
                No discoverable candidates match — people appear here only after
                they opt in with a public Work ID profile.
              </p>
            </div>
          )}
        </div>
      )}

      {/* Saved */}
      {tab === "saved" && (
        <div className="space-y-4">
          {saved.length === 0 ? (
            <div className={cardCls}>
              <p className="text-center text-sm text-neutral-400">
                Save candidates from discovery to build a private shortlist here.
              </p>
            </div>
          ) : (
            saved.map((s) => (
              <div key={s.id} className={cardCls}>
                <div className="flex items-start justify-between gap-3">
                  <Link
                    href={`/company/candidates/${s.person_id}`}
                    className="min-w-0 font-semibold hover:text-indigo-600"
                  >
                    {s.name ?? "Candidate"}
                    {s.headline && (
                      <span className="block text-sm font-normal text-neutral-500">
                        {s.headline}
                      </span>
                    )}
                  </Link>
                  <button
                    onClick={() => toggleSave(s.person_id)}
                    className={ghostBtnCls}
                  >
                    Unsave
                  </button>
                </div>
                {s.note && <p className="mt-2 text-xs text-neutral-400">{s.note}</p>}
                {s.tags && s.tags.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1">
                    {s.tags.map((t) => (
                      <span
                        key={t}
                        className="rounded-full bg-indigo-50 px-2 py-0.5 text-[11px] text-indigo-600 dark:bg-indigo-950 dark:text-indigo-300"
                      >
                        {t}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      )}

      {/* Pools */}
      {tab === "pools" && (
        <PoolPanel
          orgId={orgId}
          pools={pools}
          onChanged={async () => {
            await loadPools();
          }}
        />
      )}

      {/* Ranked matches for a published job */}
      {tab === "matches" && (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center gap-2">
            <select
              value={selectedJob}
              onChange={(e) => setSelectedJob(e.target.value)}
              className={inputCls}
            >
              <option value="">Choose a published job…</option>
              {jobs.map((j) => (
                <option key={j.id} value={j.id}>
                  {j.title}
                </option>
              ))}
            </select>
            <button className={btnCls} disabled={!selectedJob || busy} onClick={loadMatches}>
              {busy ? "Ranking…" : "Rank matching candidates"}
            </button>
          </div>
          {jobs.length === 0 && (
            <p className="text-sm text-neutral-400">
              Publish a job first — ranked discovery works against your published
              opportunities.
            </p>
          )}
          {matches && (
            <div className="grid gap-4 md:grid-cols-2">
              {matches.items.map((m) => (
                <article key={m.person_id} className={cardCls}>
                  <div className="flex items-start justify-between gap-3">
                    <Link
                      href={`/company/candidates/${m.person_id}?job=${selectedJob}`}
                      className="min-w-0"
                    >
                      <h3 className="truncate font-semibold hover:text-indigo-600">
                        {m.summary.name ?? "Candidate"}
                      </h3>
                      <p className="text-xs text-neutral-400">
                        {m.summary.location ?? "Location not disclosed"}
                      </p>
                    </Link>
                    <span
                      className={`rounded-full px-2.5 py-0.5 text-[11px] font-medium capitalize ${modeStyle[m.mode] ?? modeStyle.explore}`}
                    >
                      {m.mode.replace("_", " ")}
                    </span>
                  </div>
                  <p className="mt-2 text-2xl font-semibold tracking-tight">
                    {m.percent}%
                    <span className="ml-2 text-[10px] font-normal uppercase tracking-wide text-neutral-400">
                      match
                    </span>
                  </p>
                  {m.matched_skills.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1">
                      {m.matched_skills.slice(0, 6).map((s) => (
                        <span
                          key={s}
                          className="rounded-full bg-emerald-50 px-2 py-0.5 text-[11px] capitalize text-emerald-700 dark:bg-emerald-950 dark:text-emerald-400"
                        >
                          ✓ {s}
                        </span>
                      ))}
                    </div>
                  )}
                  {m.missing_skills.length > 0 && (
                    <p className="mt-2 text-xs text-amber-600 dark:text-amber-400">
                      Missing: {m.missing_skills.slice(0, 5).join(", ")}
                    </p>
                  )}
                  <button
                    onClick={() => toggleSave(m.person_id)}
                    className={`mt-3 ${ghostBtnCls}`}
                  >
                    {saved.some((s) => s.person_id === m.person_id)
                      ? "Saved ✓"
                      : "Save"}
                  </button>
                </article>
              ))}
              {matches.items.length === 0 && (
                <p className="text-sm text-neutral-400">
                  No fully-discoverable candidates ranked for this role yet.
                </p>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function PoolPanel({
  orgId,
  pools,
  onChanged,
}: {
  orgId: string;
  pools: TalentPool[];
  onChanged: () => Promise<void>;
}) {
  const [name, setName] = useState("");
  const [desc, setDesc] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function createPool() {
    if (!name.trim() || busy) return;
    setBusy(true);
    setError("");
    try {
      await api.post(`/talent/${orgId}/pools`, {
        name: name.trim(),
        description: desc.trim() || null,
      });
      setName("");
      setDesc("");
      await onChanged();
    } catch (e) {
      setError(String((e as Error).message ?? e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-4">
      <form
        onSubmit={(e) => {
          e.preventDefault();
          createPool();
        }}
        className={`${cardCls} grid gap-2 sm:grid-cols-3`}
      >
        <input
          className={inputCls}
          placeholder="Pool name (e.g. Senior React Engineers)"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <input
          className={inputCls}
          placeholder="Description (optional)"
          value={desc}
          onChange={(e) => setDesc(e.target.value)}
        />
        <button className={btnCls} disabled={busy} type="submit">
          {busy ? "Creating…" : "Create pool"}
        </button>
      </form>
      {error && (
        <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
      )}
      <div className="grid gap-4 md:grid-cols-2">
        {pools.map((p) => (
          <div key={p.id} className={cardCls}>
            <div className="flex items-center justify-between gap-3">
              <div className="min-w-0">
                <h3 className="truncate font-semibold">{p.name}</h3>
                {p.description && (
                  <p className="mt-0.5 truncate text-xs text-neutral-400">
                    {p.description}
                  </p>
                )}
              </div>
              <span className="shrink-0 rounded-full bg-neutral-100 px-2 py-0.5 text-xs text-neutral-600 dark:bg-neutral-800 dark:text-neutral-300">
                {p.member_count}
              </span>
            </div>
            <p className="mt-2 text-[10px] uppercase tracking-wide text-neutral-400">
              Private to this organization
            </p>
          </div>
        ))}
        {pools.length === 0 && (
          <p className="text-sm text-neutral-400">
            Pools are private to your organization — Company B can never see them.
          </p>
        )}
      </div>
    </div>
  );
}
