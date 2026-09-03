"use client";
/**
 * Company Home — the employer command center.
 *
 * Answers: what is happening with our hiring, and what needs action now.
 * The page is organization-scoped: the user picks an employer/recruiter org
 * they belong to (created self-service — the creator becomes org_admin), then
 * every number comes from the canonical /api/v1/company dashboard.
 */
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { api, getAccessToken } from "@/lib/api/session";
import { CompanyDashboard, MyOrganization } from "@/lib/api/types";

const ORG_KEY = "asktrabaajo_org_id";
const cardCls =
  "rounded-xl border border-neutral-200 bg-white p-5 dark:border-neutral-800 dark:bg-neutral-900";
const statCls = "text-3xl font-semibold tracking-tight";
const labelCls = "text-xs uppercase tracking-wide text-neutral-400";

function orgFromStorage(): string {
  if (typeof window === "undefined") return "";
  return window.localStorage.getItem(ORG_KEY) ?? "";
}

export default function CompanyHome() {
  const router = useRouter();
  const [orgs, setOrgs] = useState<MyOrganization[]>([]);
  const [activeOrg, setActiveOrg] = useState<MyOrganization | null>(null);
  const [dash, setDash] = useState<CompanyDashboard | null>(null);
  const [newName, setNewName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const loadOrgs = useCallback(async () => {
    const rows = await api.get<MyOrganization[]>("/organizations");
    const employers = rows.filter(
      (r) => r.kind === "employer" || r.kind === "recruiter"
    );
    setOrgs(employers);
    const stored = orgFromStorage();
    const match =
      employers.find((o) => o.organization_id === stored) ?? employers[0] ?? null;
    setActiveOrg(match);
    return employers;
  }, []);

  const loadDash = useCallback(async (orgId: string) => {
    setDash(await api.get<CompanyDashboard>(`/company/${orgId}/dashboard`));
  }, []);

  useEffect(() => {
    if (!getAccessToken()) {
      router.push("/id");
      return;
    }
    loadOrgs()
      .then((employers) => {
        if (employers.length > 0) {
          const match =
            employers.find((o) => o.organization_id === orgFromStorage()) ??
            employers[0];
          window.localStorage.setItem(ORG_KEY, match.organization_id);
          return loadDash(match.organization_id);
        }
      })
      .catch((e) => setError(String((e as Error).message ?? e)));
  }, [loadOrgs, loadDash, router]);

  async function selectOrg(org: MyOrganization) {
    setActiveOrg(org);
    window.localStorage.setItem(ORG_KEY, org.organization_id);
    setError("");
    try {
      await loadDash(org.organization_id);
    } catch (e) {
      setError(String((e as Error).message ?? e));
    }
  }

  async function createOrg() {
    if (!newName.trim() || busy) return;
    setBusy(true);
    setError("");
    try {
      const created = await api.post<{ id: string; name: string; slug: string }>(
        "/organizations",
        { name: newName.trim(), kind: "employer" }
      );
      setNewName("");
      const fresh = await loadOrgs();
      const org =
        fresh.find((o) => o.organization_id === created.id) ?? null;
      if (org) {
        await selectOrg(org);
      }
    } catch (e) {
      setError(String((e as Error).message ?? e));
    } finally {
      setBusy(false);
    }
  }

  if (error && !dash) {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50 p-5 text-sm text-red-700 dark:border-red-900 dark:bg-red-950 dark:text-red-300">
        {error} —{" "}
        <button
          onClick={() => window.location.reload()}
          className="underline"
        >
          retry
        </button>
      </div>
    );
  }

  // No employer organization yet — offer self-service creation.
  if (orgs.length === 0 && !busy) {
    return (
      <div className="mx-auto max-w-xl py-16">
        <h1 className="text-2xl font-semibold tracking-tight">
          Set up your company workspace
        </h1>
        <p className="mt-2 text-sm text-neutral-500 dark:text-neutral-400">
          Creating an organization makes you its administrator (org_admin). You
          can then create jobs, publish them into the opportunity catalogue, and
          manage your candidate pipeline.
        </p>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            createOrg();
          }}
          className="mt-6 space-y-3"
        >
          <input
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            placeholder="Company name — e.g. Acme Technologies"
            className="w-full rounded-lg border border-neutral-300 bg-white px-3 py-2 text-sm dark:border-neutral-700 dark:bg-neutral-900"
          />
          {error && (
            <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
          )}
          <button
            type="submit"
            disabled={busy}
            className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500 disabled:opacity-50"
          >
            Create organization
          </button>
        </form>
      </div>
    );
  }

  if (!activeOrg || !dash) {
    return (
      <div className="py-20 text-center text-neutral-400">
        Loading your hiring command center…
      </div>
    );
  }

  const stats: { label: string; value: number; href?: string; alert?: boolean }[] = [
    { label: "Open jobs", value: dash.open_jobs, href: "/company/jobs" },
    { label: "Applications", value: dash.applications_total, href: "/company/pipeline" },
    {
      label: "Need review",
      value: dash.needs_review,
      href: "/company/pipeline",
      alert: dash.needs_review > 0,
    },
    { label: "Interviews today", value: dash.interviews_today },
    { label: "Interviews upcoming", value: dash.interviews_upcoming },
    {
      label: "Offers awaiting response",
      value: dash.offers_pending,
      alert: dash.offers_pending > 0,
    },
    { label: "Offers accepted", value: dash.offers_accepted },
  ];

  return (
    <div className="space-y-8">
      {/* Org switcher */}
      <section className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm text-neutral-400">Hiring, operating-system style.</p>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight">
            {activeOrg.name}
          </h1>
        </div>
        <div className="flex items-center gap-2 text-sm">
          <select
            value={activeOrg.organization_id}
            onChange={(e) => {
              const org = orgs.find((o) => o.organization_id === e.target.value);
              if (org) selectOrg(org);
            }}
            className="rounded-lg border border-neutral-300 bg-white px-3 py-1.5 text-sm dark:border-neutral-700 dark:bg-neutral-900"
          >
            {orgs.map((o) => (
              <option key={o.organization_id} value={o.organization_id}>
                {o.name}
              </option>
            ))}
          </select>
          <span className="rounded-full bg-indigo-50 px-2.5 py-0.5 text-xs font-medium text-indigo-600 dark:bg-indigo-950 dark:text-indigo-300">
            {dash.my_role.replace("_", " ")}
          </span>
        </div>
      </section>

      {/* Priority actions */}
      {dash.needs_review > 0 || dash.interviews_today > 0 || dash.offers_pending > 0 ? (
        <section className="flex flex-wrap gap-2 text-sm">
          {dash.needs_review > 0 && (
            <Link
              href="/company/pipeline"
              className="rounded-lg bg-indigo-600 px-3 py-1.5 font-medium text-white hover:bg-indigo-500"
            >
              {dash.needs_review} candidate{dash.needs_review === 1 ? "" : "s"} need
              review →
            </Link>
          )}
          {dash.interviews_today > 0 && (
            <span className="rounded-lg border border-indigo-200 bg-indigo-50 px-3 py-1.5 text-indigo-700 dark:border-indigo-900 dark:bg-indigo-950 dark:text-indigo-300">
              {dash.interviews_today} interview{dash.interviews_today === 1 ? "" : "s"} today
            </span>
          )}
          {dash.offers_pending > 0 && (
            <span className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-1.5 text-amber-700 dark:border-amber-900 dark:bg-amber-950 dark:text-amber-300">
              {dash.offers_pending} offer{dash.offers_pending === 1 ? "" : "s"} awaiting response
            </span>
          )}
        </section>
      ) : null}

      {/* Stats */}
      <section className="grid gap-4 sm:grid-cols-2 md:grid-cols-4">
        {stats.map((s) =>
          s.href ? (
            <Link key={s.label} href={s.href} className={cardCls}>
              <p className={labelCls}>{s.label}</p>
              <p className={`${statCls} ${s.alert ? "text-indigo-600 dark:text-indigo-400" : ""}`}>
                {s.value}
              </p>
            </Link>
          ) : (
            <div key={s.label} className={cardCls}>
              <p className={labelCls}>{s.label}</p>
              <p className={`${statCls} ${s.alert ? "text-amber-500" : ""}`}>{s.value}</p>
            </div>
          )
        )}
      </section>

      <section className="grid gap-6 lg:grid-cols-3">
        {/* Recent applications */}
        <div className={`${cardCls} lg:col-span-2`}>
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold">Recent applications</h2>
            <Link
              href="/company/pipeline"
              className="text-sm text-indigo-600 hover:underline dark:text-indigo-400"
            >
              Full pipeline →
            </Link>
          </div>
          {dash.recent_applications.length === 0 && (
            <p className="text-sm text-neutral-400">
              No applications yet — publish a job to open discovery.
            </p>
          )}
          <div className="space-y-2">
            {dash.recent_applications.map((a) => (
              <Link
                key={a.id}
                href="/company/pipeline"
                className="flex items-center justify-between gap-4 rounded-lg border border-neutral-200 px-4 py-3 text-sm hover:border-indigo-400 dark:border-neutral-800"
              >
                <div className="min-w-0">
                  <p className="truncate font-medium">{a.job_title ?? "Opportunity"}</p>
                  <p className="truncate text-xs text-neutral-400">{a.candidate_name}</p>
                </div>
                <span className="shrink-0 rounded-full bg-neutral-100 px-2 py-0.5 text-xs capitalize text-neutral-600 dark:bg-neutral-800 dark:text-neutral-300">
                  {a.status.replace("_", " ")}
                </span>
              </Link>
            ))}
          </div>
        </div>

        {/* Workspace */}
        <div className={`${cardCls} lg:col-span-1`}>
          <h2 className="text-sm font-semibold">Workspace</h2>
          <div className="mt-4 space-y-2 text-sm">
            <Link
              href="/company/jobs"
              className="block rounded-lg border border-neutral-200 p-3 hover:border-indigo-400 dark:border-neutral-800"
            >
              <span className="font-medium">Jobs</span>
              <p className="mt-0.5 text-xs text-neutral-400">
                Create, publish and manage postings
              </p>
            </Link>
            <Link
              href="/company/pipeline"
              className="block rounded-lg border border-neutral-200 p-3 hover:border-indigo-400 dark:border-neutral-800"
            >
              <span className="font-medium">Candidate pipeline</span>
              <p className="mt-0.5 text-xs text-neutral-400">
                Review, decide, interview, offer
              </p>
            </Link>
            <div className="rounded-lg border border-neutral-200 p-3 dark:border-neutral-800">
              <p className="text-xs uppercase tracking-wide text-neutral-400">
                Your permissions
              </p>
              <div className="mt-2 flex flex-wrap gap-1">
                {dash.permissions.slice(0, 8).map((p) => (
                  <span
                    key={p}
                    className="rounded bg-neutral-100 px-1.5 py-0.5 text-[10px] text-neutral-500 dark:bg-neutral-800 dark:text-neutral-400"
                  >
                    {p}
                  </span>
                ))}
                {dash.permissions.length > 8 && (
                  <span className="text-[10px] text-neutral-400">
                    +{dash.permissions.length - 8}
                  </span>
                )}
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
