"use client";
/**
 * Employer Billing (Phase 17) — org-scoped commerce dashboard.
 *
 * Jobseeker core stays free; this surface is for authorized org members
 * (billing.read / billing.manage). It shows the current plan, entitlements
 * with usage, and invoices for the SELECTED organization only. The only
 * catalog plan is the configurable FREE plan — pricing is never invented
 * in the client, and no real payment runs (mock/sandbox provider only).
 */
import { useCallback, useEffect, useState } from "react";

import { api } from "@/lib/api/session";
import {
  BillingPlan,
  EntitlementState,
  InvoiceOut,
  SubscriptionOut,
} from "@/lib/api/types";
import { useOrg } from "@/context/OrgContext";

const cardCls =
  "rounded-xl border border-neutral-200 bg-white p-5 dark:border-neutral-800 dark:bg-neutral-900";
const btnCls =
  "rounded bg-amber-500 px-4 py-2 text-sm font-medium text-black hover:bg-amber-400 disabled:opacity-50";
const secondaryBtnCls =
  "rounded border border-neutral-300 px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-100 disabled:opacity-50 dark:border-neutral-700 dark:text-neutral-200 dark:hover:bg-neutral-800";

const STATUS_LABEL: Record<string, string> = {
  trial: "Trial",
  active: "Active",
  past_due: "Past due",
  paused: "Paused",
  cancelled: "Cancelled",
  expired: "Expired",
};

const ENTITLEMENT_LABEL: Record<string, string> = {
  "jobs.create": "Job postings created",
  "jobs.active": "Active job postings",
  "candidate.search": "Candidate searches",
  "candidate.outreach": "Outreach requests",
  "ai.athena": "Athena AI usage",
  "ai.interview": "AI interviews",
  analytics: "Analytics",
  premium_support: "Premium support",
};

const INVOICE_STATUS_LABEL: Record<string, string> = {
  draft: "Draft",
  issued: "Issued",
  paid: "Paid",
  void: "Void",
  past_due: "Past due",
};

