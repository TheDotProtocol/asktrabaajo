"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import {
  ErrorBanner,
  LoadingState,
  PageHeader,
  cardCls,
} from "@/components/candidate/ui";
import { api } from "@/lib/api/session";
import { hasPermission } from "@/lib/api/portal";
import { useCanonicalAuth } from "@/context/AuthContext";
import {
  AppealList,
  AthenaStatus,
  EnforcementActionList,
  EventsFeed,
  GovernanceDashboard,
} from "@/lib/api/types";

type CountCard = { label: string; value: number | string; href: string; note?: string };

export default function AdminCommandCenterPage() {
  const { me } = useCanonicalAuth();
  const [cards, setCards] = useState<CountCard[]>([]);
  const [error, setError] = useState("");
  const [ready, setReady] = useState(false);

  const load = useCallback(async () => {
    setError("");
    const next: CountCard[] = [];
    try {
      if (hasPermission(me, "reports.read")) {
        const dash = await api.get<GovernanceDashboard>("/governance/dashboard");
        next.push(
          { label: "Open cases", value: dash.open, href: "/admin/governance" },
          { label: "Urgent", value: dash.urgent, href: "/admin/governance" },
          { label: "SLA breached", value: dash.breached, href: "/admin/governance" },
          { label: "Escalated", value: dash.escalated, href: "/admin/governance" },
          { label: "Unassigned", value: dash.unassigned, href: "/admin/governance" },
        );
      }
      if (hasPermission(me, "appeals.read")) {
        const appeals = await api.get<AppealList>("/enforcement/appeals?status=submitted&page_size=1");
        next.push({ label: "Appeals awaiting review", value: appeals.total, href: "/admin/governance/appeals" });
      }
      if (hasPermission(me, "enforcement.read")) {
        const proposed = await api.get<EnforcementActionList>("/enforcement/actions?status=proposed&page_size=1");
        next.push({ label: "Enforcement proposed", value: proposed.total, href: "/admin/governance/enforcement" });
      }
      if (hasPermission(me, "finance.read")) {
        const tx = await api.get<{ transactions: unknown[] }>("/finance/transactions?limit=1");
        next.push({
          label: "Finance records",
          value: tx.transactions.length > 0 ? "Available" : "None yet",
          href: "/admin/finance",
          note: "Counts come from authorized finance APIs only.",
        });
      }
      try {
        const events = await api.get<EventsFeed>("/events?limit=1");
        next.push({ label: "Your operational events", value: events.count, href: "/admin/operations" });
      } catch {
        /* events are caller-scoped; absence is not a platform outage */
      }
      try {
        const status = await api.get<AthenaStatus>("/athena/status");
        next.push({
          label: "Athena intelligence",
          value: status.available ? "Available" : "Unavailable",
          href: "/admin/athena",
          note: "Platform-operator Athena has no tools in this release.",
        });
      } catch {
        next.push({
          label: "Athena intelligence",
          value: "Unavailable",
          href: "/admin/athena",
        });
      }
      setCards(next);
    } catch (e) {
      setError(String((e as Error).message ?? e));
    } finally {
      setReady(true);
    }
  }, [me]);

  useEffect(() => {
    void load();
  }, [load]);

  if (!ready && !error) return <LoadingState label="Opening the control plane…" />;

  return (
    <div className="space-y-8">
      <PageHeader
        kicker="Super Admin"
        title="Platform command center"
        subtitle="Authorized operational counts only. This is not unrestricted access to private candidate or employer data."
      />
      {error && <ErrorBanner message={error} onRetry={() => void load()} />}
      {cards.length === 0 ? (
        <div className={cardCls}>
          <p className="font-medium text-white">No authorized operational signals</p>
          <p className="mt-2 text-sm text-[#9ca3af]">
            Your platform role does not include governance, enforcement, appeals, or finance read
            permissions. The backend remains the authority.
          </p>
        </div>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {cards.map((card) => (
            <Link key={card.label} href={card.href} className={`${cardCls} hover:border-[#d4af37]/40`}>
              <p className="text-2xl font-semibold text-white">{card.value}</p>
              <p className="mt-1 text-sm text-[#9ca3af]">{card.label}</p>
              {card.note && <p className="mt-2 text-xs text-[#6b7280]">{card.note}</p>}
            </Link>
          ))}
        </div>
      )}
      <div className={`${cardCls} space-y-2`}>
        <p className="font-medium text-white">Least privilege</p>
        <p className="text-sm text-[#9ca3af]">
          Super Admin is not an “see everything” role in the product. Case, enforcement, finance,
          and audit surfaces each require their own permission. Unsupported Figma directories
          (People, Companies, Governments, Marketing) are not fabricated.
        </p>
      </div>
    </div>
  );
}
