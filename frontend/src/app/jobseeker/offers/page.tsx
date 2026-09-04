"use client";
/**
 * Offer Center — view terms and make an explicit accept/decline decision.
 * The authoritative offer document is always the company's own; this page
 * never generates binding documents.
 */
import { useCallback, useEffect, useState } from "react";

import { EmptyState, ErrorBanner, PageHeader, StatusPill, btnCls, cardCls, ghostBtnCls } from "@/components/candidate/ui";
import { api } from "@/lib/api/session";
import { Offer } from "@/lib/api/types";

export default function OffersPage() {
  const [offers, setOffers] = useState<Offer[]>([]);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const load = useCallback(async () => {
    try {
      setOffers(await api.get<Offer[]>("/jobseeker/offers"));
    } catch (e) {
      setError(String((e as Error).message ?? e));
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function decide(id: string, decision: "accepted" | "declined") {
    const verb = decision === "accepted" ? "accept" : "decline";
    if (!window.confirm(`Are you sure you want to ${verb} this offer?`)) return;
    try {
      await api.post(`/jobseeker/offers/${id}/decision`, { decision });
      setNotice(`Offer ${decision}.`);
      await load();
    } catch (e) {
      setError(String((e as Error).message ?? e));
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        kicker="Decisions"
        title="Offers"
        subtitle="Review terms and respond explicitly. Accepting updates your application lifecycle. This page never generates a binding letter."
      />

      {notice && <p className="text-sm text-emerald-400">{notice}</p>}
      {error && <ErrorBanner message={error} />}

      {offers.length === 0 && (
        <EmptyState
          title="No offers yet"
          body="When a company extends an offer on an application, it will appear here with the real terms from the backend."
          actionHref="/jobseeker/applications"
          actionLabel="View applications"
        />
      )}

      <div className="grid gap-4 lg:grid-cols-2">
        {offers.map((offer) => (
          <article key={offer.id} className={cardCls}>
            <div className="flex items-start justify-between">
              <h2 className="text-lg font-semibold">
                {offer.salary_amount
                  ? `${offer.salary_currency ?? "USD"} ${offer.salary_amount.toLocaleString()}`
                  : "Offer"}
              </h2>
              <StatusPill status={offer.status} />
            </div>

            <dl className="mt-3 space-y-1.5 text-sm">
              {offer.equity && (
                <div className="flex justify-between">
                  <dt className="text-neutral-400">Equity</dt>
                  <dd>{offer.equity}</dd>
                </div>
              )}
              {offer.start_date && (
                <div className="flex justify-between">
                  <dt className="text-neutral-400">Start date</dt>
                  <dd>{offer.start_date}</dd>
                </div>
              )}
              {offer.location && (
                <div className="flex justify-between">
                  <dt className="text-neutral-400">Location</dt>
                  <dd>{offer.location}</dd>
                </div>
              )}
            </dl>

            {offer.benefits_summary && (
              <p className="mt-3 text-sm text-neutral-500 dark:text-neutral-400">
                {offer.benefits_summary}
              </p>
            )}
            {offer.terms_summary && (
              <p className="mt-2 text-xs text-neutral-400">{offer.terms_summary}</p>
            )}
            {offer.expires_at && (
              <p className="mt-2 text-xs text-amber-600 dark:text-amber-400">
                Responds by {new Date(offer.expires_at).toLocaleString()}
              </p>
            )}

            {offer.status === "pending" && (
              <div className="mt-4 flex gap-2">
                <button type="button" className={btnCls} onClick={() => decide(offer.id, "accepted")}>
                  Accept offer
                </button>
                <button type="button" className={ghostBtnCls} onClick={() => decide(offer.id, "declined")}>
                  Decline
                </button>
              </div>
            )}
          </article>
        ))}
      </div>
    </div>
  );
}