export default function EmployerBillingPage() {
  const { organizationId: orgId, memberships, selectOrganization } = useOrg();
  const orgs = memberships.map((m) => ({
    organization_id: m.organization_id,
    name: m.organization_name,
  }));
  const [plans, setPlans] = useState<BillingPlan[]>([]);
  const [subscription, setSubscription] = useState<SubscriptionOut | null>(null);
  const [entitlements, setEntitlements] = useState<Record<string, EntitlementState>>({});
  const [invoices, setInvoices] = useState<InvoiceOut[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    if (!orgId) return;
    setBusy(true);
    setError("");
    try {
      const [plansRes, subRes, entRes, invRes] = await Promise.all([
        api.get<{ plans: BillingPlan[] }>("/billing/plans"),
        api.get<{ subscription: SubscriptionOut | null }>(
          `/billing/subscription?organization_id=${encodeURIComponent(orgId)}`
        ),
        api.get<{ entitlements: Record<string, EntitlementState> }>(
          `/billing/entitlements?organization_id=${encodeURIComponent(orgId)}`
        ),
        api.get<{ invoices: InvoiceOut[] }>(
          `/billing/invoices?organization_id=${encodeURIComponent(orgId)}`
        ),
      ]);
      setPlans(plansRes.plans);
      setSubscription(subRes.subscription);
      setEntitlements(entRes.entitlements);
      setInvoices(invRes.invoices);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }, [orgId]);

  useEffect(() => {
    if (orgId) load();
  }, [orgId, load]);

  const subscribe = async (planCode: string) => {
    setBusy(true);
    setError("");
    try {
      await api.post(
        `/billing/subscriptions?organization_id=${encodeURIComponent(orgId)}`,
        { plan_code: planCode }
      );
      await load();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const cancel = async () => {
    setBusy(true);
    setError("");
    try {
      await api.post(
        `/billing/subscriptions/cancel?organization_id=${encodeURIComponent(orgId)}`,
        { reason: "employer_requested" }
      );
      await load();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mx-auto max-w-5xl space-y-4 p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Billing</h1>
          <p className="text-sm text-neutral-500 dark:text-neutral-400">
            Organization subscription, entitlements and invoices. Jobseeker core stays free.
          </p>
        </div>
        {orgs.length > 1 && (
          <select
            value={orgId}
            onChange={(e) => selectOrganization(e.target.value)}
            className="rounded border border-neutral-300 bg-white px-3 py-1.5 text-sm dark:border-neutral-700 dark:bg-neutral-900"
          >
            {orgs.map((o) => (
              <option key={o.organization_id} value={o.organization_id}>
                {o.name}
              </option>
            ))}
          </select>
        )}
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700 dark:border-red-900 dark:bg-red-950 dark:text-red-300">
          {error}
        </div>
      )}

      {/* Current subscription */}
      <section className={cardCls}>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-sm font-semibold uppercase tracking-wide text-neutral-500">
              Current plan
            </h2>
            {subscription ? (
              <div className="mt-1">
                <p className="text-lg font-semibold">
                  {subscription.plan_name ?? subscription.plan_code}{" "}
                  <span
                    className={`ml-2 rounded px-2 py-0.5 text-xs font-medium ${
                      subscription.status === "active"
                        ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/50 dark:text-emerald-300"
                        : "bg-neutral-100 text-neutral-600 dark:bg-neutral-800 dark:text-neutral-300"
                    }`}
                  >
                    {STATUS_LABEL[subscription.status] ?? subscription.status}
                  </span>
                </p>
                <p className="text-sm text-neutral-500 dark:text-neutral-400">
                  {subscription.price === "0.00" ? "Free" : `${subscription.currency} ${subscription.price}`}
                  {" · "}
                  {subscription.billing_interval === "year" ? "yearly" : "monthly"}
                  {subscription.current_period_end
                    ? ` · renews ${new Date(subscription.current_period_end).toLocaleDateString()}`
                    : ""}
                </p>
              </div>
            ) : (
              <p className="mt-1 text-neutral-500 dark:text-neutral-400">No active subscription.</p>
            )}
          </div>
          {subscription ? (
            <button className={secondaryBtnCls} onClick={cancel} disabled={busy}>
              Cancel subscription
            </button>
          ) : (
            plans
              .filter((p) => p.published)
              .map((p) => (
                <button key={p.code} className={btnCls} onClick={() => subscribe(p.code)} disabled={busy}>
                  Start {p.name} plan
                </button>
              ))
          )}
        </div>
      </section>

      {/* Entitlements + usage */}
      <section className={cardCls}>
        <h2 className="text-sm font-semibold uppercase tracking-wide text-neutral-500">
          Entitlements & usage
        </h2>
        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          {Object.entries(entitlements).map(([code, state]) => (
            <div
              key={code}
              className="rounded-lg border border-neutral-200 p-3 dark:border-neutral-800"
            >
              <div className="flex items-center justify-between gap-2">
                <span className="text-sm font-medium">
                  {ENTITLEMENT_LABEL[code] ?? code}
                </span>
                <span
                  className={`rounded px-1.5 py-0.5 text-xs ${
                    state.unlimited
                      ? "bg-neutral-100 text-neutral-500 dark:bg-neutral-800 dark:text-neutral-400"
                      : state.within_limit
                        ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/50 dark:text-emerald-300"
                        : "bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300"
                  }`}
                >
                  {state.unlimited
                    ? "Unlimited"
                    : `${state.used} / ${Math.round(Number(state.limit ?? "0"))}`}
                </span>
              </div>
              <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-neutral-100 dark:bg-neutral-800">
                <div
                  className={`h-full rounded-full ${
                    state.unlimited
                      ? "bg-neutral-300 dark:bg-neutral-700"
                      : state.within_limit
                        ? "bg-emerald-400"
                        : "bg-red-400"
                  }`}
                  style={{
                    width: state.unlimited
                      ? "0%"
                      : `${Math.min(100, Math.round((state.used / Math.max(1, Number(state.limit ?? "1"))) * 100))}%`,
                  }}
                />
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Invoices */}
      <section className={cardCls}>
        <h2 className="text-sm font-semibold uppercase tracking-wide text-neutral-500">
          Invoices
        </h2>
        {invoices.length === 0 ? (
          <p className="mt-2 text-sm text-neutral-500 dark:text-neutral-400">
            No invoices yet.
          </p>
        ) : (
          <table className="mt-3 w-full text-sm">
            <thead>
              <tr className="border-b border-neutral-200 text-left text-neutral-500 dark:border-neutral-800">
                <th className="py-1.5 pr-3 font-medium">Number</th>
                <th className="py-1.5 pr-3 font-medium">Status</th>
                <th className="py-1.5 pr-3 font-medium">Issued</th>
                <th className="py-1.5 text-right font-medium">Total</th>
              </tr>
            </thead>
            <tbody>
              {invoices.map((inv) => (
                <tr key={inv.invoice_id} className="border-b border-neutral-100 dark:border-neutral-900">
                  <td className="py-2 pr-3 font-mono text-xs">{inv.invoice_number}</td>
                  <td className="py-2 pr-3">
                    <span className="rounded bg-neutral-100 px-1.5 py-0.5 text-xs text-neutral-600 dark:bg-neutral-800 dark:text-neutral-300">
                      {INVOICE_STATUS_LABEL[inv.status] ?? inv.status}
                    </span>
                  </td>
                  <td className="py-2 pr-3 text-neutral-500 dark:text-neutral-400">
                    {inv.issued_at ? new Date(inv.issued_at).toLocaleDateString() : "—"}
                  </td>
                  <td className="py-2 text-right font-medium">
                    {inv.currency} {Number(inv.total).toFixed(2)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <p className="text-xs text-neutral-400 dark:text-neutral-600">
        Payments run on the sandbox provider in development. No production charges are ever made
        from this screen.
      </p>
    </div>
  );
}
