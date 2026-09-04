"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";

import {
  ErrorBanner,
  LoadingState,
  PageHeader,
  StatusPill,
  btnCls,
  cardCls,
  ghostBtnCls,
  inputCls,
} from "@/components/candidate/ui";
import { useCanonicalAuth } from "@/context/AuthContext";
import { hasPermission } from "@/lib/api/portal";
import { api } from "@/lib/api/session";

interface FinanceTx {
  transaction_id: string;
  organization_id: string;
  provider: string;
  amount: string;
  currency: string;
  status: string;
  description: string | null;
  refunded_amount: string;
}

interface FinanceRefund {
  refund_id: string;
  transaction_id: string;
  amount: string;
  currency: string;
  status: string;
  reason: string | null;
}

interface FinanceInvoice {
  id?: string;
  invoice_id?: string;
  organization_id?: string;
  status?: string;
  total?: string;
  amount?: string;
  currency?: string;
}

interface FinanceSubscription {
  subscription_id: string;
  organization_id: string;
  plan_code: string | null;
  plan_name: string | null;
  status: string;
  price: string;
  currency: string;
}

export default function AdminFinancePage() {
  const { me } = useCanonicalAuth();
  const canRead = hasPermission(me, "finance.read");
  const canManage = hasPermission(me, "finance.manage");
  const [txs, setTxs] = useState<FinanceTx[]>([]);
  const [refunds, setRefunds] = useState<FinanceRefund[]>([]);
  const [invoices, setInvoices] = useState<FinanceInvoice[]>([]);
  const [subs, setSubs] = useState<FinanceSubscription[]>([]);
  const [error, setError] = useState("");
  const [forbidden, setForbidden] = useState(false);
  const [ready, setReady] = useState(false);
  const [txId, setTxId] = useState("");
  const [amount, setAmount] = useState("");
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    if (!canRead) {
      setForbidden(true);
      setReady(true);
      return;
    }
    setError("");
    try {
      const [t, r, i, s] = await Promise.all([
        api.get<{ transactions: FinanceTx[] }>("/finance/transactions?limit=30"),
        api.get<{ refunds: FinanceRefund[] }>("/finance/refunds?limit=30"),
        api.get<{ invoices: FinanceInvoice[] }>("/finance/invoices?limit=30"),
        api.get<{ subscriptions: FinanceSubscription[] }>("/finance/subscriptions?limit=30"),
      ]);
      setTxs(t.transactions);
      setRefunds(r.refunds);
      setInvoices(i.invoices);
      setSubs(s.subscriptions);
    } catch (e) {
      const err = e as { status?: number; message?: string };
      if (err.status === 403) setForbidden(true);
      setError(String(err.message ?? e));
    } finally {
      setReady(true);
    }
  }, [canRead]);

  useEffect(() => {
    void load();
  }, [load]);

  async function refund(event: FormEvent) {
    event.preventDefault();
    if (!canManage) return;
    setBusy(true);
    setError("");
    try {
      await api.post("/finance/refunds", {
        transaction_id: txId.trim(),
        amount,
        reason: reason.trim() || null,
      });
      setTxId("");
      setAmount("");
      setReason("");
      await load();
    } catch (e) {
      setError(String((e as Error).message ?? e));
    } finally {
      setBusy(false);
    }
  }

  if (!ready) return <LoadingState label="Opening platform finance…" />;
  if (forbidden) {
    return (
      <ErrorBanner message="Missing platform finance permission. Company billing.manage does not grant this surface." />
    );
  }

  return (
    <div className="space-y-8">
      <PageHeader
        kicker="Platform finance"
        title="Financial records"
        subtitle="Platform-scope invoices, transactions, and refunds. Provider secrets are never shown. Employer billing stays on /employer/billing."
      />
      {error && <ErrorBanner message={error} onRetry={() => void load()} />}

      {canManage && (
        <form onSubmit={refund} className={`${cardCls} space-y-3`}>
          <p className="font-medium text-white">Authorize a refund</p>
          <p className="text-xs text-[#6b7280]">
            Requires finance.manage. The backend records the authorizing user. This does not invent a payment.
          </p>
          <input className={inputCls} placeholder="Transaction UUID" value={txId} onChange={(e) => setTxId(e.target.value)} />
          <input className={inputCls} placeholder="Amount" value={amount} onChange={(e) => setAmount(e.target.value)} />
          <input className={inputCls} placeholder="Reason" value={reason} onChange={(e) => setReason(e.target.value)} />
          <button type="submit" className={btnCls} disabled={busy || !txId.trim() || !amount}>
            {busy ? "Authorizing…" : "Authorize refund"}
          </button>
        </form>
      )}

      <section className="space-y-3">
        <h2 className="text-lg font-semibold">Transactions</h2>
        {txs.length === 0 ? (
          <p className="text-sm text-[#9ca3af]">No platform transactions yet.</p>
        ) : (
          txs.map((row) => (
            <article key={row.transaction_id} className={`${cardCls} flex flex-wrap items-center justify-between gap-3`}>
              <div>
                <p className="font-medium">{row.amount} {row.currency}</p>
                <p className="text-xs text-[#9ca3af]">{row.description || row.provider} · org {row.organization_id.slice(0, 8)}…</p>
              </div>
              <StatusPill status={row.status} />
            </article>
          ))
        )}
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-semibold">Invoices</h2>
        {invoices.length === 0 ? (
          <p className="text-sm text-[#9ca3af]">No invoices yet.</p>
        ) : (
          invoices.map((row, i) => (
            <article key={row.id || row.invoice_id || i} className={`${cardCls} flex justify-between gap-3`}>
              <p className="font-medium">{row.total || row.amount || "Invoice"} {row.currency || ""}</p>
              {row.status && <StatusPill status={row.status} />}
            </article>
          ))
        )}
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-semibold">Subscriptions</h2>
        {subs.length === 0 ? (
          <p className="text-sm text-[#9ca3af]">No platform subscriptions yet.</p>
        ) : (
          subs.map((row) => (
            <article key={row.subscription_id} className={`${cardCls} flex justify-between gap-3`}>
              <p className="text-sm">
                {row.plan_name || row.plan_code || "Plan"} · {row.price} {row.currency}
              </p>
              <StatusPill status={row.status} />
            </article>
          ))
        )}
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-semibold">Refunds</h2>
        {refunds.length === 0 ? (
          <p className="text-sm text-[#9ca3af]">No refunds recorded.</p>
        ) : (
          refunds.map((row) => (
            <article key={row.refund_id} className={`${cardCls} flex justify-between gap-3`}>
              <p className="text-sm">{row.amount} {row.currency} · {row.reason || "authorized"}</p>
              <StatusPill status={row.status} />
            </article>
          ))
        )}
      </section>
      {!canManage && (
        <p className="text-xs text-[#6b7280]">Refund authorization is hidden because this account lacks finance.manage.</p>
      )}
      <button type="button" className={ghostBtnCls} onClick={() => void load()}>
        Refresh
      </button>
    </div>
  );
}
