"use client";

import { useCallback, useEffect, useState } from "react";

import {
  EmptyState,
  ErrorBanner,
  LoadingState,
  PageHeader,
  StatusPill,
  btnCls,
  cardCls,
  ghostBtnCls,
} from "@/components/candidate/ui";
import { useOrg } from "@/context/OrgContext";
import { api } from "@/lib/api/session";
import { CompanyOffer } from "@/lib/api/types";

export default function CompanyOffersPage() {
  const { organizationId } = useOrg();
  const [rows, setRows] = useState<CompanyOffer[] | null>(null);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    if (!organizationId) return;
    try {
      setRows(await api.get<CompanyOffer[]>(`/company/${organizationId}/offers`));
      setError("");
    } catch (e) {
      setError(String((e as Error).message ?? e));
    }
  }, [organizationId]);

  useEffect(() => {
    void load();
  }, [load]);

  async function send(id: string) {
    if (!organizationId || !window.confirm("Send this offer to the candidate?")) return;
    try {
      await api.post(`/company/${organizationId}/offers/${id}/send`);
      await load();
    } catch (e) {
      setError(String((e as Error).message ?? e));
    }
  }

  async function withdraw(id: string) {
    if (!organizationId || !window.confirm("Withdraw this offer?")) return;
    try {
      await api.post(`/company/${organizationId}/offers/${id}/withdraw`);
      await load();
    } catch (e) {
      setError(String((e as Error).message ?? e));
    }
  }

  if (!organizationId) {
    return <EmptyState title="Select an organization" body="Offers are tenant-scoped." actionHref="/company" actionLabel="Command center" />;
  }
  if (error && !rows) return <ErrorBanner message={error} onRetry={() => void load()} />;
  if (!rows) return <LoadingState />;

  return (
    <div className="space-y-6">
      <PageHeader
        kicker="Decisions"
        title="Offers"
        subtitle="Create offers from the pipeline. Send and withdraw use backend state transitions. Candidates accept or decline on their side."
      />
      {error && <ErrorBanner message={error} />}
      {rows.length === 0 ? (
        <EmptyState
          title="No offers yet"
          body="Issue an offer from an application review. This list stays empty until the backend records one."
          actionHref="/company/pipeline"
          actionLabel="Open pipeline"
        />
      ) : (
        <ul className="grid gap-4 lg:grid-cols-2">
          {rows.map((offer) => (
            <li key={offer.id} className={cardCls}>
              <div className="flex items-start justify-between gap-3">
                <p className="font-medium">
                  {offer.salary_amount
                    ? `${offer.salary_currency ?? "USD"} ${offer.salary_amount.toLocaleString()}`
                    : "Offer"}
                </p>
                <StatusPill status={offer.status} />
              </div>
              <div className="mt-3 flex gap-2">
                {offer.status === "draft" && (
                  <button type="button" className={btnCls} onClick={() => void send(offer.id)}>Send</button>
                )}
                {["draft", "pending", "sent"].includes(offer.status) && (
                  <button type="button" className={ghostBtnCls} onClick={() => void withdraw(offer.id)}>Withdraw</button>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
