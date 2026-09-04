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

function OpportunityCard({ row, hrefBase }: { row: Record<string, unknown>; hrefBase: string }) {
  const id = text(row.id || row.opportunity_id);
  const match = asRecord(row.match) ?? asRecord(row.matching);
  const mode = text(match?.mode || row.mode);
  return (
    <article className={`${cardCls} space-y-2`}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="font-medium text-white">{text(row.title) || "Opportunity"}</p>
          <p className="text-sm text-[#9ca3af]">{[text(row.company_name), text(row.location || row.city)].filter(Boolean).join(" · ")}</p>
        </div>
        {mode && <StatusPill status={mode} tone="gold" />}
      </div>
      {Array.isArray(row.skills_required) && row.skills_required.length > 0 && (
        <p className="text-xs text-[#6b7280]">Skills: {(row.skills_required as unknown[]).slice(0, 6).map(text).join(", ")}</p>
      )}
      {id && (
        <Link href={`${hrefBase}/${id}`} className="text-sm text-[#d4af37] hover:underline">
          Open
        </Link>
      )}
    </article>
  );
}

function CandidateCard({ row }: { row: Record<string, unknown> }) {
  const id = text(row.person_id || row.id);
  return (
    <article className={`${cardCls} space-y-2`}>
      <p className="font-medium text-white">{text(row.display_name || row.name) || "Candidate"}</p>
      <p className="text-sm text-[#9ca3af]">{text(row.headline || row.location)}</p>
      {id && (
        <Link href={`/company/candidates/${id}`} className="text-sm text-[#d4af37] hover:underline">
          Open professional profile
        </Link>
      )}
    </article>
  );
}

function ApplicationCard({ row, portal }: { row: Record<string, unknown>; portal: "candidate" | "employer" }) {
  const id = text(row.application_id || row.id);
  const href = portal === "candidate" ? "/jobseeker/applications" : "/company/pipeline";
  return (
    <article className={`${cardCls} flex items-center justify-between gap-3`}>
      <div>
        <p className="font-medium text-white">{text(row.title || row.job_title) || "Application"}</p>
        <p className="text-xs text-[#9ca3af]">{text(row.company_name)}</p>
      </div>
      <div className="flex items-center gap-2">
        {text(row.status) && <StatusPill status={text(row.status)} />}
        <Link href={href} className="text-sm text-[#d4af37] hover:underline">
          {id ? "Open" : "Pipeline"}
        </Link>
      </div>
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
        const opportunities = asList(payload.results).concat(asList(payload.items)).concat(asList(payload.opportunities));
        const candidates = asList(payload.candidates).concat(asList(payload.items).filter((row) => row.person_id));
        const applications = asList(payload.applications);
        const jobs = asList(payload.jobs);
        const interviews = asList(payload.interviews);

        return (
          <section key={index} className="space-y-2">
            <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-[#6b7280]">
              {item.tool?.replaceAll("_", " ") || "Result"} · {item.status || "ok"}
            </p>
            {opportunities.length > 0 && (
              <div className="grid gap-3 md:grid-cols-2">
                {opportunities.slice(0, 6).map((row, i) => (
                  <OpportunityCard key={i} row={row} hrefBase="/jobseeker/opportunities" />
                ))}
              </div>
            )}
            {portal === "employer" && (candidates.length > 0 || (asList(payload.items).length > 0 && opportunities.length === 0 && applications.length === 0)) && (
              <div className="grid gap-3 md:grid-cols-2">
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
                  <article key={i} className={`${cardCls} flex justify-between gap-3`}>
                    <p className="font-medium">{text(row.title) || "Job"}</p>
                    {text(row.status) && <StatusPill status={text(row.status)} />}
                  </article>
                ))}
              </div>
            )}
            {interviews.length > 0 && (
              <div className="space-y-2">
                {interviews.slice(0, 6).map((row, i) => (
                  <article key={i} className={cardCls}>
                    <p className="font-medium">{text(row.title) || "Interview"}</p>
                    <p className="text-xs text-[#9ca3af]">{text(row.scheduled_at || row.status)}</p>
                  </article>
                ))}
              </div>
            )}
          </section>
        );
      })}
    </div>
  );
}
