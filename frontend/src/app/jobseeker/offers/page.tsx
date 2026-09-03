"use client";
/**
 * Offer Center — view terms and make an explicit accept/decline decision.
 * The authoritative offer document is always the company's own; this page
 * never generates binding documents.
 */
import { useCallback, useEffect, useState } from "react";

import { api } from "@/lib/api/session";
import { Offer } from "@/lib/api/types";

const cardCls =
  "rounded-xl border border-neutral-200 bg-white p-5 dark:border-neutral-800 dark:bg-neutral-900";
const btnCls =
  "rounded bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-500";
const declineCls =
  "rounded border border-neutral-300 px-4 py-2 text-sm text-neutral-600 hover:border-red-400 hover:text-red-500 dark:border-neutral-700 dark:text-neutral-300";

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
      <section>
        <h1 className="text-2xl font-semibold tracking-tight">Offers</h1>
        <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
          Review terms and respond explicitly. Accepting an offer updates your
          application lifecycle and career timeline.
        </p>
      </section>

      {notice && (
        <div className="rounded-lg border border-emerald-300 bg-emerald-50 px-4 py-2 text-sm text-emerald-700 dark:border-emerald-800 dark:bg-emerald-950 dark:text-emerald-300">
          {notice}
        </div>
      )}
      {error && (
        <div className="rounded-lg border border-red-300 bg-red-50 px-4 py-2 text-sm text-red-700 dark:border-red-900 dark:bg-red-950 dark:text-red-300">
          {error}
        </div>
      )}

      {offers.length === 0 && (
        <div className={cardCls}>
          <p className="text-center text-sm text-neutral-400">
            No offers yet. They appear here when a company makes you one.
          </p>
        </div>
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
              <span
                className={`rounded-full px-2.5 py-0.5 text-xs capitalize ${
                  offer.status === "accepted"
                    ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-400"
                    : offer.status === "declined"
                      ? "bg-neutral-100 text-neutral-500 dark:bg-neutral-800 dark:text-neutral-400"
                      : "bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-400"
                }`}
              >
                {offer.status}
              </span>
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
                <button type="button" className={declineCls} onClick={() => decide(offer.id, "declined")}>
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
