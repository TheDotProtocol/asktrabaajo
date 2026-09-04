import Link from "next/link";

import { StatusPill, cardCls } from "@/components/candidate/ui";
import { AthenaToolResult } from "@/lib/api/types";

function asRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : null;
}

function asList(value: unknown): Record<string, unknown>[] {
  if (!Array.isArray(value)) return [];
  return value.map(asRecord).filter(Boolean) as Record<string, unknown>[];
}

function text(value: unknown): string {
  if (value == null) return "";
  if (typeof value === "string" || typeof value === "number") return String(value);
  return "";
}

function stringList(value: unknown, limit = 3): string[] {
  if (!Array.isArray(value)) return [];
  return value.map(text).filter(Boolean).slice(0, limit);
}

function matchOf(row: Record<string, unknown>): Record<string, unknown> | null {
  return asRecord(row.match) ?? asRecord(row.matching) ?? (row.strengths || row.percent || row.mode ? row : null);
}

function ReasonList({ label, items }: { label: string; items: string[] }) {
  if (items.length === 0) return null;
  return (
    <div>
      <p className="font-mono text-[10px] uppercase tracking-wider text-[#6b7280]">{label}</p>
      <ul className="mt-1 space-y-0.5 text-xs leading-relaxed text-[#9ca3af]">
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </div>
  );
}

function applicationNext(status: string, portal: "candidate" | "employer"): { label: string; href: string } {
  const s = status.toLowerCase();
  if (portal === "candidate") {
    if (s === "interview") return { label: "Open interviews", href: "/jobseeker/interviews" };
    if (s === "offer") return { label: "Review offer", href: "/jobseeker/offers" };
    if (s === "accepted" || s === "onboarding") return { label: "Continue onboarding", href: "/jobseeker/applications" };
    if (s === "screening" || s === "assessment") return { label: "Prepare for interview", href: "/jobseeker/interview-prep" };
    return { label: "Track application", href: "/jobseeker/applications" };
  }
  if (s === "interview") return { label: "Open interviews", href: "/company/interviews" };
  if (s === "offer") return { label: "Review offers", href: "/company/offers" };
  return { label: "Open pipeline", href: "/company/pipeline" };
}

function OpportunityCard({ row }: { row: Record<string, unknown> }) {
  const id = text(row.id || row.opportunity_id);
  const match = matchOf(row);
  const mode = text(match?.mode || row.mode);
  const percent = text(match?.percent);
  const location = [text(row.location || row.city), text(row.country)].filter(Boolean).join(", ");
  return (
    <article className={`${cardCls} space-y-3`}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="font-medium text-white">{text(row.title) || "Opportunity"}</p>
          <p className="mt-0.5 text-sm text-[#9ca3af]">
            {[text(row.company_name), location].filter(Boolean).join(" · ")}
          </p>
        </div>
        <div className="flex shrink-0 flex-col items-end gap-1">
          {mode && <StatusPill status={mode} tone="gold" />}
          {percent && <span className="font-mono text-[10px] text-[#d4af37]">{percent}% match</span>}
        </div>
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        <ReasonList label="Strengths" items={stringList(match?.strengths)} />
        <ReasonList label="Gaps" items={stringList(match?.gaps || match?.missing_skills)} />
      </div>
      {id && (
        <Link href={`/jobseeker/opportunities/${id}`} className="inline-flex text-sm text-[#d4af37] hover:underline">
          View opportunity
        </Link>
      )}
    </article>
  );
}

function CandidateCard({ row }: { row: Record<string, unknown> }) {
  const summary = asRecord(row.summary);
  const id = text(row.person_id || summary?.person_id || row.id);
  const name = text(summary?.name || row.display_name || row.name) || "Candidate";
  const headline = text(summary?.headline || row.headline || row.location);
  const match = matchOf(row);
  const mode = text(row.mode || match?.mode);
  const percent = text(row.percent || match?.percent);
  return (
    <article className={`${cardCls} space-y-3`}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="font-medium text-white">{name}</p>
          {headline && <p className="mt-0.5 text-sm text-[#9ca3af]">{headline}</p>}
        </div>
        <div className="flex shrink-0 flex-col items-end gap-1">
          {mode && <StatusPill status={mode} tone="gold" />}
          {percent && <span className="font-mono text-[10px] text-[#d4af37]">{percent}% match</span>}
        </div>
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        <ReasonList label="Strengths" items={stringList(row.strengths || match?.strengths)} />
        <ReasonList label="Gaps" items={stringList(row.gaps || match?.gaps)} />
      </div>
      {id && (
        <Link href={`/company/candidates/${id}`} className="inline-flex text-sm text-[#d4af37] hover:underline">
          Open professional profile
        </Link>
      )}
    </article>
  );
}

