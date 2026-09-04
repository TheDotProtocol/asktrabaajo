"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import {
  EmptyState,
  ErrorBanner,
  LoadingState,
  PageHeader,
  StatusPill,
  btnCls,
  cardCls,
  inputCls,
  labelCls,
} from "@/components/candidate/ui";
import { useCanonicalAuth } from "@/context/AuthContext";
import { useOrg } from "@/context/OrgContext";
import { api } from "@/lib/api/session";
import { CompanyDashboard, MyOrganization } from "@/lib/api/types";

export default function CompanyHome() {
  const { reload } = useCanonicalAuth();
  const { organizationId, selectOrganization } = useOrg();
  const [orgs, setOrgs] = useState<MyOrganization[]>([]);
  const [dash, setDash] = useState<CompanyDashboard | null>(null);
  const [newName, setNewName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const loadOrgs = useCallback(async () => {
    const rows = await api.get<MyOrganization[]>("/organizations");
    const employers = rows.filter((r) => r.kind === "employer" || r.kind === "recruiter");
    setOrgs(employers);
    return employers;
  }, []);

  const loadDash = useCallback(async (orgId: string) => {
    setDash(await api.get<CompanyDashboard>(`/company/${orgId}/dashboard`));
  }, []);

  useEffect(() => {
    loadOrgs()
      .then((employers) => {
        if (employers.length === 0) return;
        const match = employers.find((o) => o.organization_id === organizationId) ?? employers[0];
        if (match.organization_id !== organizationId) selectOrganization(match.organization_id);
        return loadDash(match.organization_id);
      })
      .catch((e) => setError(String((e as Error).message ?? e)));
  }, [loadOrgs, loadDash, organizationId, selectOrganization]);

  async function createOrg() {
    if (!newName.trim() || busy) return;
    setBusy(true);
    setError("");
    try {
      const created = await api.post<{ id: string }>("/organizations", {
        name: newName.trim(),
        kind: "employer",
      });
      setNewName("");
      await reload();
      selectOrganization(created.id);
      await loadOrgs();
      await loadDash(created.id);
    } catch (e) {
      setError(String((e as Error).message ?? e));
    } finally {
      setBusy(false);
    }
  }

  if (error && !dash && orgs.length > 0) {
    return <ErrorBanner message={error} onRetry={() => window.location.reload()} />;
  }

  if (orgs.length === 0 && !busy) {
    return (
      <div className="mx-auto max-w-xl space-y-6 py-10">
        <PageHeader
          kicker="Employer OS"
          title="Set up your company workspace"
          subtitle="Creating an organization makes you its administrator. Jobs, pipeline, and billing stay scoped to this organization."
        />
        <form
          onSubmit={(e) => {
            e.preventDefault();
            void createOrg();
          }}
          className={`${cardCls} space-y-3`}
        >
          <input
            className={inputCls}
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            placeholder="Company name — mark DEV if this is a fixture"
          />
          {error && <ErrorBanner message={error} />}
          <button type="submit" disabled={busy} className={btnCls}>
            Create organization
          </button>
        </form>
      </div>
    );
  }

  if (!dash) return <LoadingState label="Opening the command center…" />;

  const stats = [
    { label: "Open jobs", value: dash.open_jobs, href: "/company/jobs" },
    { label: "Applications", value: dash.applications_total, href: "/company/pipeline" },
    { label: "Need review", value: dash.needs_review, href: "/company/pipeline" },
    { label: "Interviews today", value: dash.interviews_today, href: "/company/interviews" },
    { label: "Upcoming interviews", value: dash.interviews_upcoming, href: "/company/interviews" },
    { label: "Offers pending", value: dash.offers_pending, href: "/company/offers" },
    { label: "Offers accepted", value: dash.offers_accepted, href: "/company/offers" },
  ];

  return (
    <div className="space-y-8">
      <PageHeader
        kicker="Command center"
        title={dash.organization.name}
        subtitle="Hiring activity for the selected organization. Counts come from the canonical company dashboard — nothing is invented here."
        actions={<StatusPill status={dash.my_role} />}
      />
      {error && <ErrorBanner message={error} />}

      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => (
          <Link key={stat.label} href={stat.href} className={cardCls}>
            <p className={labelCls}>{stat.label}</p>
            <p className="mt-2 text-3xl font-semibold">{stat.value}</p>
          </Link>
        ))}
      </section>

      <section className="grid gap-6 lg:grid-cols-3">
        <div className={`${cardCls} lg:col-span-2`}>
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-sm font-semibold">Recent applications</h2>
            <Link href="/company/pipeline" className="text-sm text-[#d4af37] hover:underline">
              Pipeline
            </Link>
          </div>
          {dash.recent_applications.length === 0 ? (
            <EmptyState
              title="No applications yet"
              body="Publish a job so candidates can apply. This list stays empty until the backend records one."
              actionHref="/company/jobs"
              actionLabel="Open jobs"
            />
          ) : (
            <ul className="space-y-2">
              {dash.recent_applications.map((a) => (
                <li key={a.id} className="flex items-center justify-between gap-3 rounded-lg border border-[#23272a] px-3 py-2 text-sm">
                  <div className="min-w-0">
                    <p className="truncate font-medium">{a.job_title ?? "Opportunity"}</p>
                    <p className="truncate text-xs text-[#9ca3af]">{a.candidate_name}</p>
                  </div>
                  <StatusPill status={a.status} />
                </li>
              ))}
            </ul>
          )}
        </div>
        <div className={cardCls}>
          <h2 className="text-sm font-semibold">Workspace</h2>
          <div className="mt-4 space-y-2 text-sm">
            <Link href="/company/jobs/new" className="block rounded-lg border border-[#23272a] p-3 hover:border-[#d4af37]/40">
              Create a job draft
            </Link>
            <Link href="/company/profile" className="block rounded-lg border border-[#23272a] p-3 hover:border-[#d4af37]/40">
              Company profile
            </Link>
            <Link href="/company/candidates" className="block rounded-lg border border-[#23272a] p-3 hover:border-[#d4af37]/40">
              Talent Graph
            </Link>
          </div>
          <p className={`${labelCls} mt-5`}>Your permissions</p>
          <div className="mt-2 flex flex-wrap gap-1">
            {dash.permissions.slice(0, 10).map((p) => (
              <span key={p} className="rounded border border-[#23272a] px-1.5 py-0.5 font-mono text-[10px] text-[#9ca3af]">
                {p}
              </span>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}