function ApplicationCard({ row, portal }: { row: Record<string, unknown>; portal: "candidate" | "employer" }) {
  const status = text(row.status);
  const next = applicationNext(status, portal);
  return (
    <article className={`${cardCls} space-y-3`}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="font-medium text-white">{text(row.title || row.job_title) || "Application"}</p>
          <p className="mt-0.5 text-sm text-[#9ca3af]">
            {[text(row.company_name), status ? `Stage: ${status.replaceAll("_", " ")}` : ""].filter(Boolean).join(" · ")}
          </p>
        </div>
        {status && <StatusPill status={status} />}
      </div>
      <Link href={next.href} className="inline-flex text-sm text-[#d4af37] hover:underline">
        {next.label}
      </Link>
    </article>
  );
}

function InterviewCard({ row, portal }: { row: Record<string, unknown>; portal: "candidate" | "employer" }) {
  const when = text(row.scheduled_at);
  const href = portal === "candidate" ? "/jobseeker/interviews" : "/company/interviews";
  return (
    <article className={`${cardCls} space-y-3`}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="font-medium text-white">{text(row.title || row.job_title) || "Interview"}</p>
          <p className="mt-0.5 text-sm text-[#9ca3af]">
            {[text(row.mode), when ? new Date(when).toLocaleString() : ""].filter(Boolean).join(" · ")}
          </p>
        </div>
        {text(row.status) && <StatusPill status={text(row.status)} />}
      </div>
      <Link href={href} className="inline-flex text-sm text-[#d4af37] hover:underline">
        {portal === "candidate" ? "Open interviews" : "Review interview"}
      </Link>
    </article>
  );
}

export function AthenaResults({
  results,
  portal,
}: {
  results: AthenaToolResult[];
  portal: "candidate" | "employer";
}) {
  if (results.length === 0) return null;
  return (
    <div className="space-y-3">
      {results.map((item, index) => {
        if (item.status === "error") {
          return (
            <div key={index} className="rounded-xl border border-red-900 bg-red-950/40 px-4 py-3 text-sm text-red-200">
              {item.tool ? `${item.tool}: ` : ""}
              {item.message || "Action failed."}
            </div>
          );
        }
        const payload = item.result ?? {};
        const rawItems = asList(payload.items);
        const isCandidate = (row: Record<string, unknown>) =>
          Boolean(row.person_id || asRecord(row.summary)?.person_id);
        const opportunities = asList(payload.results)
          .concat(rawItems.filter((row) => !isCandidate(row) && (row.title || row.company_name || row.opportunity_id)))
          .concat(asList(payload.opportunities));
        const candidates = asList(payload.candidates).concat(rawItems.filter(isCandidate));
        const applications = asList(payload.applications);
        const jobs = asList(payload.jobs);
        const interviews = asList(payload.interviews);

        return (
          <section key={index} className="space-y-3">
            <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-[#6b7280]">
              {item.tool?.replaceAll("_", " ") || "Structured intelligence"} · {item.status || "ok"}
            </p>
            {opportunities.length > 0 && (
              <div className="grid gap-3">
                {opportunities.slice(0, 6).map((row, i) => (
                  <OpportunityCard key={i} row={row} />
                ))}
              </div>
            )}
            {portal === "employer" &&
              (candidates.length > 0 ||
                (asList(payload.items).length > 0 && opportunities.length === 0 && applications.length === 0)) && (
                <div className="grid gap-3">
                  {(candidates.length > 0 ? candidates : asList(payload.items)).slice(0, 6).map((row, i) => (
                    <CandidateCard key={i} row={row} />
                  ))}
                </div>
              )}
            {applications.length > 0 && (
              <div className="space-y-2">
                {applications.slice(0, 8).map((row, i) => (
                  <ApplicationCard key={i} row={row} portal={portal} />
                ))}
              </div>
            )}
            {jobs.length > 0 && (
              <div className="space-y-2">
                {jobs.slice(0, 8).map((row, i) => (
                  <article key={i} className={`${cardCls} flex items-center justify-between gap-3`}>
                    <div>
                      <p className="font-medium text-white">{text(row.title) || "Job"}</p>
                      {text(row.location) && <p className="text-xs text-[#9ca3af]">{text(row.location)}</p>}
                    </div>
                    {text(row.status) && <StatusPill status={text(row.status)} />}
                  </article>
                ))}
              </div>
            )}
            {interviews.length > 0 && (
              <div className="space-y-2">
                {interviews.slice(0, 6).map((row, i) => (
                  <InterviewCard key={i} row={row} portal={portal} />
                ))}
              </div>
            )}
          </section>
        );
      })}
    </div>
  );
}
